# -*- coding: utf-8 -*-
'''
Goal : 
Author : Yonghan Jung, ISyE, KAIST 
Date : 15
Comment 
- 

'''

''' Library '''
import numpy as np
import scipy as sp
import pandas as pd
from Module.data_call import data_call
from Module.bandpass import BandPassFilter
from Module.AdaptiveThreshold import AdaptiveThreshold
from Module.FourierTransformation import FourierTransformation
from Module.SlopeSumFunction import SlopeSumFunction
import adaptfilt

import matplotlib.pyplot as plt


''' Function or Class '''

class DrMPPGAnalysis:
    def __init__(self, Str_DataName, Int_DataNum, ):
        self.FltSamplingRate = 75.0
        self.Str_DataName = Str_DataName
        self.Int_DataNum = Int_DataNum
        self.Array_PPG_Long = data_call(data_name=self.Str_DataName,data_num=self.Int_DataNum, wanted_length=0)
        self.Array_TimeDomain_Long = np.linspace(0, len(self.Array_PPG_Long) / self.FltSamplingRate ,len(self.Array_PPG_Long) )

        ## CONTROL VARIABLE ##
        Int_Start = 40
        Int_End = 43
        Int_CutTime = 60
        self.Array_PPG_Long = self.Array_PPG_Long[: int(self.FltSamplingRate) * Int_CutTime]
        self.Array_PPG_Long = self.BandPassFilter(Array_Signal=self.Array_PPG_Long)
        # self.Array_PPG_Long = self.BandPassFilter(self.Array_PPG_Long)
        self.Array_TimeDomain_Long = self.Array_TimeDomain_Long[:int(self.FltSamplingRate) * Int_CutTime]
        self.Array_PPG = self.Array_PPG_Long[ Int_Start *int(self.FltSamplingRate)   :Int_End * int(self.FltSamplingRate)]
        self.Array_TimeDomain = self.Array_TimeDomain_Long[Int_Start *int(self.FltSamplingRate)   :Int_End * int(self.FltSamplingRate)]

        #####################
    # Target is a peak or not
    def Determine_PeakorNot(self, PrevAmp, CurAmp, NextAmp):
        if PrevAmp < CurAmp and CurAmp >= NextAmp:
            return True
        else:
            return False

    def Determine_PeakFindingBuffer(self, Int_PeakIdx, Int_PeakFindingBuffer, List_PeakCand):
        PeakIsThere = False
        for PeakCand in List_PeakCand:
            List_PeakCandBuffer = range(PeakCand-Int_PeakFindingBuffer, PeakCand+Int_PeakFindingBuffer)
            if Int_PeakIdx in List_PeakCandBuffer:
                PeakIsThere = True
                break
            else:
                pass
        if PeakIsThere == True:
            return True
        else:
            return False

    def Execution(self):
        Int_TotalSignalLength = len(self.Array_PPG_Long)
        Int_3secSignalLength = int(self.FltSamplingRate * 3)
        Int_IdxTarget = (Int_3secSignalLength / 2) + 1
        Int_LMSFilterLength = 10
        Int_SSFBufferLength = 10
        Int_BufferPeakFinding = 10
        Int_IdxBuffer = 20
        Dict_PeakTimeLoc_PeakAmp = dict()

        for IntIdx in range(Int_TotalSignalLength - Int_3secSignalLength):
            Array_BlockSignal = self.Array_PPG_Long[IntIdx : IntIdx + Int_3secSignalLength]
            Array_BlockTime = self.Array_TimeDomain_Long[IntIdx : IntIdx + Int_3secSignalLength]
            Flt_PrevPt = Array_BlockSignal[Int_IdxTarget-1]
            Flt_NextPt = Array_BlockSignal[Int_IdxTarget+1]
            Flt_TargetPt = Array_BlockSignal[Int_IdxTarget]
            Flt_IdxTarget = Array_BlockTime[Int_IdxTarget]

            # print IntIdx, Flt_IdxTarget
            # print Flt_IdxTarget, Flt_TargetPt
            if self.Determine_PeakorNot(PrevAmp=Flt_PrevPt, CurAmp=Flt_TargetPt, NextAmp=Flt_NextPt) == True:
                Array_HammingBlockSignal = self.Block_Signal(Array_BlockSignal)
                Array_MARBlockSignal = self.Removing_MotionArtifact(Int_FilterLength=Int_LMSFilterLength, Array_Signal=Array_HammingBlockSignal)
                Array_MARBlockSignal = np.concatenate([np.zeros(Int_LMSFilterLength-1), Array_MARBlockSignal])
                Array_SSFBlockSignal, Flt_Threshold = self.Computing_SSF(Array_MARBlockSignal, Int_SSFBufferLength)
                Array_SSFBlockSignal = np.concatenate([np.zeros(Int_SSFBufferLength), Array_SSFBlockSignal])
                Dict_Loc_ThresholdAmp, Dict_MaxLoc_MaxAmp = self.AdaptiveThreshold(Array_Signal=Array_SSFBlockSignal, Flt_AmpThreshold=Flt_Threshold)
                # print IntIdx, Int_IdxTarget, Flt_IdxTarget, Dict_MaxLoc_MaxAmp.keys()
                if self.Determine_PeakFindingBuffer(Int_PeakIdx=Int_IdxTarget, Int_PeakFindingBuffer=Int_BufferPeakFinding, List_PeakCand=Dict_MaxLoc_MaxAmp.keys()) == True:
                    print "PEAK!", IntIdx, Int_IdxTarget, Flt_IdxTarget, Dict_MaxLoc_MaxAmp.keys()
                    Idx_ModifiedIdx, Flt_NewIdxTarget = self.PeakArrangeMent(Array_BlockSignal = Array_BlockSignal, Array_BlockTime=Array_BlockTime, Int_IdxTarget=Int_IdxTarget, Int_IdxBuffer=Int_IdxBuffer)
                    Dict_PeakTimeLoc_PeakAmp[Flt_NewIdxTarget] = Array_BlockSignal[Idx_ModifiedIdx]
        return Dict_PeakTimeLoc_PeakAmp

    def BandPassFilter(self, Array_Signal):
        self.Flt_LowCut = 0.5
        self.Flt_HighCut = 9
        Object_BandPassFilter = BandPassFilter(Array_Signal=Array_Signal, Flt_SamplingRate=self.FltSamplingRate, Flt_LowCut=self.Flt_LowCut, Flt_HighCut=self.Flt_HighCut)
        return Object_BandPassFilter.butter_bandpass_filter()

    def Block_Signal(self, Array_Signal):
        Int_ArraySignal = len(Array_Signal)
        HammingWindow = np.hamming(Int_ArraySignal)
        Array_Signal = Array_Signal * HammingWindow
        return Array_Signal

    def ConvertFrequencyDomain(self, Array_Signal):
        Object_FFT = FourierTransformation(Array_Signal=Array_Signal, Flt_SamplingRate=self.FltSamplingRate)
        Array_FrequencyDomain, Array_FourierResult= Object_FFT.Compute_FrequencyDomain()
        return Array_FrequencyDomain, Array_FourierResult

    def ConvertInvertFourier(self, Array_Signal):
        ### ControlVaraible ###
        # Source = Raghu Ram et al., (2012) A Noven Approach for Motion Artifact Reduction in PPG Signals Based on AS-LMS Adaptive Filter
        Flt_Pulsatile_Lower = 0.5
        Flt_Pulsatile_Upper = 4.0
        Flt_Resp_Lower = 0.2
        Flt_Resp_Upper = 0.35
        # Flt_BandPassFilter = 9.0
        ##############################
        # Array_Signal = self.BandPassFilter()
        NormalizedTerm = (len(Array_Signal)/ 2)
        Object_FFT = FourierTransformation(Array_Signal=Array_Signal, Flt_SamplingRate=self.FltSamplingRate)
        Array_FrequencyDomain, Array_FourierResult = Object_FFT.Compute_FrequencyDomain()
        for IntIdx in range(len(Array_FrequencyDomain)):
            # Cut Resp Power
            Hz = Array_FrequencyDomain[IntIdx]
            if Hz > Flt_Resp_Lower and Hz < Flt_Resp_Upper:
                Array_FourierResult[IntIdx] = 0.0
            elif Hz > Flt_Pulsatile_Lower and Hz < Flt_Pulsatile_Upper:
                Array_FourierResult[IntIdx] = 0.0
            # elif Hz <= 0.05:
            #     Array_FourierResult[IntIdx] = 0.0
            # elif Hz > Flt_BandPassFilter :
            #     Array_FourierResult[IntIdx] = 0.0
        Array_InverseFourierSignal = 2*np.fft.ifft(Array_FourierResult*NormalizedTerm).real
        return Array_FrequencyDomain, Array_FourierResult, Array_InverseFourierSignal

    def Removing_MotionArtifact(self, Int_FilterLength, Array_Signal):
        _,_,Array_NoiseReference = self.ConvertInvertFourier(Array_Signal=Array_Signal)
        Flt_StepSize = 0.1

        Array_NoiseEst, Array_NoiseRemoved, Array_FilterCoefs = adaptfilt.nlms(u=Array_NoiseReference,d=Array_Signal, M=Int_FilterLength, step=Flt_StepSize)
        return Array_NoiseRemoved

    def Computing_SSF(self, Array_Signal, INt_SSF_FilterLength):
        Object_SSF = SlopeSumFunction(Array_SignalInWindow=Array_Signal, Int_SSFLength=INt_SSF_FilterLength)
        Array_SSF, Flt_Threshold = Object_SSF.Conduct_SSF()
        return Array_SSF, Flt_Threshold

    def AdaptiveThreshold(self, Array_Signal, Flt_AmpThreshold):
        ## Control Variable
        Flt_SlopeThreshold = -0.6
        Flt_BackThreshold = 0.6 * self.FltSamplingRate
        #####################

        Object_AdaptiveThreshold = AdaptiveThreshold(Array_SignalinWindow=Array_Signal, Flt_SamplingRate=self.FltSamplingRate, Flt_AmpThreshold=Flt_AmpThreshold)
        Dict_Loc_ThresholdAmp, Dict_MaxLoc_MaxAmp = Object_AdaptiveThreshold.AdaptiveThreshold(Flt_SlopeThreshold, Flt_BackThreshold)
        return Dict_Loc_ThresholdAmp, Dict_MaxLoc_MaxAmp

    def PeakArrangeMent(self, Array_BlockTime, Array_BlockSignal, Int_IdxTarget, Int_IdxBuffer):
        # Among keys in Dict_PeakTimeLoc_PeakAmp, Arrange key to the most appropriate one
        Array_BlockSignal = np.array(Array_BlockSignal)
        Array_IdxTarget_Buffer = np.array(range(Int_IdxTarget - Int_IdxBuffer, Int_IdxTarget + Int_IdxBuffer))
        Idx_ModifiedIdx = np.argmax(Array_BlockSignal[Array_IdxTarget_Buffer])
        Int_NewModifiedIdx = Array_IdxTarget_Buffer[Idx_ModifiedIdx]
        Flt_NewIdxTarget = Array_BlockTime[Int_NewModifiedIdx]
        return Int_NewModifiedIdx, Flt_NewIdxTarget








if __name__ == "__main__":
    Str_DataName = "PPG_Walk"
    # Str_DataName = "PPG_KW_long" ## SUPER CLEAN
    List_DataNum = [1,2,3,4,5,6,7]
    List_MAData = [2,4,6]
    List_Clean = [1,3,5,7]
    List_KW = [0,1,2]
    Int_DataNum = 7
    # 1 : Moderately Clean, little corrupted
    # 2 : MA Super corrupted
    # 3 : Super Clean
    # 4 : MA Corrupted
    # 5 : Clean
    # 6 : Corrupted
    # 7 : Quite Clean

    Int_FilterLength = 10
    Int_SSFLength = 10
    Object_DrMPPG = DrMPPGAnalysis(Str_DataName=Str_DataName, Int_DataNum=Int_DataNum)
    Array_PPG =Object_DrMPPG.Array_PPG_Long
    Array_Time = Object_DrMPPG.Array_TimeDomain_Long
    StartIdx = int(75 * (9.33-1.5))

    # Mode = "Practice"
    Mode = "Real"

    if Mode == "Practice":
        Array_PPGSample = Array_PPG[StartIdx:StartIdx+3*75]
        Array_TimeSample = Array_Time[StartIdx:StartIdx+ 3*75]
        Array_HammingSample = Object_DrMPPG.Block_Signal(Array_PPGSample)
        Array_MARemovalSample = Object_DrMPPG.Removing_MotionArtifact(Int_FilterLength=Int_FilterLength, Array_Signal=Array_HammingSample)
        Array_MARemovalSample = np.concatenate([np.zeros(Int_FilterLength-1), Array_MARemovalSample])
        Array_SSFSample, Flt_Threshold = Object_DrMPPG.Computing_SSF(Array_Signal=Array_MARemovalSample, INt_SSF_FilterLength=Int_SSFLength)
        Array_SSFSample = np.concatenate([np.zeros(Int_SSFLength), Array_SSFSample])
        Dict_Loc_ThresholdAmp, Dict_MaxLoc_MaxAmp = Object_DrMPPG.AdaptiveThreshold(Array_Signal=Array_SSFSample, Flt_AmpThreshold=Flt_Threshold)

        Int_TargetIdx = 3*75/2 + 1

        plt.figure()
        # Peak retained?
        plt.title("PPG Example " + str(StartIdx))
        plt.grid()
        plt.plot(Array_TimeSample, Array_PPGSample,'b', label="Raw Signal")
        plt.plot(Array_TimeSample, Array_HammingSample,'g', label="Hamming Signal")
        plt.plot(Array_TimeSample[Int_TargetIdx], Array_HammingSample[Int_TargetIdx],'go')
        plt.plot(Array_TimeSample, Array_MARemovalSample,'r', label="MA removed")
        plt.plot(Array_TimeSample[Int_TargetIdx], Array_MARemovalSample[Int_TargetIdx],'go')
        plt.plot(Array_TimeSample, Array_SSFSample, 'purple', label="Slope Sum")
        plt.plot(Array_TimeSample[Dict_Loc_ThresholdAmp.keys()], Dict_Loc_ThresholdAmp.values(),'orange')
        plt.plot(Array_TimeSample[Dict_MaxLoc_MaxAmp.keys()], Dict_MaxLoc_MaxAmp.values(),'ko')
        plt.plot(Array_TimeSample[Int_TargetIdx], Array_SSFSample[Int_TargetIdx], 'go', label="Target Point")
        plt.legend()

        plt.show()

    elif Mode == "Real":
        Dict_PeakTimeLoc_PeakAmp = Object_DrMPPG.Execution()
        # for idx, key in enumerate(sorted(Dict_PeakTimeLoc_PeakAmp)):
        #     print key, Dict_PeakTimeLoc_PeakAmp[key]

        plt.figure()
        plt.title("Peak Finding SigNum : "+ str(Int_DataNum))
        plt.grid()
        plt.plot(Array_Time, Array_PPG,'bo')
        plt.plot(Dict_PeakTimeLoc_PeakAmp.keys(), Dict_PeakTimeLoc_PeakAmp.values(),'ro')

        plt.figure()
        plt.title("Peak Finding SigNum : "+ str(Int_DataNum))
        plt.grid()
        plt.plot(Array_Time, Array_PPG,'b', label="Raw PPG Signal")
        plt.plot(Dict_PeakTimeLoc_PeakAmp.keys(), Dict_PeakTimeLoc_PeakAmp.values(),'ro', label="Peak")
        plt.legend()
        plt.show()

