from __future__ import print_function
import argparse
import os
import queue
import random
import torch
import shutil
import glob
import torch.nn as nn
import torch.nn.parallel
import torch.backends.cudnn as cudnn
import torch.optim as optim
import torch.utils.data
import gym_recording.playback
import numpy as np
from GAIL.Discriminator import Discriminator
from GAIL.Generator import Generator
from Stage1.getVideoWAction import GetVideoWAction
import cv2

#parser = argparse.ArgumentParser()
#Net
#parser.add_argument('--lr', type=float, default=0.001, help='learning rate, default=0.0002')
#parser.add_argument('--betas', type=float, default=0.5, help='beta1 for adam. default=0.5')
lr = 0.0002
betas = 0.5
#Data
#parser.add_argument('--dataset', required=False, default='folder')
#parser.add_argument('--dataroot', required=False, default='./data', help='path to dataset')
#parser.add_argument('--outf', default='./Output', help='folder to output images and model checkpoints')
#GPU
#parser.add_argument('--cuda', action='store_true', help='enables cuda')
#parser.add_argument('--ngpu', type=int, default=0, help='number of GPUs to use')
#Generator
#parser.add_argument('--Gkernel', required=False, default=2, help='AKA filter')
#parser.add_argument('--GinChannel', type=int, required=False, default=210)
#parser.add_argument('--GoutChannel',type=int, required=False, default=18)
Gkernel = 2
#Discriminator
#parser.add_argument('--Dkernel', required=False, default=2, help='AKA filter')
#parser.add_argument('--DinChannel', type=int, required=False, default=210)
#parser.add_argument('--DoutChannel',type=int, required=False, default=18)
Dkernel = 2
#GAIL
#parser.add_argument('--batchSize', type=int, default=64, help='input batch size')
#parser.add_argument('--nz', type=int, default=100, help='size of the latent z vector')
#parser.add_argument('--ngf', type=int, default=64)
#parser.add_argument('--ndf', type=int, default=64)
#parser.add_argument('--niter', type=int, default=25, help='number of epochs to train for')

#opt = parser.parse_args()
#print(opt)

#try:
    #os.makedirs(opt.outf)
#except OSError:
    #pass

cudnn.benchmark = True

#if torch.cuda.is_available() and not opt.cuda:
    #print("WARNING: You have a CUDA device, so you should probably run with --cuda")

#nz = int(opt.nz)
#ngf = int(opt.ngf)
#ndf = int(opt.ndf)
#nc = 3

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

class GAIL():
    def __init__(self,folder,target)-> None:
        self.expertState = []
        self.expertAction = []
        self.expertReward = []
        self.sample(folder,target)
        stateSize = len(self.expertState)
        actionSize = len(self.expertAction)
        maxAction = max(self.expertAction)
        self.generator = Generator(stateSize, actionSize,Gkernel, maxAction).to(device)
        self.generatorOptim = torch.optim.Adam(self.generator.parameters(),lr=lr)

        self.discriminator = Discriminator(stateSize, actionSize, Dkernel).to(device)
        self.discriminatorOptim = torch.optim.Adam(self.discriminator.parameters(), lr=lr)

        #self.numIntaration = numIteration()

        #self.loss_fn = nn.BCELoss()

    def sample(self, folder, targetFolder):
        #load images
        expertData = GetVideoWAction("IceHockey-v0", 3, True)
        dataName = expertData.replay(folder, targetFolder)
        #Read Action
        self.expertAction = np.load(dataName+"/action.npy")
        # Read Reward
        self.expertReward = np.load(dataName+"/reward.npy")
        # Read State
        shutil.unpack_archive(dataName + "/state.zip", dataName + "/state")
        for ii in range(0, len(self.expertAction)):
            ii += 1
            self.expertState.append(dataName + "/state/"+str(ii)+".jpg")



    def update(self, n_iter, batch_size = 100):
        for i in range(n_iter):
            #######################
            # update discriminator
            #######################
            self.discriminatorOptim.zero_grad()

            # label tensors
            exp_label = torch.full((batch_size, 1), 1, device=device)
            policy_label = torch.full((batch_size, 1), 0, device=device)


            # with expert transitions
            prob_exp = self.discriminator.forward(self.expertState, self.expertAction)
            loss = self.loss_fn(prob_exp, exp_label)

            # with policy transitions
            prob_policy = self.discriminator(state, action.detach())
            loss += self.loss_fn(prob_policy, policy_label)

            # take gradient step
            loss.backward()
            self.optim_discriminator.step()

            ################
            # update policy
            ################
            self.generatorOptim.zero_grad()

            loss_generator = -self.discriminator(state, )

        print("")

    def policyStep(self,state):
        state = torch.FloatTensor(state.reshape(1, -1)).to(device)
        return self.generator(state).cpu().data.numpy().flatten()

    def train(self):
        #Init Generator
        numState = len(self.expertAction)
        f = cv2.imread(self.expertState[0])
        h, w, d = f.shape
        randomNoise = np.uint8(np.random.randint(0, 255, size=(h, w, d)))
        self.generator.forward(randomNoise)

        #Train with expert state
        for x in range(0,numState):
            istate = cv2.imread(self.expertState[0])
            action = self.generator.forward(istate)
            self.generatorOptim.step()



if __name__ == "__main__":
    gail = GAIL("/DropTheGame/Demo/Stage1/openai.gym.1566264389.031848.82365","../resources")


