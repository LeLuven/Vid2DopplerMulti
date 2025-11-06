"""
Created on 30.07.2018

@author: IMST GmbH

Interface baseclass that must be implemented and extended by every other interface
"""

import struct
from time import sleep

BUFFER_FACTOR = 2
DEFAULT_TX_BUF_SIZE = BUFFER_FACTOR * 4096
DEFAULT_RX_BUF_SIZE = BUFFER_FACTOR * 1024 * 1024
DEBUG = True


class Interface(object):
    """
    Interface class which should be implemented by interfaces.
    TX data is stored in a buffer until send function is used.
    After receive function all Byte data is stored in RX buffer and can be converted by given methods.
    Send, receive and transceive functions must be implemented by the new interface.
    Also Open/Close functions
    """

    # general error codes
    ERR_IF_OPEN = 2**0
    ERR_IF_TRANSMIT_1 = 2**1
    ERR_IF_TRANSMIT_2 = 2**2
    ERR_IF_RECEIVE_1 = 2**3
    ERR_IF_RECEIVE_2 = 2**4

    def __init__(
        self,
        txBufSize: int = DEFAULT_TX_BUF_SIZE,
        rxBufSize: int = DEFAULT_RX_BUF_SIZE,
        txBuf=None,
        rxBuf=None,
        minBytes=1,
        name="",
        interfaceType="",
    ) -> None:
        if txBuf is None:
            self.__txBuf = bytearray(txBufSize)
            self.__txBufSize = txBufSize
        else:
            self.__txBuf = txBuf
            self.__txBufSize = len(txBuf)
        self.__txCnt = 0
        self.__txSent = 0
        if rxBuf is None:
            self.__rxBuf = bytearray(rxBufSize)
            self.__rxBufSize = rxBufSize
        else:
            self.__rxBuf = rxBuf
            self.__rxBufSize = len(rxBuf)
        self.__rxRead = 0
        self.__rxWrite = 0
        self._minBytes = minBytes  # determines smallest amount to put in buffer, if >1 zero bytes are padded (e.g. for 16-bit USB)
        self._fixedDelay = 0
        self._name = name
        self._interfaceType = interfaceType
        self.errorCode = 0
        self.errorString = ""  # string for last occurred error

    def SetTxBufSize(self, size: int) -> None:
        self.__txBuf = bytearray(size)
        self.__txBufSize = size
        self.__txCnt = 0

    def GetTxBufSize(self) -> int:
        return self.__txBufSize

    def SetRxBufSize(self, size: int) -> None:
        self.__rxBuf = bytearray(size)
        self.__rxBufSize = size
        self.__rxRead = 0
        self.__rxWrite = 0

    def GetRxBufSize(self):
        return self.__rxBufSize

    def Open(self):
        raise Exception(
            "Here the initialization should be added e.g. open a socket or com port"
        )

    def Close(self):
        raise Exception("Here the interface should be closed")

    def IsOpen(self):
        raise Exception("Here open/connect state should be returned")

    def Write(self, data):
        raise Exception("Here the interface byte sending function should be")

    def Read(self, n):
        raise Exception("Here the interface byte reading function should be")

    def Transmit(self, openInterface=False):
        # Transmit TX buffer content
        if openInterface:
            ret = self.Open()
            if ret is None:
                self.errorCode |= self.ERR_IF_OPEN
                self.errorString = (
                    "Interface Error: Open method not implemented correctly."
                )
                return False
            if ret is False:
                self.Close()
                return False

        if self.__txCnt == 0:
            return True
        self.__txSent = sent = 0
        try:
            while self.__txSent < self.__txCnt:
                sent = self.Write(self.__txBuf[self.__txSent : self.__txCnt])
                if sent is None:
                    raise Exception(
                        "Interface Error: Send method not implemented correctly."
                    )
                if sent == 0:
                    if DEBUG:
                        print("Transmit error: sent nothing")
                    self.errorCode |= self.ERR_IF_TRANSMIT_1
                    self.errorString = "Transmit error: sent nothing"
                    return False
                self.__txSent += sent
        except Exception as E:
            if DEBUG:
                print("Transmit error: " + str(E))
            self.errorCode |= self.ERR_IF_TRANSMIT_2
            self.errorString = "Transmit error: " + str(E)
            return False
        return True

    def Receive(self, rxLen, fixedMinSize=6, closeInterface=False, lessOk=False):
        # Receive RX buffer
        nRcvd = nRcvdTotal = 0
        if rxLen == 0:
            if closeInterface:
                self.Close()
            return 0
        try:
            if rxLen < 0 or lessOk:
                # read as much as possible, if rxLen < 0, every amount of data is ok, else read rxLen or less
                if rxLen < 0:
                    rxLen = self.__rxBufSize
                msgPart = self.Read(rxLen)
                nRcvd = len(msgPart)
                if (self.__rxWrite + nRcvd) > (self.__rxBufSize - 1):
                    raise Exception("Receive buffer full! (1)")
                self.__rxBuf[self.__rxWrite : self.__rxWrite + nRcvd] = msgPart
                self.__rxWrite += nRcvd
                if closeInterface:
                    self.Close()
                return nRcvd
            else:
                while nRcvdTotal < rxLen:
                    msgPart = self.Read(min(rxLen - nRcvdTotal, self.__rxBufSize))
                    nRcvd = len(msgPart)
                    if nRcvd == 0:
                        self.errorString = (
                            "Receive error: receiving stopped at ({}/{})".format(
                                self.__rxWrite, rxLen
                            )
                        )
                        if self.__rxWrite == 0:
                            self.errorString = "Receive error: received nothing"
                            if DEBUG:
                                print(self.errorString)
                        else:
                            self.errorString = (
                                "Receive error: received just a part ({})".format(
                                    self.__rxWrite
                                )
                            )
                            if DEBUG:
                                print(self.errorString)
                        self.errorCode |= self.ERR_IF_RECEIVE_1
                        return 0
                    if (self.__rxWrite + nRcvd) > (self.__rxBufSize - 1):
                        raise Exception("Receive buffer full! (2)")
                    self.__rxBuf[self.__rxWrite : self.__rxWrite + nRcvd] = msgPart
                    self.__rxWrite += nRcvd
                    nRcvdTotal += nRcvd
                    if nRcvd < rxLen and nRcvd == fixedMinSize:
                        if closeInterface:
                            self.Close()
                        return nRcvd
        except Exception as E:
            if DEBUG:
                print("Receive error: " + str(E))
            self.errorCode |= self.ERR_IF_RECEIVE_2
            self.errorString = "Receive error: " + str(E)
            if closeInterface:
                self.Close()
            return -1

        if closeInterface:
            self.Close()
        return nRcvdTotal

    def Transceive(self, rxLen=0, delaySeconds=0):
        # Main function. Transmit and receive (both optionally)
        if not self.Transmit(True):
            self.Close()
            raise Exception(self.errorString)

        if delaySeconds > 0:
            sleep(delaySeconds)
        if self._fixedDelay > 0:
            sleep(self._fixedDelay)

        rL = self.Receive(rxLen, closeInterface=True)

        return rL

    def getNumSent(self):
        return self.__txSent

    def getNumReceived(self):
        # returns number of bytes received by Receive
        return self.__rxWrite

    def getNumRx(self):
        # returns number of unread bytes in buffer
        return self.__rxWrite - self.__rxRead

    def _setNumRcvd(self, rcvd):
        self.__rxWrite = rcvd

    def clearBuffer(self):
        self.clearTxBuf()
        self.clearRxBuf()

    def resetErrors(self):
        self.errorCode = 0
        self.errorString = ""

    def getErrorCode(self):
        return self.errorCode

    def getErrorString(self):
        return self.errorString

    # -----------------------------------------------------------------------------
    #                         Methods to fill TX buffer
    # -----------------------------------------------------------------------------

    def clearTxBuf(self):
        self.__txCnt = 0

    def getTxBuf(self):
        return self.__txBuf

    def getTxCount(self):
        return self.__txCnt

    def _setTxCount(self, txCnt):
        self.__txCnt = txCnt

    # Inserts val into buffer from index start to stop. Val should already be string
    # and start/stop should match the data types
    def TxInsert(self, val, start, stop):
        if stop - start <= 0 or start > self.__txCnt or stop > self.__txCnt:
            return
        self.__txBuf[start:stop] = val

    def TxU8(self, u8):
        if self._minBytes > 1:
            self.TxU16(u8)
            return

        self.__txBuf[self.__txCnt : self.__txCnt + 1] = u8_to_string(u8)
        self.__txCnt += 1

    def TxI8(self, i8):
        if self._minBytes > 1:
            self.TxI16(i8)
            return

        self.__txBuf[self.__txCnt : self.__txCnt + 1] = int8_to_string(i8)
        self.__txCnt += 1

    def TxU16(self, u16):
        self.__txBuf[self.__txCnt : self.__txCnt + 2] = u16_to_string(u16)
        self.__txCnt += 2

    def TxI16(self, i16):
        self.__txBuf[self.__txCnt : self.__txCnt + 2] = int16_to_string(i16)
        self.__txCnt += 2

    def TxU32(self, u32):
        self.__txBuf[self.__txCnt : self.__txCnt + 4] = u32_to_string(u32)
        self.__txCnt += 4

    def TxI32(self, i32):
        self.__txBuf[self.__txCnt : self.__txCnt + 4] = int32_to_string(i32)
        self.__txCnt += 4

    def TxU64(self, u64):
        self.__txBuf[self.__txCnt : self.__txCnt + 8] = u64_to_string(u64)
        self.__txCnt += 8

    def TxI64(self, i64):
        self.__txBuf[self.__txCnt : self.__txCnt + 8] = int64_to_string(i64)
        self.__txCnt += 8

    def TxFloat(self, f):
        self.__txBuf[self.__txCnt : self.__txCnt + 4] = float_to_string(f)
        self.__txCnt += 4

    def TxDouble(self, d):
        self.__txBuf[self.__txCnt : self.__txCnt + 8] = double_to_string(d)
        self.__txCnt += 8

    def TxArray(self, Arr, dataType):  # dataType e.g -2 for i16 or 8. for double
        for val in Arr:
            if dataType == 1:
                self.TxU8(val)
            elif dataType == -1:
                self.TxI8(val)
            elif dataType == 2:
                self.TxU16(val)
            elif dataType == -2:
                self.TxI16(val)
            elif dataType == 4:
                if type(dataType) is float:
                    self.TxFloat(val)
                else:
                    self.TxU32(val)
            elif dataType == -4:
                if type(dataType) is float:
                    self.TxFloat(val)
                else:
                    self.TxI32(val)
            elif dataType == 8:
                if type(dataType) is float:
                    self.TxDouble(val)
                else:
                    self.TxU64(val)
            elif dataType == -8:
                if type(dataType) is float:
                    self.TxDouble(val)
                else:
                    self.TxI64(val)

    # "-----------------------------------------------------------------------------"
    # "                    Methods for reading out RX buffer                        "
    # "-----------------------------------------------------------------------------"

    def clearRxBuf(self):
        self.__rxRead = 0
        self.__rxWrite = 0

    def getRxBuf(self):
        return self.__rxBuf

    def getRxWritePos(self):
        return self.__rxWrite

    def getRxReadPos(self):
        return self.__rxRead

    def _setRxReadPos(self, pos):
        self.__rxRead = pos

    def getRxContent(self, start, stop):
        return self.__rxBuf[start:stop]

    def _putIntoRxBuf(self, data, idx=None):
        l = len(data)
        if idx is None:
            self.__rxBuf[self.__rxWrite : self.__rxWrite + l] = data
            self.__rxWrite += l
        else:
            self.__rxBuf[idx : idx + l] = data

    def RxU8(self):
        if self._minBytes > 1:
            return self.RxU16()
        val = string_to_u8(self.__rxBuf[self.__rxRead : self.__rxRead + 1])
        self.__rxRead += 1
        return val

    def RxI8(self):
        if self._minBytes > 1:
            return self.RxI16()
        val = string_to_int8(self.__rxBuf[self.__rxRead : self.__rxRead + 1])
        self.__rxRead += 1
        return val

    def RxU16(self):
        val = string_to_u16(self.__rxBuf[self.__rxRead : self.__rxRead + 2])
        self.__rxRead += 2
        return val

    def RxI16(self):
        val = string_to_int16(self.__rxBuf[self.__rxRead : self.__rxRead + 2])
        self.__rxRead += 2
        return val

    def RxU32(self):
        val = string_to_u32(self.__rxBuf[self.__rxRead : self.__rxRead + 4])
        self.__rxRead += 4
        return val

    def RxI32(self):
        val = string_to_int32(self.__rxBuf[self.__rxRead : self.__rxRead + 4])
        self.__rxRead += 4
        return val

    def RxU64(self):
        val = string_to_u64(self.__rxBuf[self.__rxRead : self.__rxRead + 8])
        self.__rxRead += 8
        return val

    def RxI64(self):
        val = string_to_int64(self.__rxBuf[self.__rxRead : self.__rxRead + 8])
        self.__rxRead += 8
        return val

    def RxFloat(self):
        val = string_to_float(self.__rxBuf[self.__rxRead : self.__rxRead + 4])
        self.__rxRead += 4
        return val

    def RxDouble(self):
        val = string_to_double(self.__rxBuf[self.__rxRead : self.__rxRead + 8])
        self.__rxRead += 8
        return val

    def RxArray(self, length, dataType):
        Arr = []
        for _ in range(length):
            if dataType == 1:
                Arr.append(self.RxU8())
            elif dataType == -1:
                Arr.append(self.RxI8())
            elif dataType == 2:
                Arr.append(self.RxU16())
            elif dataType == -2:
                Arr.append(self.RxI16())
            elif dataType == 4:
                if type(dataType) is float:
                    Arr.append(self.RxFloat())
                else:
                    Arr.append(self.RxU32())
            elif dataType == -4:
                if type(dataType) is float:
                    Arr.append(self.RxFloat())
                else:
                    Arr.append(self.RxI32())
            elif dataType == 8:
                if type(dataType) is float:
                    Arr.append(self.RxDouble())
                else:
                    Arr.append(self.RxU64())
            elif dataType == -8:
                if type(dataType) is float:
                    Arr.append(self.RxDouble())
                else:
                    Arr.append(self.RxI64())
        return Arr


# =================================================================================
#             Methods to convert byte to data types and vise versa
# =================================================================================
# BYTE_ORDER = '<'    # little-endian
BYTE_ORDER = ">"  # big-endian


def int8_to_string(val):
    return struct.pack(BYTE_ORDER + "b", val)


def u8_to_string(val):
    return struct.pack(BYTE_ORDER + "B", val)


def int16_to_string(val):
    return struct.pack(BYTE_ORDER + "h", val)


def u16_to_string(val):
    return struct.pack(BYTE_ORDER + "H", val)


def int32_to_string(val):
    return struct.pack(BYTE_ORDER + "i", val)


def u32_to_string(val):
    return struct.pack(BYTE_ORDER + "I", val)


def int64_to_string(val):
    return struct.pack(BYTE_ORDER + "q", val)


def u64_to_string(val):
    return struct.pack(BYTE_ORDER + "Q", val)


def float_to_string(val):
    return struct.pack(BYTE_ORDER + "f", val)


def double_to_string(val):
    return struct.pack(BYTE_ORDER + "d", val)


def string_to_int8(buf):
    return struct.unpack(BYTE_ORDER + "b", buf)[0]


def string_to_u8(buf):
    return struct.unpack(BYTE_ORDER + "B", buf)[0]


def string_to_int16(buf):
    return struct.unpack(BYTE_ORDER + "h", buf)[0]


def string_to_u16(buf):
    return struct.unpack(BYTE_ORDER + "H", buf)[0]


def string_to_int32(buf):
    return struct.unpack(BYTE_ORDER + "i", buf)[0]


def string_to_u32(buf):
    return struct.unpack(BYTE_ORDER + "I", buf)[0]


def string_to_int64(buf):
    return struct.unpack(BYTE_ORDER + "q", buf)[0]


def string_to_u64(buf):
    return struct.unpack(BYTE_ORDER + "Q", buf)[0]


def string_to_float(buf):
    return struct.unpack(BYTE_ORDER + "f", buf)[0]


def string_to_double(buf):
    return struct.unpack(BYTE_ORDER + "d", buf)[0]
