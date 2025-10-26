"""
Created on 06.01.2022

@author: IMST GmbH
"""

from time import sleep
from time import time
from typing import Any
from typing import Dict

from radar.communication.CommandError import CommandError
from radar.communication.CRC import CRC16
from radar.communication.EthernetParams import ENET_MAX_TCP_PORTS
from radar.communication.EthernetParams import ENET_MAX_UDP_PORTS
from radar.communication.EthernetParams import EthernetParams
from radar.communication.FrontendParameters import FrontendParameters
from radar.communication.InfoParameters import InfoParameters
from radar.communication.Interface import Interface
from radar.communication.RadarParameters import PROC_DopplerFFT
from radar.communication.RadarParameters import PROC_NoProcessing
from radar.communication.RadarParameters import PROC_RangeFFT
from radar.communication.RadarParameters import PROC_Tracking
from radar.communication.RadarParameters import RadarParameters
from radar.communication.RadarParameters import RCUBE_smpl2048_crp1_4rx

NUM_NN_LABELS = 8

CMD_GET_ERRORS = "CMD_GET_ERRORS"
CMD_GET_ERROR_LOGS = "CMD_GET_ERROR_LOGS"
CMD_RESET_ERROR_LOGS = "CMD_RESET_ERROR_LOGS"
CMD_GET_ERROR_LOG_TABLE = "CMD_GET_ERROR_LOG_TABLE"
CMD_RESET_ERROR_LOG_TABLE = "CMD_RESET_ERROR_LOG_TABLE"
CMD_INFO = "CMD_INFO"
CMD_GET_SYS_TIME = "CMD_GET_SYS_TIME"
CMD_GET_RADAR_PARAMS = "CMD_GET_RADAR_PARAMS"
CMD_SET_RADAR_PARAMS_NO_EEP = "CMD_SET_RADAR_PARAMS_NO_EEP"
CMD_GET_RADAR_RESOLUTION = "CMD_GET_RADAR_RESOLUTION"
CMD_GET_FRONTEND_PARAMS = "CMD_GET_FRONTEND_PARAMS"
CMD_SET_FRONTEND_PARAMS_NO_EEP = "CMD_SET_FRONTEND_PARAMS_NO_EEP"
CMD_GET_STREAM = "CMD_GET_STREAM"
CMD_START_ETHERNET_STREAM = "CMD_START_ETHERNET_STREAM"
CMD_STOP_ETHERNET_STREAM = "CMD_STOP_ETHERNET_STREAM"
CMD_GET_MULTI_DATA_STREAM = "CMD_GET_MULTI_DATA_STREAM"
CMD_CONFIGURE_STREAM = "CMD_CONFIGURE_STREAM"
CMD_TRIGGER_STREAM = "CMD_TRIGGER_STREAM"

# Command Return States
CMD_STATE_OK = 0x0000
CMD_STATE_CRC_ERROR = 0x0001
CMD_STATE_WRONG_RX_DATA = 0x0002  # received data was not ok
CMD_STATE_MEAS_TIMEOUT = (
    0x0004  # measurement took too long or wasn't performed by radar core
)
CMD_STATE_FE_ERROR = 0x0008  # problem with frontend (e.g. SPI communication)
CMD_STATE_FE_TEMP_ERROR = 0x0010  # frontend temperature error, so it was shutdown and no measurement was performed
CMD_STATE_ACUTE_GLOBAL_ERROR = 0x0100  # there is a global acute error pending
CMD_STATE_GLOBAL_ERROR_LOGGED = 0x0200  # a global error has been logged
CMD_STATE_FW_UPD_ERROR = 0x1000  # error during uploading firmware update

UNKNOWN_CMD_ID = 0xE0F0
ACK_SIZE = 4
CRC_SIZE = 2

RADAR_MAX_BUF_SIZE = 25 * 1024  # [bytes]


class Commands(object):
    def __init__(
        self,
        interface: Interface,
        useCrc,
    ) -> None:
        self.infoParams = InfoParameters()
        self.radarParams = RadarParameters()
        self.frontendParams = FrontendParameters()
        self.enetParams = EthernetParams()

        self.myInterface = interface

        self.useCrc = useCrc  # if True, CRC16 is used for data transmission, else not
        self.crc16 = CRC16()

        self.cmd_list = {}
        self.cmd_list[CMD_GET_ERRORS] = (0xE000, self.cmd_getErrors)
        self.cmd_list[CMD_GET_ERROR_LOGS] = (0xE001, self.cmd_getErrorLogs)
        self.cmd_list[CMD_RESET_ERROR_LOGS] = (0xE002, self.cmd_resetErrorLogs)
        self.cmd_list[CMD_GET_ERROR_LOG_TABLE] = (0xE003, self.cmd_getErrorLogTable)
        self.cmd_list[CMD_RESET_ERROR_LOG_TABLE] = (0xE004, self.cmd_resetErrorLogTable)

        self.cmd_list[CMD_INFO] = (0x0001, self.cmd_getInfo)
        self.cmd_list[CMD_GET_SYS_TIME] = (0x0003, self.cmd_getSysTime)

        self.cmd_list[CMD_GET_RADAR_PARAMS] = (0x000A, self.cmd_getRadarParams)
        self.cmd_list[CMD_SET_RADAR_PARAMS_NO_EEP] = (0x800B, self.cmd_setRadarParams)
        self.cmd_list[CMD_GET_RADAR_RESOLUTION] = (0x000D, self.cmd_getRadarResolution)

        self.cmd_list[CMD_GET_FRONTEND_PARAMS] = (0x0010, self.cmd_getFrontendParams)
        self.cmd_list[CMD_SET_FRONTEND_PARAMS_NO_EEP] = (
            0x8011,
            self.cmd_setFrontendParams,
        )

        self.cmd_list[CMD_GET_STREAM] = (0x0023, self.cmd_getStream)
        self.cmd_list[CMD_START_ETHERNET_STREAM] = (
            0x0024,
            self.cmd_startEthernetStream,
        )
        self.cmd_list[CMD_STOP_ETHERNET_STREAM] = (0x0025, self.cmd_stopEthernetStream)
        self.cmd_list[CMD_GET_MULTI_DATA_STREAM] = (0x0027, self.cmd_getMultiDataStream)
        self.cmd_list[CMD_CONFIGURE_STREAM] = (0x0028, self.cmd_configureStream)
        self.cmd_list[CMD_TRIGGER_STREAM] = (0x0029, self.cmd_triggerStream)

        self.curCmdCode = None  # to save current used command code for comparison
        self.stateRcvd = 0  # to save current received radar state for later

    def paramsAccepted(self) -> bool:
        return self.stateRcvd & CMD_STATE_WRONG_RX_DATA == 0

    def hasRadarError(self) -> int:
        return self.stateRcvd & (
            CMD_STATE_ACUTE_GLOBAL_ERROR | CMD_STATE_GLOBAL_ERROR_LOGGED
        )

    def setInterface(self, interface: Interface) -> None:
        self.myInterface = interface

    def getInterface(self) -> Interface:
        return self.myInterface

    def executeCmd(self, cmdID, *opt) -> Any:
        if self.myInterface is None:
            raise CommandError("No interface defined")
        # get cmd ID string if int was entered
        if type(cmdID) == int:
            for cmd in self.cmd_list.keys():
                if self.cmd_list[cmd][0] == cmdID:
                    cmdID = cmd
        if cmdID not in self.cmd_list:
            raise CommandError("Invalid command ID: {}".format(cmdID))
        # Get command code and function
        code, func = self.cmd_list[cmdID]
        # save code for comparison
        self.curCmdCode = code
        # reset state
        self.stateRcvd = 0
        # Clear TX and RX buffer
        self.myInterface.clearBuffer()
        # Add command code to TX buffer
        self.myInterface.TxU16(code)
        # Perform command
        ret = func(*opt)
        # check returned state
        self.onRadarState()
        return ret

    def onRadarState(self):
        if self.stateRcvd & CMD_STATE_CRC_ERROR:
            raise CommandError("CRC error returned by Command 0x%X" % self.curCmdCode)
        elif self.stateRcvd & CMD_STATE_MEAS_TIMEOUT:
            raise CommandError("Measurement Timeout in Command 0x%X" % self.curCmdCode)
        elif self.stateRcvd & CMD_STATE_FW_UPD_ERROR:
            raise CommandError(
                "Firmware Update Error in Command 0x%X" % self.curCmdCode
            )

    def Transmit(self) -> None:
        "Wrapper for interface transmit function"
        if self.useCrc:  # calculate CRC if enabled
            self.crc16.reset()
            self.crc16.process_buf(
                self.myInterface.getTxBuf(), self.myInterface.getTxCount()
            )
            # insert CRC value at the end, no further Tx function should be called because counter wasn't increased
            crc_bytes = self.crc16.get_crc_value_as_byte_list()
            self.myInterface.TxU8(crc_bytes[0])
            self.myInterface.TxU8(crc_bytes[1])
        self.myInterface.Transmit(False)  # TODO: always reopen interface?

    def Receive(self, rxLen, withAck=True, withCRC=True, checkCRC=True, lessOk=False):
        # Wrapper for interface receive function which always reads ACK and state
        # rxLen : number of bytes expected
        # withAck : if True an acknowledge is expected. In case CRC is used, it will
        # be reset and expected. If False it can be useful for multiple calls of Receive in commands.
        # withCRC : if CRC is enabled this flag determines if a CRC should be expected
        # at the end or not.
        # checkCRC : only used if CRC is enabled, if False it will not be checked
        # lessOk: if True, less than requested bytes are Ok also (Ethernet)
        nRx = rxLen
        nAdd = 0
        if withAck:
            nAdd += ACK_SIZE
        if self.useCrc and withCRC:
            nAdd += CRC_SIZE
        rL = self.myInterface.Receive(nRx + nAdd, closeInterface=False, lessOk=lessOk)

        if not lessOk and rL < nRx:
            if rL == nAdd:
                # maybe measurement timeout
                cmdId = self.myInterface.RxU16()
                self.stateRcvd = self.myInterface.RxU16()
                self.onRadarState()
            raise Exception(self.myInterface.getErrorString())

        # calculate and check CRC value if enabled
        if self.useCrc:
            if withAck:  # only reset on start of command
                self.crc16.reset()

            if checkCRC:  # enable checking if it is the only or last call of Receive
                self.crc16.process_buf(
                    self.myInterface.getRxBuf(), self.myInterface.getNumReceived()
                )
                if self.crc16.get_crc_value() != 0:
                    raise CommandError("CRC Error (Receive)")

        # read acknowledge and state word if enabled
        if withAck:
            cmdId = self.myInterface.RxU16()
            self.stateRcvd = self.myInterface.RxU16()
            rL -= ACK_SIZE
            if cmdId != self.curCmdCode:
                if cmdId == UNKNOWN_CMD_ID:
                    raise CommandError(
                        "Radar does not know command: {}".format(hex(self.curCmdCode))
                    )
                else:
                    raise CommandError(
                        "Command returned wrong ID! Sent: {}, Received: {}".format(
                            hex(self.curCmdCode), hex(cmdId)
                        )
                    )

        if withCRC:
            rL -= CRC_SIZE

        # not received desired number of bytes, check for state here which could raise exception
        if rxLen > 0 and not lessOk and rL < rxLen:
            self.onRadarState()
            # no state error? raise another exception
            raise Exception("Wrong data length.")
        return rL

    def Transceive(self, rxLen=0, delaySeconds=0.0, rxLessOk=False) -> Any:
        self.Transmit()
        if delaySeconds > 0:
            sleep(delaySeconds)
        return self.Receive(rxLen, lessOk=rxLessOk)

    def cmd_getErrors(self):
        self.Transceive(34)  # (1+16)*2

        gMask = self.myInterface.RxU16()
        masks = []
        for _ in range(16):
            masks.append(self.myInterface.RxU16())
        return (gMask, masks)

    def cmd_getErrorLogs(self):
        self.Transceive(34)  # (1+16)*2

        gMask = self.myInterface.RxU16()
        masks = []
        for _ in range(16):
            masks.append(self.myInterface.RxU16())
        return (gMask, masks)

    def cmd_resetErrorLogs(self, resetMask=0xFFFF) -> None:
        self.myInterface.TxU16(resetMask)
        self.Transceive()

    def cmd_getErrorLogTable(self):
        nMin = 2
        rl = self.Transceive(
            100 * (8 + 2) + 2, rxLessOk=True
        )  # just try read whole table
        if rl < nMin:
            raise CommandError("Expected at least %d bytes!" % nMin)
        nErr = self.myInterface.RxU16()

        errLog = []
        for _ in range(nErr):
            errLog.append(
                (self.myInterface.RxU64(), self.myInterface.RxU16())
            )  # time [ms], error

        return errLog

    def cmd_resetErrorLogTable(self) -> None:
        self.Transceive()

    def cmd_getInfo(self) -> InfoParameters:
        self.Transceive(5 * 4)
        self.infoParams.deviceNumber = self.myInterface.RxU32()
        self.infoParams.frontendConnected = self.myInterface.RxU32()
        self.infoParams.fwVersion = self.myInterface.RxU32()
        self.infoParams.fwRevision = self.myInterface.RxU32()
        self.infoParams.fwDate = self.myInterface.RxU32()

        return self.infoParams

    def cmd_getSysTime(self) -> Any:
        self.Transceive(8)
        return self.myInterface.RxU64()

    def cmd_getRadarParams(self) -> RadarParameters:
        rp = self.radarParams
        self.Transceive(60)
        rp.RadarCube = self.myInterface.RxU16()
        rp.ContinuousMeas = self.myInterface.RxU8()
        rp.MeasInterval = self.myInterface.RxU16()
        rp.Processing = self.myInterface.RxU16()
        rp.RangeWinFunc = self.myInterface.RxU16()
        rp.DopplerWinFunc = self.myInterface.RxU16()
        rp.DopplerFftShift = self.myInterface.RxU8()
        rp.MinRangeBin = self.myInterface.RxU16()
        rp.MaxRangeBin = self.myInterface.RxU16()
        rp.MinDopplerBin = self.myInterface.RxI16()
        rp.MaxDopplerBin = self.myInterface.RxI16()
        rp.CfarWindowSize = self.myInterface.RxU16()
        rp.CfarGuardInt = self.myInterface.RxU16()
        rp.RangeCfarThresh = self.myInterface.RxU16()
        rp.TriggerThresh = self.myInterface.RxI16()  # !
        rp.PeakSearchThresh = self.myInterface.RxU16()
        rp.SuppressStaticTargets = self.myInterface.RxU16()
        rp.MaxTargets = self.myInterface.RxU16()
        rp.MaxTracks = self.myInterface.RxU16()
        rp.MaxHorSpeed = self.myInterface.RxU16()
        rp.MaxVerSpeed = self.myInterface.RxU16()
        rp.MaxAccel = self.myInterface.RxU16()
        rp.MaxRangeError = self.myInterface.RxU16()
        rp.MinConfirm = self.myInterface.RxU16()
        rp.TargetSize = self.myInterface.RxU16()
        rp.MergeLimit = self.myInterface.RxU16()
        rp.SectorFiltering = self.myInterface.RxU8()
        rp.SpeedEstimation = self.myInterface.RxU16()
        rp.DspDopplerProc = self.myInterface.RxU8()
        rp.RxChannels = self.myInterface.RxU16()
        rp.CfarSelect = self.myInterface.RxU16()
        rp.DopplerCfarThresh = self.myInterface.RxU16()
        rp.updateInternals()
        return rp

    def cmd_setRadarParams(self, rp: RadarParameters = None) -> None:
        update = True
        if rp is None:
            update = False
            rp = self.radarParams

        self.myInterface.TxU16(rp.RadarCube)
        self.myInterface.TxU8(rp.ContinuousMeas)
        self.myInterface.TxU16(rp.MeasInterval)
        self.myInterface.TxU16(rp.Processing)
        self.myInterface.TxU16(rp.RangeWinFunc)
        self.myInterface.TxU16(rp.DopplerWinFunc)
        self.myInterface.TxU8(rp.DopplerFftShift)
        self.myInterface.TxU16(rp.MinRangeBin)
        self.myInterface.TxU16(rp.MaxRangeBin)
        self.myInterface.TxI16(rp.MinDopplerBin)
        self.myInterface.TxI16(rp.MaxDopplerBin)
        self.myInterface.TxU16(rp.CfarWindowSize)
        self.myInterface.TxU16(rp.CfarGuardInt)
        self.myInterface.TxU16(rp.RangeCfarThresh)
        self.myInterface.TxI16(rp.TriggerThresh)  # !
        self.myInterface.TxU16(rp.PeakSearchThresh)
        self.myInterface.TxU16(rp.SuppressStaticTargets)
        self.myInterface.TxU16(rp.MaxTargets)
        self.myInterface.TxU16(rp.MaxTracks)
        self.myInterface.TxU16(rp.MaxHorSpeed)
        self.myInterface.TxU16(rp.MaxVerSpeed)
        self.myInterface.TxU16(rp.MaxAccel)
        self.myInterface.TxU16(rp.MaxRangeError)
        self.myInterface.TxU16(rp.MinConfirm)
        self.myInterface.TxU16(rp.TargetSize)
        self.myInterface.TxU16(rp.MergeLimit)
        self.myInterface.TxU8(rp.SectorFiltering)
        self.myInterface.TxU16(rp.SpeedEstimation)
        self.myInterface.TxU8(rp.DspDopplerProc)
        self.myInterface.TxU16(rp.RxChannels)
        self.myInterface.TxU16(rp.CfarSelect)
        self.myInterface.TxU16(rp.DopplerCfarThresh)
        self.Transceive()

        if update:
            self.radarParams.__dict__.update(rp.__dict__)

    def cmd_resetRadarParams(self) -> None:
        self.Transceive()

    def cmd_getRadarResolution(self) -> Dict[str, Any]:
        self.Transceive(4 * 4)
        res = {}
        res["If"] = self.myInterface.RxFloat()
        res["Range"] = self.myInterface.RxFloat()
        res["Doppler"] = self.myInterface.RxFloat()
        res["Speed"] = self.myInterface.RxFloat()
        return res

    def cmd_getFrontendParams(self) -> FrontendParameters:
        fp = self.frontendParams
        self.Transceive(42)
        fp.MinFrequency = self.myInterface.RxU32()
        fp.MaxFrequency = self.myInterface.RxU32()
        fp.SignalType = self.myInterface.RxU16()
        fp.TxChannelSelection = self.myInterface.RxU16()
        fp.RxChannelSelection = self.myInterface.RxU16()
        fp.TxPowerSetting = self.myInterface.RxI16()
        fp.RxPowerSetting = self.myInterface.RxI16()
        fp.RampInit = self.myInterface.RxU32()
        fp.RampTime = self.myInterface.RxU32()
        fp.RampReset = self.myInterface.RxU32()
        fp.RampDelay = self.myInterface.RxU32()
        fp.PowerSaving = self.myInterface.RxI16()
        fp.AdcFrequency = self.myInterface.RxI16()
        fp.DcSuppression = self.myInterface.RxI16()
        fp.RangeOffset = self.myInterface.RxI16()
        return fp

    def cmd_setFrontendParams(self, fp: FrontendParameters = None) -> None:
        update = True
        if fp is None:
            fp = self.frontendParams
            update = False

        self.myInterface.TxU32(fp.MinFrequency)
        self.myInterface.TxU32(fp.MaxFrequency)
        self.myInterface.TxU16(fp.SignalType)
        self.myInterface.TxU16(fp.TxChannelSelection)
        self.myInterface.TxU16(fp.RxChannelSelection)
        self.myInterface.TxI16(fp.TxPowerSetting)
        self.myInterface.TxI16(fp.RxPowerSetting)
        self.myInterface.TxU32(fp.RampInit)
        self.myInterface.TxU32(fp.RampTime)
        self.myInterface.TxU32(fp.RampReset)
        self.myInterface.TxU32(fp.RampDelay)
        self.myInterface.TxI16(fp.PowerSaving)
        self.myInterface.TxI16(fp.AdcFrequency)
        self.myInterface.TxI16(fp.DcSuppression)
        self.myInterface.TxI16(fp.RangeOffset)
        self.Transceive()

        if update:
            self.frontendParams.__dict__.update(fp.__dict__)

    def cmd_resetFrontendParams(self) -> None:
        self.Transceive()

    def cmd_getStream(self, mask=0, opt=0) -> None:
        self.myInterface.TxU16(mask)
        self.myInterface.TxU16(opt)
        self.Transceive()

    def cmd_getMultiDataStream(
        self, mask, dataMask, chirp, rangeBin, dopplerFormat
    ) -> None:
        self.myInterface.TxU16(mask)
        self.myInterface.TxU16(dataMask)
        self.myInterface.TxU16(chirp)
        self.myInterface.TxU16(rangeBin)
        self.myInterface.TxU16(dopplerFormat)
        self.Transceive()

    def cmd_configureStream(self, streamCfg) -> None:
        self.myInterface.TxU16(streamCfg.DataMode)
        self.myInterface.TxU16(streamCfg.MeasMode)
        for d in streamCfg.Delays:
            self.myInterface.TxU32(d)
        self.myInterface.TxU16(streamCfg.Mask)
        self.myInterface.TxU16(streamCfg.DataMask)
        self.myInterface.TxU16(streamCfg.ChirpRange)
        self.myInterface.TxU16(streamCfg.RangeBin)
        self.myInterface.TxU16(streamCfg.DopplerFormat)
        self.Transceive()

    def cmd_triggerStream(self, newTime=None, timeMode=0, delayIndex=0) -> None:
        if newTime is None:
            newTime = int(time() * 1000)
        else:
            newTime = int(newTime)

        self.myInterface.TxU64(newTime)
        self.myInterface.TxU16(timeMode)
        self.myInterface.TxU16(delayIndex)
        self.Transceive()

    def cmd_startEthernetStream(self, streamCfg) -> None:
        opt = 0
        if self.radarParams.Processing == PROC_NoProcessing:
            opt = streamCfg.ChirpRaw
        elif self.radarParams.Processing == PROC_RangeFFT:
            opt = streamCfg.ChirpRange
        elif self.radarParams.Processing == PROC_DopplerFFT:
            opt = streamCfg.RangeBin
        elif self.radarParams.Processing == PROC_Tracking:
            opt = streamCfg.DopplerFormat

        self.myInterface.TxU16(streamCfg.Mask)
        self.myInterface.TxU16(opt)
        self.myInterface.TxU16(streamCfg.EnetType)
        self.myInterface.TxU16(streamCfg.Port)
        for val in streamCfg.getIpAsList():
            self.myInterface.TxU8(val)
        self.myInterface.TxU16(streamCfg.OwnPort)
        self.Transceive()

    def cmd_stopEthernetStream(self, portType: int = 3, port: int = 0) -> None:
        self.myInterface.TxU16(portType)
        self.myInterface.TxU16(port)
        self.Transceive()
