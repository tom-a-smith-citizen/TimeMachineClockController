# -*- coding: utf-8 -*-
"""
Created on Fri Mar 22 08:07:22 2024

@author: TOSmith
"""
from zeroconf import ServiceBrowser, Zeroconf
import socket

def client_program(host):
    port = 5000
    client_socket = socket.socket()
    client_socket.connect((host,port))
    message = "Test message."
    client_socket.send(message.encode())
    client_socket.close()

class MyListener:
    def remove_service(self, zeroconf, type, name):
        print("Service %s removed" % (name,))

    def add_service(self, zeroconf, type, name):
        if name == "TimeMachine Clock Controller._http._tcp.local.":
            info = zeroconf.get_service_info(type, name)
            if info:
                print("Found service:", name)
                addresses = [socket.inet_ntoa(addr) for addr in info.addresses]
                print("IP addresses:", addresses)
            for hosts in addresses:
                client_program(hosts)
            zeroconf.close()

zeroconf = Zeroconf()
listener = MyListener()
browser = ServiceBrowser(zeroconf, "_http._tcp.local.", listener)

try:
    input("Press enter to exit...\n\n")
finally:
    zeroconf.close()