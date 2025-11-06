"""
Created on 31.07.2018

@author: rainer.jetten

Interfaces for TCP and UDP Ethernet
"""

import socket

from radar.communication.EnetConfig import EnetConfig
from radar.communication.Interface import Interface


class EnetUdpInterface(Interface):
    def __init__(self, enetConfig: EnetConfig):
        Interface.__init__(self, name="EthernetUdpInterface", interfaceType="Ethernet")

        self.config = enetConfig

        self.socket = None
        self._opened = False

        self.hostIp = ""
        self.hostPort = 0

    def Open(self) -> bool:
        "Open UDP socket"
        self.resetErrors()
        try:
            self.Close()
            self.socket = socket.socket(
                socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP
            )
            self.socket.settimeout(self.config.Timeout)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(("", self.config.OwnPort))
            self._opened = True
        except Exception as E:
            self.errorCode |= self.ERR_IF_OPEN
            self.errorString = "Error while opening UDP socket: " + str(E)
            self.Close()
        return self._opened

    def __del__(self) -> None:
        self.Close()

    def Close(self) -> None:
        if self.socket is not None:
            # self.socket.shutdown(socket.SHUT_RDWR) # TODO check if this is okay
            self.socket.close()
            self.socket = None
        self._opened = False

    def IsOpen(self) -> bool:
        return self._opened

    def Write(self, data) -> int:
        return self.socket.sendto(data, (self.config.IP, self.config.Port))

    def Read(self, n: int) -> bytes:
        data, address = self.socket.recvfrom(n)
        self.hostIp, self.hostPort = address
        return data
