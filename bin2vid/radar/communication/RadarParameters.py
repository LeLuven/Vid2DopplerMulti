"""
Created on 15.07.2022

@author: IMST GmbH
"""


from typing import Tuple

# maximum number of rx channels
MAX_RX_CHAN = 4
MAX_RX_CHAN_MIMO = 12

# possible radar cube values (samples_chirps_rxChannel)
RCUBE_smpl256_crp1_4rx = 0
RCUBE_smpl512_crp1_4rx = 1
RCUBE_smpl1024_crp1_4rx = 2
RCUBE_smpl2048_crp1_4rx = 3

RCUBE_smpl128_crp64_4rx = 4
RCUBE_smpl128_crp128_4rx = 5
RCUBE_smpl128_crp256_4rx = 6
RCUBE_smpl256_crp64_4rx = 7
RCUBE_smpl256_crp128_4rx = 8
RCUBE_smpl256_crp256_4rx = 9
RCUBE_smpl512_crp64_4rx = 10
RCUBE_smpl512_crp128_4rx = 11
RCUBE_smpl512_crp256_4rx = 12
RCUBE_smpl1024_crp64_4rx = 13
RCUBE_smpl1024_crp128_4rx = 14

RCUBE_smpl256_crp64_tdMimo_3tx_4rx = 15
RCUBE_smpl256_crp128_tdMimo_3tx_4rx = 16
RCUBE_smpl256_crp256_tdMimo_3tx_4rx = 17
RCUBE_smpl512_crp64_tdMimo_3tx_4rx = 18
RCUBE_smpl512_crp128_tdMimo_3tx_4rx = 19
RCUBE_smpl1024_crp64_tdMimo_3tx_4rx = 20
RCUBE_maxValue = 21

# possible processing steps
PROC_NoProcessing = 0
PROC_RangeFFT = 1
PROC_DopplerFFT = 2
PROC_Combining = 3
PROC_PeakDet = 4
PROC_CFAR = 5
PROC_Detections = 6
PROC_Tracking = 7

# possible FFT windows
FFTWIN_NoWin = 0
FFTWIN_Blackman = 1
FFTWIN_Hamming = 2
FFTWIN_Hann = 3
FFTWIN_Nuttal = 4

# possible speed estimation options
SPEED_EST_OFF = 0
SPEED_EST_SPEED_ONLY = 1
SPEED_EST_FILTER_ALL = 2
SPEED_EST_FILTER_TRACKS = 3


class RadarParameters(object):
    # values to indicate that current maximum values should be used
    MAX_RANGE_BIN = 0xEFCA
    MAX_DOPPLER_BIN = 0xFEAC
    NO_DOPPLER_INTERVAL = 0xD000

    def __init__(self):
        # Data acquisition
        self.RadarCube = RCUBE_smpl512_crp128_4rx  # data cube dimension
        self.ContinuousMeas = 0  # 0 or 1
        self.MeasInterval = 0  # timer interval [ms] (0 - 10000)
        self.Processing = PROC_RangeFFT
        self.RangeWinFunc = FFTWIN_Blackman
        self.DopplerWinFunc = FFTWIN_Blackman
        self.DopplerFftShift = 1  # shift doppler data when sending data cube (0 or 1)
        self.MinRangeBin = 0  # minimum range bin for data sending
        self.MaxRangeBin = 255  # maximum range bin for data sending
        self.MinDopplerBin = -64  # minimum doppler bin for data sending
        self.MaxDopplerBin = 63  # maximum doppler bin for data sending
        # Target detection
        self.CfarWindowSize = 10  # window size of CFAR
        self.CfarGuardInt = 2  # CFAR guard interval
        self.RangeCfarThresh = 8  # threshold for CFAR in range direction
        self.TriggerThresh = 10  # threshold for triggering pin
        self.PeakSearchThresh = (
            6  # threshold for initialization of threshold used by peak search
        )
        self.SuppressStaticTargets = (
            0  # 0 = OFF, 1 = delete 0 doppler, 2 = delete 0 doppler and neighbors
        )
        self.MaxTargets = 30  # maximum number of detected targets allowed
        # Target tracking
        self.MaxTracks = 10  # maximum number of tracks allowed (<= MaxTargets)
        self.MaxHorSpeed = 5  # [m/s]
        self.MaxVerSpeed = 1  # [m/s]
        self.MaxAccel = 10  # [m/s^2]
        self.MaxRangeError = 20  # range error [m/10]
        self.MinConfirm = 2  # minimum number of confirmations
        self.TargetSize = 5  # expected target size [m/10]
        self.MergeLimit = 15  # limit for track merging
        # Other
        self.SectorFiltering = 0  # normalize measured RCS of targets
        self.SpeedEstimation = (
            SPEED_EST_OFF  # enable/disable estimation of radar system speed
        )
        self.DspDopplerProc = 0  # use DSP doppler processing for tracks
        self.RxChannels = (
            0xF  # bitmask which rx channels should be sent in data read commands
        )
        self.CfarSelect = (
            1  # bitmask: 0 = No CFAR; 0x1 = Range CFAR, 0x2 = Doppler CFAR
        )
        self.DopplerCfarThresh = 10  # threshold for CFAR in doppler direction

        self.updateInternals()

    def updateInternals(self):
        nS, nR, nD = self.getCubeBins(self.RadarCube)

        self._isMIMO = self.RadarCube >= RCUBE_smpl256_crp64_tdMimo_3tx_4rx

        self._NumSamples = nS
        self._NumRangeBins = nR
        self._NumDopplerBins = nD
        self._ActiveRangeBins = self.MaxRangeBin - self.MinRangeBin + 1
        self._ActiveDopplerBins = self.MaxDopplerBin - self.MinDopplerBin + 1
        self._ActiveRxChannels = self.getNumActiveRxChan()

        # get internal used doppler indices, dependent on FFT shift here!
        self._dBinNegL = (
            self._dBinNegH
        ) = self._dBinPosL = self._dBinPosH = self.NO_DOPPLER_INTERVAL
        if self.MinDopplerBin < 0 and self.MaxDopplerBin >= 0:
            self._dBinNegL = self._NumDopplerBins + self.MinDopplerBin
            self._dBinNegH = self._NumDopplerBins - 1
            self._dBinPosL = 0
            self._dBinPosH = self.MaxDopplerBin
        elif self.MinDopplerBin >= 0 and self.MaxDopplerBin > 0:
            self._dBinPosL = self.MinDopplerBin
            self._dBinPosH = self.MaxDopplerBin
        else:  # MinDopplerBin < 0 and MaxDopplerBin < 0
            self._dBinNegL = self._NumDopplerBins + self.MinDopplerBin
            self._dBinNegH = self._NumDopplerBins + self.MaxDopplerBin

        if self.DopplerFftShift:  # correct indices for doppler shift
            nD //= 2
            if (
                self._dBinNegL != self.NO_DOPPLER_INTERVAL
            ):  # lower limit of negative doppler interval
                self._dBinNegL -= nD
            if (
                self._dBinNegH != self.NO_DOPPLER_INTERVAL
            ):  # upper limit of negative doppler interval
                self._dBinNegH -= nD
            if (
                self._dBinPosL != self.NO_DOPPLER_INTERVAL
            ):  # lower limit of positive doppler interval
                self._dBinPosL += nD
            if (
                self._dBinPosH != self.NO_DOPPLER_INTERVAL
            ):  # upper limit of positive doppler interval
                self._dBinPosH += nD

        if self.DopplerFftShift:
            if self._dBinNegL != self.NO_DOPPLER_INTERVAL:
                self._dBinIdxs = [d for d in range(self._dBinNegL, self._dBinNegH + 1)]
            if self._dBinPosL != self.NO_DOPPLER_INTERVAL:
                self._dBinIdxs += [d for d in range(self._dBinPosL, self._dBinPosH + 1)]
        else:
            if self._dBinPosL != self.NO_DOPPLER_INTERVAL:
                self._dBinIdxs = [d for d in range(self._dBinPosL, self._dBinPosH + 1)]
            if self._dBinNegL != self.NO_DOPPLER_INTERVAL:
                self._dBinIdxs += [d for d in range(self._dBinNegL, self._dBinNegH + 1)]

    # return number of range and doppler bins of selected cube in form (samples,range,doppler)
    @staticmethod
    def getCubeBins(cube: int) -> Tuple[int, int, int]:
        cube = int(cube)

        if cube < 0 or cube > RCUBE_maxValue - 1:
            raise Exception("cube value out of range!")
        if cube == RCUBE_smpl256_crp1_4rx:
            return (256, 256, 1)
        elif cube == RCUBE_smpl512_crp1_4rx:
            return (512, 512, 1)
        elif cube == RCUBE_smpl1024_crp1_4rx:
            return (1024, 1024, 1)
        elif cube == RCUBE_smpl2048_crp1_4rx:
            return (2048, 2048, 1)
        elif cube == RCUBE_smpl128_crp64_4rx:
            return (128, 64, 64)
        elif cube == RCUBE_smpl128_crp128_4rx:
            return (128, 64, 128)
        elif cube == RCUBE_smpl128_crp256_4rx:
            return (128, 64, 256)
        elif cube == RCUBE_smpl256_crp64_4rx:
            return (256, 128, 64)
        elif cube == RCUBE_smpl256_crp128_4rx:
            return (256, 128, 128)
        elif cube == RCUBE_smpl256_crp256_4rx:
            return (256, 128, 256)
        elif cube == RCUBE_smpl512_crp64_4rx:
            return (512, 256, 64)
        elif cube == RCUBE_smpl512_crp128_4rx:
            return (512, 256, 128)
        elif cube == RCUBE_smpl512_crp256_4rx:
            return (512, 256, 256)
        elif cube == RCUBE_smpl1024_crp64_4rx:
            return (1024, 512, 64)
        elif cube == RCUBE_smpl1024_crp128_4rx:
            return (1024, 512, 128)
        elif cube == RCUBE_smpl256_crp64_tdMimo_3tx_4rx:
            return (256, 128, 64)
        elif cube == RCUBE_smpl256_crp128_tdMimo_3tx_4rx:
            return (256, 128, 128)
        elif cube == RCUBE_smpl256_crp256_tdMimo_3tx_4rx:
            return (256, 128, 256)
        elif cube == RCUBE_smpl512_crp64_tdMimo_3tx_4rx:
            return (512, 256, 64)
        elif cube == RCUBE_smpl512_crp128_tdMimo_3tx_4rx:
            return (512, 256, 128)
        elif cube == RCUBE_smpl1024_crp64_tdMimo_3tx_4rx:
            return (1024, 512, 64)

        return (-1, -1, -1)

    def getMaxNumRxChan(self):
        if self._isMIMO:
            return MAX_RX_CHAN
        else:
            return MAX_RX_CHAN_MIMO

    def getNumActiveRxChan(self):
        if self._isMIMO:
            return bin(self.RxChannels & 0xFFF).count("1")
        else:
            return bin(self.RxChannels & 0xF).count("1")

    def print(self):
        print("\t\t\t\tRadarCube", self.RadarCube)
        print("\t\t\t\tContinuousMeas", self.ContinuousMeas)
        print("\t\t\t\tMeasInterval", self.MeasInterval)
        print("\t\t\t\tProcessing", self.Processing)
        print("\t\t\t\tRangeWinFunc", self.RangeWinFunc)
        print("\t\t\t\tDopplerWinFunc", self.DopplerWinFunc)
        print("\t\t\t\tDopplerFftShift", self.DopplerFftShift)
        print("\t\t\t\tMinRangeBin", self.MinRangeBin)
        print("\t\t\t\tMaxRangeBin", self.MaxRangeBin)
        print("\t\t\t\tMinDopplerBin", self.MinDopplerBin)
        print("\t\t\t\tMaxDopplerBin", self.MaxDopplerBin)
        print("\t\t\t\tCfarWindowSize", self.CfarWindowSize)
        print("\t\t\t\tCfarGuardInt", self.CfarGuardInt)
        print("\t\t\t\tRangeCfarThresh", self.RangeCfarThresh)
        print("\t\t\t\tTriggerThresh", self.TriggerThresh)
        print("\t\t\t\tPeakSearchThresh", self.PeakSearchThresh)
        print("\t\t\t\tSuppressStaticTargets", self.SuppressStaticTargets)
        print("\t\t\t\tMaxTargets", self.MaxTargets)
        print("\t\t\t\tMaxTracks", self.MaxTracks)
        print("\t\t\t\tMaxHorSpeed", self.MaxHorSpeed)
        print("\t\t\t\tMaxVerSpeed", self.MaxVerSpeed)
        print("\t\t\t\tMaxAccel", self.MaxAccel)
        print("\t\t\t\tMaxRangeError", self.MaxRangeError)
        print("\t\t\t\tMinConfirm", self.MinConfirm)
        print("\t\t\t\tTargetSize", self.TargetSize)
        print("\t\t\t\tMergeLimit", self.MergeLimit)
        print("\t\t\t\tSectorFiltering", self.SectorFiltering)
        print("\t\t\t\tSpeedEstimation", self.SpeedEstimation)
        print("\t\t\t\tDspDopplerProc", self.DspDopplerProc)
        print("\t\t\t\tRxChannels", self.RxChannels)
        print("\t\t\t\tCfarSelect", self.CfarSelect)
        print("\t\t\t\tDopplerCfarThresh", self.DopplerCfarThresh)

        print("\t\t\t\t#####")
        spc, rbs, dbs = self.getCubeBins(self.RadarCube)
        print("\t\t\t\tADC samples per chirp:", spc)
        print("\t\t\t\tRange bins:", rbs)
        print("\t\t\t\tDoppler bins:", dbs)

        print("\t\t\t\t#####")
        print("\t\t\t\tActive range bins:", self._ActiveRangeBins)
        print("\t\t\t\tActive doppler bins:", self._ActiveDopplerBins)
