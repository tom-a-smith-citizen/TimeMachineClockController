# -*- coding: utf-8 -*-
"""
Created on Fri Mar 22 06:10:53 2024

@author: TOSmith
"""
#!/usr/bin/env python3

""" Example of announcing a service (in this case, a fake HTTP server) """

import argparse
import logging
import socket
from time import sleep
import threading
from zeroconf import IPVersion, ServiceInfo, Zeroconf

def announce_service():
    sock = socket.gethostname()
    ip = socket.gethostbyname(sock)

    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', action='store_true')
    version_group = parser.add_mutually_exclusive_group()
    version_group.add_argument('--v6', action='store_true')
    version_group.add_argument('--v6-only', action='store_true')
    args = parser.parse_args()

    if args.debug:
        logging.getLogger('zeroconf').setLevel(logging.DEBUG)
    if args.v6:
        ip_version = IPVersion.All
    elif args.v6_only:
        ip_version = IPVersion.V6Only
    else:
        ip_version = IPVersion.V4Only

    desc = {'path': '/~timemachine/'}

    info = ServiceInfo(
        "_http._tcp.local.",
        "TimeMachine Clock Controller._http._tcp.local.",
        addresses=[socket.inet_aton(ip)],
        port=80,
        properties=desc,
        server="ash-2.local.",
    )

    zeroconf = Zeroconf(ip_version=ip_version)
    print("Registration of a service, press Ctrl-C to exit...")
    zeroconf.register_service(info)
    try:
        while True:
            sleep(0.1)
    except KeyboardInterrupt:
        pass
    finally:
        print("Unregistering...")
        zeroconf.unregister_service(info)
        zeroconf.close()

def server_program():
    # get the hostname
    host = socket.gethostname()
    port = 5000  # initiate port no above 1024

    server_socket = socket.socket()  # get instance
    # look closely. The bind() function takes tuple as argument
    server_socket.bind((host, port))  # bind host address and port together

    # configure how many client the server can listen simultaneously
    server_socket.listen(2)
    conn, address = server_socket.accept()  # accept new connection
    print("Connection from: " + str(address))
    while True:
        # receive data stream. it won't accept data packet greater than 1024 bytes
        data = conn.recv(1024).decode()
        if not data:
            # if data is not received break
            break
        print("from connected user: " + str(data))
        data = input(' -> ')
        conn.send(data.encode())  # send data to the client

    conn.close()  # close the connection

if __name__ == '__main__':
    server_thread = threading.Thread(target=server_program,daemon=True)
    announce_thread = threading.Thread(target=announce_service,daemon=True)
    server_thread.start()
    announce_thread.start()