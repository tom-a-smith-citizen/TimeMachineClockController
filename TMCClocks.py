# -*- coding: utf-8 -*-
"""
TMC Clocks
Created on Fri Jan  6 07:29:34 2023

@author: TOSmith

This module is designed to establish the clock object class and associated methods
that allow for control and receiving of information from TimeMachine Corporation
POE B series clocks. It uses the manufacturer provided API located at 
https://www.timemachinescorp.com/wp-content/uploads/TimeMachinesControlAPI.pdf

I've built this module so that the code for the UI is more readable, and so
that changes can be made more quickly and efficiently if necessary.

"""

from datetime import datetime, timedelta
import socket
import struct

class clock(object):
    def __init__(self, clock, ip, port, enabled, mode):
        self.clock = clock
        self.ip = ip
        self.UDP_PORT = port
        self.enabled = True
        self.mode = None
        self.device_type = None
        self.mac = None
        self.displayed_time = None
        self.trt = None
        self.countdown_time = None
        self.timer_time = None
        self.timeout = None
        
        #Commands from the API
        self.API = {"UpTimer Mode": 0xA2,
                         "UpTimer Start/Pause": 0xA3,
                         "UpTimer Reset": 0xA4,
                         "DownTimer Mode": 0xA5,
                         "DownTimer Start/Pause": 0xA6,
                         "DownTimer Reset": 0xA7,
                         "Time Mode": 0xA8,
                         "DotMatrix": 0xA9,
                         "UpTimer While Running": 0xAA,
                         "DownTimer While Running": 0xAB,
                         "Countdown to Date Timer Reset": 0xB9,
                         "Countdown to Date Start/Pause": 0xBA,
                         "Execute Stored Program": 0xB8,
                         "Relay Close": 0xB4,
                         "Relay Toggle": 0xBC,
                         "Revert to Time Timeout": 0xBB,
                         "Dimmer Set": 0xB5,
                         "Color Set": 0xB6}
    
    #Send a command to the clock.
    def command(self, command):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(5)
        sock.sendto(bytes(command), (self.ip, self.UDP_PORT))
        reply = sock.recv(40)
        #print(reply)
        if reply:
            return reply
            sock.close()
        else:
            sock.close()
    
    #Get and store the info from the clock.
    def get_info(self):
        try:
            reply = self.command([0xA1, 0x04, 0xB2])
            key = bytearray(reply)
            device_type = int(key[0])
            if device_type == 1:
                self.device_type = "POE"
            elif device_type == 2:
                self.device_type = "WiFi"
            elif device_type == 3:
                self.device_type = "DotMatrix"
            ip = str(str(key[1])+"."+str(key[2])+"."+str(key[3])+"."+str(key[4]))
            mac = str(str(key[5])+":"+str(key[6])+":"+str(key[7])+":"+str(key[8])+":"+str(key[9])+":"+str(key[10]))
            firmware = str(str(key[11])+"."+str(key[12]))
            displayed_hours = int(key[15])
            if displayed_hours < 10:
                zero = "0"
                displayed_hours = str(displayed_hours)
                displayed_hours = str(zero+displayed_hours)
            else:
                displayed_hours = str(displayed_hours)
            displayed_minutes = int(key[16])
            if displayed_minutes < 10:
                zero = "0"
                displayed_minutes = str(displayed_minutes)
                displayed_minutes = str(zero+displayed_minutes)
            else:
                displayed_minutes = str(displayed_minutes)
            displayed_seconds = int(key[17])
            if displayed_seconds < 10:
                zero = "0"
                displayed_seconds = str(displayed_seconds)
                displayed_seconds = str(zero+displayed_seconds)
            else:
                displayed_seconds = str(displayed_seconds)
            self.displayed_time = str(displayed_hours+":"+displayed_minutes+":"+displayed_seconds)
            self.displayed_time = datetime.strptime(self.displayed_time, "%H:%M:%S")
            trt = self.displayed_time - datetime(1900, 1, 1)
            self.trt = int(trt.total_seconds())
            display_mode = key[19]
            print(f'Device Type: {self.device_type}')
            print(f'IP Address: {ip}')
            print(f'MAC Address: {mac}')
            print(f'Firmware: {firmware}')
            print(f'Displayed time: {displayed_hours}:{displayed_minutes}:{displayed_seconds}')
            if display_mode == 69:
                print('Display mode: Countdown')
                self.mode = "Countdown"
            elif display_mode == 66:
                print('Display mode: Timer')
                self.mode = "Timer"
            elif display_mode == 0:
                print('Display mode: Real Time')
                self.mode = "Real Time"
            self.timeout = False
        except socket.timeout as e:
            print(f"Timeout error: {e}")
            self.timeout = True
        except Exception as e:
            print(e)
   
    #Change clock color.
    def color(self, b1, b2, b3):
       value = [self.API['Color Set'], b1, b2, b3, b1, b2, b3]
       self.command(value)
   
    #Change brightness.
    def brightness(self, brightness):
        dimmer_setting = [self.API['Dimmer Set'], brightness, brightness]
        self.command(dimmer_setting)
    
    #Return clock to real time.
    def real_time(self):
        real_time = [0xA8, 0x01, 0x00]
        self.command(real_time)
      
    #Start a countdown.
    def countdown(self, time):
        self.countdown_time = datetime.strptime(time, "%H:%M:%S")
        colon_1 = time.index(":")
        colon_2 = time.rfind(":")
        hour = int(time[:colon_1])
        minute = int(time[colon_1+1:colon_2])
        second = int(time[colon_2+1:])       
        now = datetime.now()
        currentHour = int(now.strftime('%H'))
        if currentHour > hour or hour < 1:
            now = datetime.now() + timedelta(1)
            month = int(now.strftime('%m'))
            day = int(now.strftime('%d'))
            year = int(now.strftime('%Y'))
            year = str(struct.pack('<h', year))
        else:
            month = int(now.strftime("%m"))
            day = int(now.strftime('%d'))
            year = int(now.strftime("%Y"))
            year = str(struct.pack('<h', year))
        backslash_1 = year.index("\\")
        backslash_2 = year.rindex("\\")
        year_lsb = year[backslash_1+1:backslash_2]
        year_msb = year[backslash_2+1:backslash_2+4]
        year_lsb = "0"+year_lsb
        year_msb = "0"+year_msb
        year_lsb = int(year_lsb, 16)
        year_msb = int(year_msb, 16)
        time = [0xA8, 0x01, 0x00]
        countdown = [0xB9, 0x01, year_lsb, year_msb, month, day, hour, minute, second, 0x1, 0x1]
        start = [0xBA,0x01,0x00]
        self.command(time)
        self.command(countdown)
        self.command(start)
     
    #Starts a timer.
    def timer(self, time, hold):
        if time == 60:
            hour = 0
            minute = 1
            second = 0
        else:
            time = str(time)
            colon_count = time.count(":")
            if colon_count == 2:
                colon_1 = time.index(":")
                colon_2 = time.rfind(":")
                hour = int(time[:colon_1])
                minute = int(time[colon_1+1:colon_2])
                second = int(time[colon_2+1:])
            elif colon_count == 1:
                colon = time.index(":")
                if colon == 0:
                    hour = 0
                    minute = 0
                    second = int(time[colon+1:])
                else:
                    hour = 0
                    minute = int(time[:colon])
                    second = int(time[colon+1:])
            elif colon_count == 0:
                hour = 0
                minute = 0
                second = int(time)
        starting_tenths = 10
        alarm = 1
        alarm_duration = 10
        timer = [self.API['DownTimer Mode'], 0x01, hour, minute, second, starting_tenths, alarm, alarm_duration]
        timer_start = [self.API['DownTimer Start/Pause'], 0x01, 0x00]
        self.command(timer)
        if hold == False:
            self.command(timer_start)
   
    #Adjust current countdown or timer by up to 60 seconds.
    def adjust(self, adjustment):
        self.get_info()
        if self.mode == "Timer":
            current = self.displayed_time
            if adjustment == 60:
                time = current + timedelta(minutes=1)
            elif adjustment == -60:
                time = current + timedelta(minutes=-1)
            else:
                time = current + timedelta(seconds=adjustment)
            
            time = datetime.strftime(time, "%H:%M:%S")
            colons = time.count(":")     
            if colons == 2:
                #Hours
                colon_index = time.find(":")
                second_colon_index = time.rfind(":")
                hours = int(time[:colon_index])
                minutes = int(time[colon_index+1:second_colon_index])
                seconds = int(time[second_colon_index+1:])
            elif colons == 1:
                if len(time) > 3:
                    #Minutes
                    colon_index = time.find(":")
                    hours = 0
                    minutes = int(time[:colon_index])
                    seconds = int(time[colon_index+1:])
            else:
                #Seconds
                hours = 0
                minutes = 0
                seconds = int(time[1:])
                
            starting_tenths = 10
            alarm = 1
            alarm_duration = 10   
            countdown = [self.API['DownTimer Mode'], 0x01, hours, minutes, seconds, starting_tenths, alarm, alarm_duration]
            custom_clock_start = [self.API['DownTimer Start/Pause'], 0x01, 0x00]
            self.command(countdown)
            self.command(custom_clock_start)
            
        elif self.mode == "Countdown":
            current = self.countdown_time
            print(current)
            if adjustment == 60:
                new_time = current + timedelta(minutes=1)
            elif adjustment == -60:
                new_time = current + timedelta(minutes=-1)
            else:
                new_time = current + timedelta(seconds=adjustment)
            new_time = datetime.strftime(new_time, "%H:%M:%S")
            print(new_time)
            self.countdown(new_time)