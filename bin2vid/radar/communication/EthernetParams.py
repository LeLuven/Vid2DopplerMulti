"""
Created on 15.07.2022

@author: IMST GmbH
"""

# Ethernet
ENET_DEFAULT_IP = "192.168.0.2"
ENET_DEFAULT_TCP_PORTS = (1024, 1025, 1026, 1027, 1028, 1029)
ENET_MAX_TCP_PORTS = 2
ENET_DEFAULT_UDP_PORTS = (4120, 4121, 4122, 4123, 4124, 4125)
ENET_MAX_UDP_PORTS = 2
ENET_DEFAULT_UDP_HOST_PORT = 4100
ENET_DEFAULT_GATEWAY = "192.168.0.1"
ENET_DEFAULT_SUBNET_MASK = "255.255.0.0"
ENET_SNTP_OFF = 0
ENET_SNTP_POLL = 1
ENET_SNTP_LISTEN = 2
ENET_MAX_MULTICAST_GROUPS = 4
ENET_DEFAULT_MULTICAST_GROUPS = ["227.115.82.100", "0.115.82.101", "0.115.82.102", "0.115.82.103"]
ENET_UDP_MULTICAST_PORT = 4440
ENET_UDP_BROADCAST_PORT = 4444


class EthernetParams(object):
    "Object for Ethernet settings of the radar"

    def __init__(self):
        self.MAC = None  # readonly
        self.initValues()

    def initValues(self):
        self.DHCP = 0
        self.AutoIP = 0
        self.IP = ENET_DEFAULT_IP
        self.TcpPorts = [ENET_DEFAULT_TCP_PORTS[n] for n in range(ENET_MAX_TCP_PORTS)]
        self.UdpPorts = [ENET_DEFAULT_UDP_PORTS[n] for n in range(ENET_MAX_UDP_PORTS)]
        self.DefaultGateway = ENET_DEFAULT_GATEWAY
        self.SubnetMask = ENET_DEFAULT_SUBNET_MASK
        self.SntpMode = ENET_SNTP_OFF
        self.NtpServer = "0.0.0.0"
        self.MulticastGroups = ENET_DEFAULT_MULTICAST_GROUPS
        self.UdpMcPort = ENET_UDP_MULTICAST_PORT
        self.UdpBcPort = ENET_UDP_BROADCAST_PORT

    def getIpAsList(self, ip=None):
        if not ip:
            ip = self.IP
        return [int(n) for n in ip.split(".")]

    def getIpAsStr(self, ip):
        return str(ip[0]) + "." + str(ip[1]) + "." + str(ip[2]) + "." + str(ip[3])
