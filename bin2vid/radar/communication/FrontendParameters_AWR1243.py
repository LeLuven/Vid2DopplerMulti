"""
Created on 15.07.2022

@author: IMST GmbH
"""

# possible tx signal modulations
ST_CwMinFrequency = 1
ST_CwMaxFrequency = 2
ST_FmcwUpRamp = 3
ST_FmcwDownRamp = 4
ST_FmcwUpDownRamp = 5
ST_FmcwDownUpRamp = 6


class FrontendParameters_AWR1243(FrontendParameters):
    Freq_Limits_kHz = (
        (76000000, 77000000),
        (77000000, 81000000),
    )  # limits for supported VCO bands
    Num_Tx = 3
    Num_Rx = 4

    def __init__(self):
        self.MinFrequency = self.Freq_Limits_kHz[0][0]  # [kHz]
        self.MaxFrequency = self.Freq_Limits_kHz[0][1]  # [kHz]
        self.SignalType = ST_FmcwUpRamp  # enum
        self.RxChannelSelection = 0xF  # bitmask
        self.TxChannelSelection = 0x1  # bitmask
        self.TxPowerSetting = 0  # attenuation enum: 0-11
        self.RxPowerSetting = 10  # gain enum 0-14
        self.RampInit = 0  # [ns] (ADC start delay), readonly
        self.RampTime = 70000  # [ns] (complete time of one chirp)
        self.RampReset = 0  # [ns] (excess time), readonly
        self.RampDelay = 0  # [ns] (idle time), readonly
        self.PowerSaving = 1  # power saving ON/OFF here
        self.AdcFrequency = (
            0  # ADC sampling rate, enum: 0=10MHz, 1=15MHz, 2=20MHz, 3=30MHz
        )
        self.DcSuppression = 60  # DC peak suppression [dB] (0-200)
        self.RangeOffset = 0  # reserve
