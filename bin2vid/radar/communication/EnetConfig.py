"""
Created on 31.07.2018

@author: rainer.jetten

Interfaces for TCP and UDP Ethernet
"""


class EnetConfig(object):
    "Configuration parameters that can be used for both Ethernet interfaces"

    def __init__(
        self, IP_str: str = "", Port: int = -1, OwnPort: int = -1, UdpBcPort: int = -1, Timeout: int = 30
    ) -> None:
        self.IP = IP_str
        self.Port = Port
        self.OwnPort = OwnPort
        self.UdpBcPort = UdpBcPort
        self.Timeout = Timeout
