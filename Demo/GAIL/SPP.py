import math
import torch
import torch.nn as nn
class SPP:
    """The summary line for a class docstring should fit on one line.

        If the class has public attributes, they may be documented here
        in an ``Attributes`` section and follow the same formatting as a
        function's ``Args`` section. Alternatively, attributes may be documented
        inline with the attribute's declaration (see __init__ method below).

        Properties created with the ``@property`` decorator should be documented
        in the property's getter method.

        Attributes:
            attr1 (str): Description of `attr1`.
            attr2 (:obj:`int`, optional): Description of `attr2`.

        """
    def __init__(self, prevConv, numSample, prevConvSize, outPoolSize, kernelSize):
        super(SPP, self).__init__()
        for i in range(len(outPoolSize)):
            # print(outPoolSize)
            w_ker = int(math.ceil(prevConvSize[0] / outPoolSize[i]))
            h_ker = int(math.ceil(prevConvSize[1] / outPoolSize[i]))
            w_str = int(math.floor(prevConvSize[0] / outPoolSize[i]))
            h_str = int(math.floor(prevConvSize[1] / outPoolSize[i]))
            w_pad = int(kernelSize-1) / 2
            h_pad = int(kernelSize-1) / 2
            #w_pad = (h_wid * outPoolSize[i] - prevConvSize[0] + 1) / 2 #ToDo: h_wid wrong place
            #h_pad = (w_wid * outPoolSize[i] - prevConvSize[1] + 1) / 2
            #w_pad = (h_wid * outPoolSize[i] - prevConvSize[0] + 1) / 2
            #h_pad = (w_wid * outPoolSize[i] - prevConvSize[1] + 1) / 2

            # pad should be smaller than 1/2 kernel size
            maxpool = nn.MaxPool2d((kernelSize, kernelSize), stride=(h_str, w_str), padding=(h_pad, w_pad))

            x = maxpool(prevConv)
            if (i == 0):
                spp = x.view(numSample, -1)
                # print("spp size:",spp.size())
            else:
                # print("size:",spp.size())
                spp = torch.cat((spp, x.view(numSample, -1)), 1)
        return spp

