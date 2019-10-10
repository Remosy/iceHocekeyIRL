from __future__ import print_function
import torch
import torch.nn as nn
import torch.nn.parallel
import torch.backends.cudnn as cudnn
from torch.autograd import Variable
import torch.utils.data
import numpy as np
from GAIL.Discriminator import Discriminator
from GAIL.Generator import Generator
from GAIL.PPO import PPO
from commons.DataInfo import DataInfo
import cv2, gym

cudnn.benchmark = True
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

class GAIL():
    def __init__(self,dataInfo:DataInfo)-> None:

        self.learnRate = 0.0007
        self.lossCriterion = nn.BCELoss()

        self.dataInfo = dataInfo

        self.generator = None
        self.generatorOptim = None

        self.discriminator = None
        self.discriminatorOptim = None

        self.lastActions = []

        self.env = gym.make(dataInfo.gameName)
        self.ppo = None
        self.ppoExp = None

        self.ppoCounter = []
        self.lossCounter = []


    def setUpGail(self):
        self.generator = Generator(self.dataInfo).to(device)
        self.generatorOptim = torch.optim.Adam(self.generator.parameters(), lr=self.learnRate)

        self.discriminator = Discriminator(self.dataInfo).to(device)
        self.discriminatorOptim = torch.optim.Adam(self.discriminator.parameters(), lr=self.learnRate)

    def getAction(self,state):
        state = torch.FloatTensor(state.reshape(1, -1)).to(device)
        return self.generator(state).cpu().data.numpy().flatten()

    def makeDisInput(self, state, action):
        #state = state.flatten()
        #state = torch.reshape(state, [-1, state.shape[1]*state.shape[2]*state.shape[3]])
        output = action.view(action.shape[0],1)
        output = output.type(torch.FloatTensor).to(device)
        return output

    def updateModel(self):
        for batchIndex in range(len(self.dataInfo.expertState)):
            #read experts' state
            batch = self.dataInfo.expertState[batchIndex].size

            exp_state = []
            exp_action = np.zeros((batch, 1))
            exp_reward = np.zeros((batch,1))
            exp_done = np.zeros((batch,1)) #asume all "not done"
            exp_done = (exp_done==0)

            if self.datatype == 0: #image state
                exp_state = np.zeros((batch, self.dataInfo.stateShape[0], self.dataInfo.stateShape[1], self.dataInfo.stateShape[2]))
                for j in range(batch):
                    exp_state[j]= cv2.imread(self.dataInfo.expertState[batchIndex][j])
                    #cv2.imwrite("result.jpg", img)
                    exp_action[j] = self.dataInfo.expertAction[batchIndex][j]
                    exp_reward[j] = self.dataInfo.expertReward[batchIndex][j]
            elif self.datatype == 1: #coordinators state
                exp_state = np.zeros((batch, self.dataInfo.stateShape[-1]))
                for j in range(batch):
                    exp_state = self.dataInfo.expertState[batchIndex][j]
                    exp_action = self.dataInfo.expertAction[batchIndex][j]
            exp_state = np.rollaxis(exp_state, 3, 1) # [n,210,160,3] => [n,3,210,160]
            #_thnn_conv2d_forward not supported on CPUType for Int, so the type is float
            exp_state = (torch.from_numpy(exp_state/255)).type(torch.FloatTensor).to(device) #float for Conv2d
            exp_action = (torch.from_numpy(exp_action)).type(torch.FloatTensor).to(device)

            print("Batch: {}\t generating {} fake data...".format(str(batchIndex), str(batch)))
            #Generate action
            fake_actionDis, fake_action, _ = self.generator(exp_state)
            exp_score = (self.generator.criticScore).detach()

            # Initialise Discriminator
            self.discriminatorOptim.zero_grad()

            #Train Discriminator with fake(s,a) & expert(s,a)
            detach_fake_action = fake_action.detach()
            fake_input = self.makeDisInput(exp_state, detach_fake_action)
            exp_input = self.makeDisInput(exp_state, exp_action)

            print("Calculating loss...")
            fake_label = torch.full((batch, 1), 0, device=device)
            exp_label = torch.full((batch, 1), 1, device=device)
            fake_loss = self.discriminator(fake_input)
            fake_loss = self.lossCriterion(fake_loss, fake_label)
            exp_loss = self.discriminator(exp_input)
            exp_loss = self.lossCriterion(exp_loss, exp_label)

            #Update Discriminator based on loss gradient
            loss = fake_loss+exp_loss
            loss.backward()
            self.discriminatorOptim.step()

            #Get loss with updated Discriminator
            self.generatorOptim.zero_grad() #init
            lossFake = self.discriminator(fake_input)
            lossFake = -self.lossCriterion(lossFake, exp_label)

            # Update generator with updated-Discriminator's loss
            lossFake.backward()
            self.generatorOptim.step()

            #Use PPO to ptimise Generator
            #states,actions,rewards,scores,dones,dists
            if batchIndex%10 == 0:
                exp_state = (Variable(exp_state).data).cpu().numpy() #convert to numpy
                exp_action = (Variable(exp_action).data).cpu().numpy()
                exp_score = (Variable(exp_score).data).cpu().numpy()
                self.ppoExp = PPO(self.generator, self.generatorOptim, self.learnRate)
                self.ppoExp.importExpertData(exp_state,exp_action,exp_reward,exp_score,exp_done,fake_actionDis)
                self.generator, self.generatorOptim = self.ppoExp.optimiseGenerator()


    def train(self, numIteration):
        for i in range(numIteration):
            print("--Iteration {}--".format(str(i)))
            #GAIL
            self.dataInfo.shuffle()
            self.dataInfo.sampleData()
            self.updateModel()

            #PPO
            self.ppo = PPO(self.generator,self.generatorOptim)
            self.ppo.tryEnvironment()
            self.ppoCounter.append(self.ppo.totalReward)
            #Flexible to add
            self.generator, self.generatorOptim = self.ppo.optimiseGenerator()

        """
         #totalReawrd = 0
            #plotEpoch.append(ep)
            #plotReward.append(totalReawrd/(i_episode+1))
            #print("Epoch: {}\t Avg Reward: {}".format(ep, totalReawrd/(i_episode+1)))
        plt.plot(plotEpoch,plotReward, marker="X")
        plt.xlabel("Epochs")
        plt.ylabel("Rewards")
        plt.title("{} {} {}".format("IceHockey","0.005","ImageState"))
        plt.savefig("TrainResult.png")
        env.close()
        """

    def save(self, path):
        torch.save(self.generator.state_dict(), '{}/generator.pth'.format(path))
        torch.save(self.discriminator.state_dict(), '{}/discriminator.pth'.format(path))

    def load(self, path):
        self.generator.load_state_dict(torch.load('{}/generator.pth'.format(path)))
        self.discriminator.load_state_dict(torch.load('{}/discriminator.pth'.format(path)))










