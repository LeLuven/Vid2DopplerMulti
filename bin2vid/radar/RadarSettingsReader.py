import json
from dataclasses import dataclass
from typing import Any
from typing import Dict
from typing import Tuple

from radar.communication.FrontendParameters import FrontendParameters
from radar.communication.RadarParameters import RadarParameters


@dataclass
class RadarSettings:
    frontend: FrontendParameters
    radar: RadarParameters

    def max_mag(self) -> int:
        return 85

    # TODO determine value range for display
    def vmin(self) -> float:
        return 5

    def vmax(self) -> float:
        return 60

    def active_bins(self) -> Tuple[int, int]:
        _, _rbs, dbs = self.radar.getCubeBins(self.radar.RadarCube)

        min_rb: int = self.radar.MinRangeBin
        max_rb: int = self.radar.MaxRangeBin
        min_db: int = self.radar.MinDopplerBin
        max_db: int = self.radar.MaxDopplerBin

        min_db += dbs // 2
        max_db += dbs // 2

        a_rbs = max_rb - min_rb + 1
        a_dbs = max_db - min_db + 1

        return a_rbs, a_dbs


class RadarSettingsReader:
    @staticmethod
    def read(path: str) -> RadarSettings:
        with open(path, "r", encoding="utf8") as file:
            settings = json.load(file)

        frontend = FrontendParameters()
        frontend.MinFrequency = settings["Frontend"]["MinFrequency"]
        frontend.MaxFrequency = settings["Frontend"]["MaxFrequency"]
        frontend.SignalType = settings["Frontend"]["SignalType"]
        frontend.RxChannelSelection = settings["Frontend"]["RxChannelSelection"]
        frontend.TxChannelSelection = settings["Frontend"]["TxChannelSelection"]
        frontend.TxPowerSetting = settings["Frontend"]["TxPowerSetting"]
        frontend.RxPowerSetting = settings["Frontend"]["RxPowerSetting"]
        frontend.RampInit = settings["Frontend"]["RampInit"]
        frontend.RampTime = settings["Frontend"]["RampTime"]
        frontend.RampReset = settings["Frontend"]["RampReset"]
        frontend.RampDelay = settings["Frontend"]["RampDelay"]
        frontend.PowerSaving = settings["Frontend"]["PowerSaving"]
        frontend.AdcFrequency = settings["Frontend"]["AdcFrequency"]
        frontend.DcSuppression = settings["Frontend"]["DcSuppression"]
        frontend.RangeOffset = settings["Frontend"]["RangeOffset"]

        radar = RadarParameters()
        radar.RadarCube = settings["RadarProcessing"]["RadarCube"]
        radar.ContinuousMeas = settings["RadarProcessing"]["ContinuousMeas"]
        radar.MeasInterval = settings["RadarProcessing"]["MeasInterval"]
        radar.Processing = settings["RadarProcessing"]["Processing"]
        radar.RangeWinFunc = settings["RadarProcessing"]["RangeWinFunc"]
        radar.DopplerWinFunc = settings["RadarProcessing"]["DopplerWinFunc"]
        radar.DopplerFftShift = settings["RadarProcessing"]["DopplerFftShift"]
        radar.MinRangeBin = settings["RadarProcessing"]["MinRangeBin"]
        radar.MaxRangeBin = settings["RadarProcessing"]["MaxRangeBin"]
        radar.MinDopplerBin = settings["RadarProcessing"]["MinDopplerBin"]
        radar.MaxDopplerBin = settings["RadarProcessing"]["MaxDopplerBin"]
        radar.CfarWindowSize = settings["RadarProcessing"]["CfarWindowSize"]
        radar.CfarGuardInt = settings["RadarProcessing"]["CfarGuardInt"]
        radar.RangeCfarThresh = settings["RadarProcessing"]["RangeCfarThresh"]
        radar.TriggerThresh = settings["RadarProcessing"]["TriggerThresh"]
        radar.PeakSearchThresh = settings["RadarProcessing"]["PeakSearchThresh"]
        radar.SuppressStaticTargets = settings["RadarProcessing"][
            "SuppressStaticTargets"
        ]
        radar.MaxTargets = settings["RadarProcessing"]["MaxTargets"]
        radar.MaxTracks = settings["RadarProcessing"]["MaxTracks"]
        radar.MaxHorSpeed = settings["RadarProcessing"]["MaxHorSpeed"]
        radar.MaxVerSpeed = settings["RadarProcessing"]["MaxVerSpeed"]
        radar.MaxAccel = settings["RadarProcessing"]["MaxAccel"]
        radar.MaxRangeError = settings["RadarProcessing"]["MaxRangeError"]
        radar.MinConfirm = settings["RadarProcessing"]["MinConfirm"]
        radar.TargetSize = settings["RadarProcessing"]["TargetSize"]
        radar.MergeLimit = settings["RadarProcessing"]["MergeLimit"]
        radar.SectorFiltering = settings["RadarProcessing"]["SectorFiltering"]
        radar.SpeedEstimation = settings["RadarProcessing"]["SpeedEstimation"]
        radar.DspDopplerProc = settings["RadarProcessing"]["DspDopplerProc"]
        radar.RxChannels = settings["RadarProcessing"]["RxChannels"]
        radar.CfarSelect = settings["RadarProcessing"]["CfarSelect"]
        radar.DopplerCfarThresh = settings["RadarProcessing"]["DopplerCfarThresh"]

        radar.updateInternals()

        settings = RadarSettings(frontend, radar)
        return settings

    def write(self, path: str, settings: RadarSettings):
        frontend = settings.frontend
        radar = settings.radar

        data: Dict[str, Dict[str, Any]] = {}
        data["RadarProcessing"] = {}
        data["Frontend"] = {}

        data["Frontend"]["MinFrequency"] = frontend.MinFrequency
        data["Frontend"]["MaxFrequency"] = frontend.MaxFrequency
        data["Frontend"]["SignalType"] = frontend.SignalType
        data["Frontend"]["RxChannelSelection"] = frontend.RxChannelSelection
        data["Frontend"]["TxChannelSelection"] = frontend.TxChannelSelection
        data["Frontend"]["TxPowerSetting"] = frontend.TxPowerSetting
        data["Frontend"]["RxPowerSetting"] = frontend.RxPowerSetting
        data["Frontend"]["RampInit"] = frontend.RampInit
        data["Frontend"]["RampTime"] = frontend.RampTime
        data["Frontend"]["RampReset"] = frontend.RampReset
        data["Frontend"]["RampDelay"] = frontend.RampDelay
        data["Frontend"]["PowerSaving"] = frontend.PowerSaving
        data["Frontend"]["AdcFrequency"] = frontend.AdcFrequency
        data["Frontend"]["DcSuppression"] = frontend.DcSuppression
        data["Frontend"]["RangeOffset"] = frontend.RangeOffset

        data["RadarProcessing"]["RadarCube"] = radar.RadarCube
        data["RadarProcessing"]["ContinuousMeas"] = radar.ContinuousMeas
        data["RadarProcessing"]["MeasInterval"] = radar.MeasInterval
        data["RadarProcessing"]["Processing"] = radar.Processing
        data["RadarProcessing"]["RangeWinFunc"] = radar.RangeWinFunc
        data["RadarProcessing"]["DopplerWinFunc"] = radar.DopplerWinFunc
        data["RadarProcessing"]["DopplerFftShift"] = radar.DopplerFftShift
        data["RadarProcessing"]["MinRangeBin"] = radar.MinRangeBin
        data["RadarProcessing"]["MaxRangeBin"] = radar.MaxRangeBin
        data["RadarProcessing"]["MinDopplerBin"] = radar.MinDopplerBin
        data["RadarProcessing"]["MaxDopplerBin"] = radar.MaxDopplerBin
        data["RadarProcessing"]["CfarWindowSize"] = radar.CfarWindowSize
        data["RadarProcessing"]["CfarGuardInt"] = radar.CfarGuardInt
        data["RadarProcessing"]["RangeCfarThresh"] = radar.RangeCfarThresh
        data["RadarProcessing"]["TriggerThresh"] = radar.TriggerThresh
        data["RadarProcessing"]["PeakSearchThresh"] = radar.PeakSearchThresh
        data["RadarProcessing"]["SuppressStaticTargets"] = radar.SuppressStaticTargets
        data["RadarProcessing"]["MaxTargets"] = radar.MaxTargets
        data["RadarProcessing"]["MaxTracks"] = radar.MaxTracks
        data["RadarProcessing"]["MaxHorSpeed"] = radar.MaxHorSpeed
        data["RadarProcessing"]["MaxVerSpeed"] = radar.MaxVerSpeed
        data["RadarProcessing"]["MaxAccel"] = radar.MaxAccel
        data["RadarProcessing"]["MaxRangeError"] = radar.MaxRangeError
        data["RadarProcessing"]["MinConfirm"] = radar.MinConfirm
        data["RadarProcessing"]["TargetSize"] = radar.TargetSize
        data["RadarProcessing"]["MergeLimit"] = radar.MergeLimit
        data["RadarProcessing"]["SectorFiltering"] = radar.SectorFiltering
        data["RadarProcessing"]["SpeedEstimation"] = radar.SpeedEstimation
        data["RadarProcessing"]["DspDopplerProc"] = radar.DspDopplerProc
        data["RadarProcessing"]["RxChannels"] = radar.RxChannels
        data["RadarProcessing"]["CfarSelect"] = radar.CfarSelect
        data["RadarProcessing"]["DopplerCfarThresh"] = radar.DopplerCfarThresh

        with open(path, "w", encoding="utf8") as file:
            json.dump(data, file, indent=4)
