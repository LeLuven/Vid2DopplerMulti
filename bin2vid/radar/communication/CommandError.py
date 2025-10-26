"""
Created on 06.01.2022

@author: IMST GmbH
"""


class CommandError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)
