from typing import List


class EnetStreamConfig(object):
    "Stream configuration parameters to start a certain Ethernet stream"
    TYPE_TCP = 1
    TYPE_UDP = 2
    DATA_MODE_SINGLE = 0
    DATA_MODE_MULTIPLE = 1
    MEAS_MODE_CONT = 0
    MEAS_MODE_TRIGGERED_START = 1
    MEAS_MODE_TRIGGERED_MEAS = 2

    def __init__(
        self,
        IP_str: str = "",
        Port: int = -1,
        OwnPort: int = -1,
        EnetType: int = TYPE_UDP,
        DataMode: int = 0,
        MeasMode: int = 0,
        Mask: int = 0,
        Delays: List[int] = [0, 0, 0, 0],
    ) -> None:
        self.IP = IP_str
        self.Port = Port
        self.OwnPort = OwnPort
        self.EnetType = EnetType
        self.DataMode = DataMode
        self.MeasMode = MeasMode
        self.Delays = Delays
        self.Mask = Mask
        self.DataMask = 0
        self.ChirpRaw = 0
        self.ChirpRange = 0
        self.RangeBin = 0
        self.DopplerFormat = 0

    def getIpAsList(self) -> List[int]:
        return [int(val) for val in self.IP.split(".")]
