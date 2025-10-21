"""
Created on 31.07.2018

@author: rainer.jetten

Interfaces for TCP and UDP Ethernet
"""

import socket

from radar.communication.EnetConfig import EnetConfig
from radar.communication.Interface import Interface


class EnetTcpInterface(Interface):
    def __init__(self, enetConfig: EnetConfig) -> None:
        Interface.__init__(self, name="EthernetTcpInterface", interfaceType="Ethernet")

        self.config = enetConfig

        self.socket = None
        self._opened = False

    def Open(self) -> bool:
        "Open TCP connection"
        self.resetErrors()
        try:
            self.Close()
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.config.Timeout)
            self.socket.connect((self.config.IP, self.config.Port))
            self._opened = True
        except Exception as E:
            self.errorCode |= self.ERR_IF_OPEN
            self.errorString = "TCP connect error: " + str(E)
            self.Close()
        return self._opened

    def __del__(self) -> None:
        self.Close()

    def Close(self) -> None:
        if self.socket is not None:
            try:
                # self.socket.shutdown(socket.SHUT_RDWR)
                self.socket.close()
                self.socket = None
            except:
                pass
        self._opened = False

    def IsOpen(self) -> bool:
        return self._opened

    def Write(self, data) -> int:
        return self.socket.send(data)

    def Read(self, n: int) -> bytes:
        return self.socket.recv(n)
