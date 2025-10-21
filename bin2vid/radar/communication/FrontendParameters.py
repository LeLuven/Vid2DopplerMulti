"""
Created on 15.07.2022

@author: IMST GmbH
"""

C0 = 299792458  # [m/s]


# Base class for frontend parameters. Each frontend should use it.
class FrontendParameters(object):
    def __init__(self):
        self.MinFrequency = 0
        self.MaxFrequency = 1
        self.SignalType = 0
        self.RxChannelSelection = 0x0
        self.TxChannelSelection = 0x0
        self.TxPowerSetting = 0
        self.RxPowerSetting = 0
        self.RampInit = 0
        self.RampTime = 0
        self.RampReset = 0
        self.RampDelay = 0
        self.PowerSaving = 0
        self.AdcFrequency = 0
        self.DcSuppression = 0
        self.RangeOffset = 0

    def checkValues(self):
        raise Exception("Method not implemented!")

    def getChirpTime(self):
        return (
            self.RampInit + self.RampTime + self.RampReset + self.RampDelay
        ) * 1e-9  # [s]

    def getRangeResolution(self):
        div = 2.0 * (self.MaxFrequency - self.MinFrequency) * 1e3
        if div == 0.0:
            return 1.0

        return C0 / div  # [m]

    def getDopplerResolution(self, numChirps):
        div = self.getChirpTime() * numChirps
        if div == 0.0:
            return 1.0

        return 1.0 / div  # [Hz]

    def getSpeedResolution(self, numChirps):
        f0 = (self.MinFrequency + self.MaxFrequency) / 2 * 1e3  # [Hz]
        div = 2.0 * f0 * self.getChirpTime() * numChirps
        if div == 0.0:
            return 1.0

        return C0 / div  # [m/s]

    def getIfResolution(self):
        chirpTime = self.getChirpTime()
        if chirpTime == 0:
            return 1

        return 1.0 / chirpTime  # [Hz]

    def print(self, radarParams):
        print("\t\t\t\tStart frequency [kHz]:", self.MinFrequency)
        print("\t\t\t\tStop frequency [kHz]:", self.MaxFrequency)
        print("\t\t\t\tSignalType", self.SignalType)
        print("\t\t\t\tRxChannelSelection", self.RxChannelSelection)
        print("\t\t\t\tTxChannelSelection", self.TxChannelSelection)
        print("\t\t\t\tTxPowerSetting", self.TxPowerSetting)
        print("\t\t\t\tRxPowerSetting", self.RxPowerSetting)
        print("\t\t\t\tRampInit", self.RampInit)
        print("\t\t\t\tRampTime", self.RampTime)
        print("\t\t\t\tRampReset", self.RampReset)
        print("\t\t\t\tRampDelay", self.RampDelay)
        print("\t\t\t\tPowerSaving", self.PowerSaving)
        print("\t\t\t\tAdcFrequency", self.AdcFrequency)
        print("\t\t\t\tDcSuppression", self.DcSuppression)
        print("\t\t\t\tRangeOffset", self.RangeOffset)

        print("\t\t\t\t#####")
        print("\t\t\t\tTime of one chirp [us]:", round(self.getChirpTime() * 1e6, 3))
        print("\t\t\t\tRange resolution [m]:", round(self.getRangeResolution(), 3))
        speed_resolution = self.getSpeedResolution(radarParams._NumDopplerBins)
        print("\t\t\t\tSpeed resolution [m/s]:", round(speed_resolution, 3))
