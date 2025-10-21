"""
Created on 15.07.2022

@author: IMST GmbH
"""

import json

# frontend codes
FE_CODE_NO_FE = 0xFE000000
FE_CODE_AWR1243 = 0xFE770001


class InfoParameters(object):
    def __init__(self):
        self.deviceNumber = None
        self.frontendConnected = FE_CODE_NO_FE
        self.fwVersion = None
        self.fwRevision = None
        self.fwDate = None

    def getFwVersionString(self):
        return "%d.%d.%d" % ((self.fwVersion >> 16) & 0xFF, (self.fwVersion >> 8) & 0xFF, self.fwVersion & 0xFF)

    def getFwDateString(self):
        return "%d.%d.%d" % ((self.fwDate >> 24) & 0xFF, (self.fwDate >> 16) & 0xFF, self.fwDate & 0xFFFF)

    def print(self):
        print("\tInfo:")
        print("\t\tDevice Number:", self.deviceNumber)
        print("\t\tFrontend Code:", self.frontendConnected)
        print("\t\tFirmware Version:", self.getFwVersionString())
        print("\t\tFirmware Revision:", self.fwRevision)
        print("\t\tFirmware Date:", self.getFwDateString())

    def save(self, path: str):
        data = {}
        data["DeviceNumber"] = self.deviceNumber
        data["FrontendConnected"] = self.frontendConnected
        data["FwVersion"] = self.getFwVersionString()
        data["FwRevision"] = self.fwRevision
        data["FwDate"] = self.getFwDateString()

        with open(path, "w", encoding="utf8") as file:
            json.dump(data, file, indent=4)
