# -*- coding: utf-8 -*-
"""
TimeMachine Clock Controller 1.1.5
Created on Wed September 13 8:50:00 2023

@author: TOSmith
"""

import wx, pickle, webbrowser, logging, keyboard, os, win32api
from ObjectListView import ObjectListView, ColumnDefn
import subprocess as sp
import TMCClocks as TM
import argparse
import socket
import threading
from zeroconf import IPVersion, ServiceInfo, Zeroconf, ServiceBrowser

'''Right-click context menu that appears in the config window to exclude or
include certain clocks when using Alt+Click'''
class ExclusionMenu(wx.Menu):
    def __init__(self, parent, name):
        super(ExclusionMenu, self).__init__()
        self.parent = parent
        self.name = name
        print(self.name)
        if self.name not in frame.excluded:
            exclude = wx.MenuItem(self, wx.NewIdRef(count=1), 'Exclude with Alt+Click')
            self.Append(exclude)
            self.Bind(wx.EVT_MENU, self.on_exclude)
        elif self.name in frame.excluded:
            include = wx.MenuItem(self, wx.NewIdRef(count=1), 'Include with Alt+Click')
            self.Bind(wx.EVT_MENU, self.on_include)
            self.Append(include)
        
    def on_exclude(self, event):
        frame.excluded.append(self.name)
        
    def on_include(self, event):
        frame.excluded.pop(frame.excluded.index(self.name))

'''Right-click context menu that allows the user to clear custom buttons.'''
class ContextMenu(wx.Menu):
    def __init__(self, parent, name):
        super(ContextMenu, self).__init__()

        self.parent = parent
        self.name = name
        clear = wx.MenuItem(self, wx.NewIdRef(count=1), 'Clear')
        self.Append(clear)
        self.Bind(wx.EVT_MENU, self.on_clear, clear)
        
    def on_clear(self, event):
        if self.name == "Custom 1":
            frame.custom_1.SetLabel("Custom 1")
            frame.custom_1_assigned = False
            frame.custom_1_type = 0
            frame.custom_1_time = "HH:MM:SS"
        elif self.name == "Custom 2":
            frame.custom_2.SetLabel("Custom 2")
            frame.custom_2_assigned = False
            frame.custom_2_type = 0
            frame.custom_2_time = "HH:MM:SS"
        elif self.name == "Custom 3":
            frame.custom_3.SetLabel("Custom 3")
            frame.custom_3_assigned = False
            frame.custom_3_type = 0
            frame.custom_3_time = "HH:MM:SS"
        elif self.name == "Custom 4":
            frame.custom_4.SetLabel("Custom 4")
            frame.custom_4_assigned = False
            frame.custom_4_type = 0
            frame.custom_3_time = "HH:MM:SS"

'''About windown with program name/contact info.'''
class AboutFrame(wx.Frame):
    def __init__(self):
        super().__init__(parent=None, title="About")
        self.SetIcon(wx.Icon('icon256.ico'))
        self.SetInitialSize((400,150))
        self.font = wx.Font(12, wx.FONTFAMILY_MODERN, 0, 90, underline = False, faceName ="Arial Bold")
        self.sizer = wx.FlexGridSizer(4,1,10,10)
        self.panel = wx.Panel(self)
        self.program_name = wx.StaticText(self.panel, label=f"{frame.title} by Tom Smith")
        self.program_name.SetFont(self.font)
        self.phone = wx.StaticText(self.panel, label="(231) 343-9803")
        self.phone.SetFont(self.font)
        self.work_email = wx.StaticText(self.panel, label="thomas.smith@woodtv.com")
        self.work_email.SetFont(self.font)
        self.home_email = wx.StaticText(self.panel, label="tom.a.smith@me.com")
        self.home_email.SetFont(self.font)
        self.sizer.AddMany([(self.program_name),
                            (self.phone),
                            (self.work_email),
                            (self.home_email)])
        self.panel.SetSizer(self.sizer)
        self.sizer.Layout()
        self.Show()

'''Configuration window for adding/removing clocks, changing options, etc.'''
class ConfigFrame(wx.Frame):
    def __init__(self):
        super().__init__(parent=None, title="Configure")
        self.SetMinSize((300,350))
        self.SetInitialSize((300,350))
        self.panel = wx.Panel(self)
        self.SetIcon(wx.Icon('icon256.ico'))
        self.main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.buttons_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.add_sizer = wx.FlexGridSizer(3,2,10,10)
        self.show_add = False
        self.UDP_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.UDP_label = wx.StaticText(self.panel, label="UDP Port:")
        self.UDP_field = wx.TextCtrl(self.panel, value=str(frame.UDP_PORT))
        self.UDP_sizer.Add(self.UDP_label, 0, wx.ALL | wx.EXPAND, 5)
        self.UDP_sizer.Add(self.UDP_field, 0, wx.ALL | wx.EXPAND, 5)
        
        self.list_ctrl = ObjectListView(self.panel, wx.ID_ANY, style=wx.LC_REPORT|wx.SUNKEN_BORDER|wx.EXPAND)
        self.list_ctrl.cellEditMode = ObjectListView.CELLEDIT_DOUBLECLICK
        self.list_ctrl.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.on_right_click)
        self.set_columns()
        self.main_sizer.Add(self.list_ctrl, 0, wx.ALL | wx.EXPAND, 5)
        
        self.auto_change_sizer = wx.FlexGridSizer(2,2,0,0)
        self.auto_change_check = wx.CheckBox(self.panel, label="Auto Real Time")
        self.auto_change_check.SetValue(frame.timer_enabled)
        self.auto_change_check.Bind(wx.EVT_CHECKBOX, self.on_auto_check)
        self.seconds_box = wx.TextCtrl(self.panel, value=str(frame.reset_delay))
        self.auto_red_check = wx.CheckBox(self.panel, label="Turn Red with 10 Seconds Left")
        self.auto_red_check.Bind(wx.EVT_CHECKBOX, self.on_red_check)
        self.auto_red_check.SetValue(frame.red_enabled)
        self.auto_change_sizer.AddMany([(self.auto_change_check),
                                        (self.seconds_box),
                                        (self.auto_red_check)])
        
        self.add_btn = wx.Button(self.panel, label="Add")
        self.add_btn.Bind(wx.EVT_BUTTON, self.on_add)
        self.delete_btn = wx.Button(self.panel, label="Delete")
        self.delete_btn.Bind(wx.EVT_BUTTON, self.on_delete)
        self.buttons_sizer.AddMany([(self.add_btn),
                                (self.delete_btn)])
        
        self.clock_name_label = wx.StaticText(self.panel, label="Clock name:")
        self.clock_name_field = wx.TextCtrl(self.panel)
        self.clock_ip_label = wx.StaticText(self.panel, label="Clock IP:")
        self.clock_ip_field = wx.TextCtrl(self.panel)
        self.add_sizer.AddMany([(self.clock_name_label),
                                (self.clock_name_field),
                                (self.clock_ip_label),
                                (self.clock_ip_field)])
        self.add_sizer.ShowItems(show=False)
        
        self.main_sizer.AddMany([(self.auto_change_sizer),
                                 (self.UDP_sizer),
                                 (self.add_sizer),
                                 (self.buttons_sizer)])
        self.panel.SetSizer(self.main_sizer)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Show()

    #Toggles value of the timer bool when box is clicked
    def on_auto_check(self, event):
        change = self.auto_change_check.GetValue()
        if change == True:
            frame.timer_enabled = True
        elif change == False:
            frame.timer_enabled = False
    
    #Toggles value of the red :10 bool when box is clicked
    def on_red_check(self, event):
        change = self.auto_red_check.GetValue()
        if change == True:
            frame.red_enabled = True
        elif change == False:
            frame.red_enabled = False
    
    #Shows add fields and adds the clock then hides the fields
    def on_add(self, event):
        if self.show_add == False:
            self.show_add = True
            self.add_sizer.ShowItems(show=True)
            self.main_sizer.Layout()
        elif self.show_add == True:
            if len(self.clock_name_field.GetValue()) > 0 and len(self.clock_ip_field.GetValue()) > 0:
                clock_name = self.clock_name_field.GetValue()
                clock_ip = self.clock_ip_field.GetValue()
                frame.clock_objs.append(TM.clock(clock_name, clock_ip, frame.UDP_PORT, True, None))
                self.set_columns()
            self.show_add = False
            self.add_sizer.ShowItems(show=False)
            self.clock_name_field.SetValue("")
            self.clock_ip_field.SetValue("")
            self.main_sizer.Layout()
        self.main_sizer.Layout()
     
    #Deletes highlighted clock when button is clicked
    def on_delete(self, event):
        self.list_item_clicked = self.list_ctrl.GetSelectedObject()
        print(self.list_item_clicked.clock)
        dlg = wx.MessageDialog(None, f'Are you sure you want to delete {self.list_item_clicked.clock}?', 'Delete this clock?', wx.YES_NO | wx.NO_DEFAULT | wx.ICON_EXCLAMATION)
        result = dlg.ShowModal()
        if result == wx.ID_YES:
            for clocks in frame.clock_objs:
                if clocks.clock == self.list_item_clicked.clock:
                    index = frame.clock_objs.index(clocks)
                    frame.clock_objs.pop(index)
                    print("Removed clock.")
            self.set_columns()
        else:
            dlg.Destroy()
            
    #Saves settings to files when config window is closed
    def on_close(self, event):
        print("Writing settings to file.")
        filename = 'clocks'
        outfile = open(filename, 'wb')
        pickle.dump(frame.clock_objs, outfile)
        outfile.close()
        frame.UDP_PORT = int(self.UDP_field.GetValue())
        filename = 'udp_port'
        outfile = open(filename, 'wb')
        pickle.dump(frame.UDP_PORT, outfile)
        outfile.close()
        if self.seconds_box.GetValue().isdigit():
            frame.reset_delay = int(self.seconds_box.GetValue())
            filename = 'reset_delay'
            outfile = open(filename, 'wb')
            pickle.dump(frame.reset_delay, outfile)
            outfile.close()
        self.Destroy()
    
    #Populates the list
    def set_columns(self, data=None):
        self.list_ctrl.SetColumns([
            ColumnDefn("Clock", "left", -1, "clock"),
            ColumnDefn("Address", "left", -1, "ip"),
            ColumnDefn("Enabled", "left", -1, "enabled", minimumWidth=75)
        ])
        self.list_ctrl.SetObjects(frame.clock_objs)
    
    #Handles right-click on list items
    def on_right_click(self, event):
        obj = self.list_ctrl.GetSelectedObject()
        name = obj.clock
        self.PopupMenu(ExclusionMenu(self, name))


#Window for controlling clock brightness
class BrightnessFrame(wx.Frame):
    def __init__(self):
        super().__init__(parent=None, title="Brightness")
        self.SetInitialSize((350,100))
        self.SetMaxSize((350,100))
        self.panel = wx.Panel(self)
        self.main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.slider = wx.Slider(self.panel, value=frame.brightness, minValue=0, maxValue=100, style = wx.SL_HORIZONTAL|wx.SL_LABELS)
        self.slider.Bind(wx.EVT_SLIDER, self.adjust_brightness)
        self.ok_btn = wx.Button(self.panel, label="OK")
        self.ok_btn.Bind(wx.EVT_BUTTON, self.on_ok)
        self.main_sizer.Add(self.slider,1,flag = wx.EXPAND)
        self.main_sizer.Add(self.ok_btn)
        self.main_sizer.Layout()
        self.panel.SetSizer(self.main_sizer)
        self.Show()
                
    def adjust_brightness(self, event):
        try:
            for clock in frame.clock_objs:
                if clock.enabled == True:     
                    obj = event.GetEventObject() 
                    val = obj.GetValue()
                    clock.brightness(val)
                    frame.brightness = val
        except Exception as e:
            print(e)
            logging.error(f"Error adjusting brightness: {e}")
    
    #Closes window
    def on_ok(self, event):
        self.Destroy()

class Controller(wx.Frame):
    def __init__(self):
        super().__init__(parent=None, title="TimeMachine Clock Controller 1.1.5")
        self.title = "TimeMachine Clock Controller 1.1.5"
        self.SetIcon(wx.Icon('icon256.ico'))
        self.SetTitle(self.title)
        self.SetMinSize((700,350))
        self.SetInitialSize((700,350))
        self.Bind(wx.EVT_CLOSE, self.on_close)
        sock = socket.gethostname()
        
        '''Real Time Timer'''
        self.timer_enabled = True
        self.red_enabled = True
        self.reset_delay = 10
        self.red_timer = wx.Timer(self, id=1)
        self.real_timer = wx.Timer(self, id=2)
        self.Bind(wx.EVT_TIMER, self.red_time, id=1)
        self.Bind(wx.EVT_TIMER, self.real_time, id=2)
        
        '''UDP Port'''
        self.UDP_PORT = 7372
          
        '''Menu and Statusbar'''
        self.create_menu()    
        self.statusbar = self.CreateStatusBar(1)
        self.statusbar.SetStatusText('Ready.')
        
        self.brightness = 50 #Default brightness value for window at launch
        self.last_opened = None
        logging.basicConfig(filename='TimeMachine Clock Controller Error Log.log', format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.DEBUG)
        
        '''Clocks'''
        self.clock_objs = [TM.clock("Camera 1", "10.10.200.201", 7372, True, None),
                       TM.clock("Camera 2", "10.10.200.202", 7372, True, None),
                       TM.clock("Camera 3", "10.10.200.203", 7372, True, None),
                       TM.clock("Camera 4", "10.10.200.204", 7372, True, None),
                       TM.clock("Camera 5", "10.10.200.205", 7372, True, None),
                       TM.clock("Camera 6", "10.10.200.206", 7372, True, None),
                       TM.clock("Camera 8", "10.10.200.208", 7372, True, None),
                       TM.clock("CTLA", "10.10.200.210", 7372, True, None)]
        
        self.excluded = [] #Clocks to be ignored when Alt+Click to start a countdown
        
        '''Exclude cam 2 by default.'''
        for clock in self.clock_objs:
            if clock.clock == "Camera 2":
                self.excluded.append(clock.clock)
        
        '''UI'''
        self.panel = wx.Panel(self)
        
        self.font = wx.Font(12, wx.FONTFAMILY_MODERN, 0, 90, underline = False, faceName ="Arial Bold")
        self.wrapper = wx.BoxSizer(wx.HORIZONTAL)
        
        #Countdown Section
        self.countdown_sizer = wx.FlexGridSizer(3,1,10,10)
        self.countdown_sizer.AddGrowableRow(0,1)
        self.countdown_sizer.AddGrowableRow(1,1)
        self.countdown_sizer.AddGrowableCol(0,1)
        
        self.countdown_buttons_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.countdown_field_sizer = wx.BoxSizer(wx.VERTICAL)
        
        self.real_time_button = wx.Button(self.panel, label="Show Real Time")
        self.real_time_button.Bind(wx.EVT_BUTTON, self.real_time)
        self.start_countdown_button = wx.Button(self.panel, label="Start Countdown")
        self.start_countdown_button.Bind(wx.EVT_BUTTON, self.countdown)
        
        self.countdown_field = wx.TextCtrl(self.panel, style=wx.TE_PROCESS_ENTER, value="HH:MM:SS", name="Countdown")
        self.countdown_field.Bind(wx.EVT_TEXT_ENTER, self.on_enter)
        
        self.countdown_buttons_sizer.AddMany([(self.real_time_button, 1, wx.ALL | wx.EXPAND),
                                              (self.start_countdown_button, 1, wx.ALL | wx.EXPAND)])
        
        self.countdown_field_sizer.Add(self.countdown_field, 1, wx.EXPAND)
        
        self.countdown_sizer.AddMany([(self.countdown_buttons_sizer, 1, wx.ALL | wx.EXPAND),
                                      (self.countdown_field_sizer, 1, wx.ALL | wx.EXPAND)])
        
        
        #Quick Math Section
        self.quick_math_sizer = wx.FlexGridSizer(4,2,10,10)
        self.quick_math_sizer.AddGrowableRow(0,1)
        self.quick_math_sizer.AddGrowableRow(1,1)
        self.quick_math_sizer.AddGrowableRow(2,1)
        self.quick_math_sizer.AddGrowableRow(3,1)
        self.quick_math_sizer.AddGrowableCol(0,1)
        self.quick_math_sizer.AddGrowableCol(1,1)
        
        self.add_1 = wx.Button(self.panel, label="+1")
        self.add_1.Bind(wx.EVT_BUTTON, lambda event: self.adjust(event, 1))
        self.add_10 = wx.Button(self.panel, label="+10")
        self.add_10.Bind(wx.EVT_BUTTON, lambda event: self.adjust(event, 10))
        self.add_30 = wx.Button(self.panel, label="+30")
        self.add_30.Bind(wx.EVT_BUTTON, lambda event: self.adjust(event, 30))
        self.add_60 = wx.Button(self.panel, label="+60")
        self.add_60.Bind(wx.EVT_BUTTON, lambda event: self.adjust(event, 60))
        self.minus_1 = wx.Button(self.panel, label="-1")
        self.minus_1.Bind(wx.EVT_BUTTON, lambda event: self.adjust(event, -1))
        self.minus_10 = wx.Button(self.panel, label="-10")
        self.minus_10.Bind(wx.EVT_BUTTON, lambda event: self.adjust(event, -10))
        self.minus_30 = wx.Button(self.panel, label="-30")
        self.minus_30.Bind(wx.EVT_BUTTON, lambda event: self.adjust(event, -30))
        self.minus_60 = wx.Button(self.panel, label="-60")
        self.minus_60.Bind(wx.EVT_BUTTON, lambda event: self.adjust(event, -60))
        
        self.quick_math_sizer.AddMany([(self.add_1, 1, wx.ALL | wx.EXPAND),
                                       (self.minus_1, 1, wx.ALL | wx.EXPAND),
                                       (self.add_10, 1, wx.ALL | wx.EXPAND),
                                       (self.minus_10, 1, wx.ALL | wx.EXPAND),
                                       (self.add_30, 1, wx.ALL | wx.EXPAND),
                                       (self.minus_30, 1, wx.ALL | wx.EXPAND),
                                       (self.add_60, 1, wx.ALL | wx.EXPAND),
                                       (self.minus_60, 1, wx.ALL | wx.EXPAND)])
        
        self.countdown_field_sizer.Add(self.quick_math_sizer, 1, wx.ALL | wx.EXPAND)
        
        self.wrapper.Add(self.countdown_sizer, 1, flag = wx.ALL | wx.EXPAND, border = 15)
        
        #Timer Section
        self.premade_timers_sizer = wx.FlexGridSizer(6,2,10,10)
        self.premade_timers_sizer.AddGrowableRow(0,1)
        self.premade_timers_sizer.AddGrowableRow(1,1)
        self.premade_timers_sizer.AddGrowableRow(2,1)
        self.premade_timers_sizer.AddGrowableRow(3,1)
        self.premade_timers_sizer.AddGrowableRow(4,1)
        self.premade_timers_sizer.AddGrowableRow(5,1)
        self.premade_timers_sizer.AddGrowableCol(0,1)
        self.premade_timers_sizer.AddGrowableCol(1,1)
        self.sixty_seconds = wx.Button(self.panel, label="60 Seconds")
        self.sixty_seconds.Bind(wx.EVT_BUTTON, lambda event: self.timer(event, 60))
        self.thirty_seconds = wx.Button(self.panel, label="30 Seconds")
        self.thirty_seconds.Bind(wx.EVT_BUTTON, lambda event: self.timer(event, 30))
        self.ten_seconds = wx.Button(self.panel, label="10 Seconds")
        self.ten_seconds.Bind(wx.EVT_BUTTON, lambda event: self.timer(event, 10))
        self.five_seconds = wx.Button(self.panel, label="5 Seconds")
        self.five_seconds.Bind(wx.EVT_BUTTON, lambda event: self.timer(event, 5))
        
        self.custom_timer_button = wx.Button(self.panel, label="Custom")
        self.custom_timer_button.Bind(wx.EVT_BUTTON, lambda event: self.timer(event, self.custom_timer_field.GetValue()))
        self.custom_timer_button.Bind(wx.EVT_RIGHT_DOWN, lambda event: self.load_timer(event, self.custom_timer_field.GetValue()))
        self.custom_timer_field = wx.TextCtrl(self.panel, style=wx.TE_PROCESS_ENTER, value=":45", name="Timer")
        self.custom_timer_field.Bind(wx.EVT_TEXT_ENTER, self.on_enter)
        
        self.custom_1 = wx.Button(self.panel, label="Custom 1", name="Custom 1")
        self.custom_1.Bind(wx.EVT_BUTTON, lambda event: self.on_custom(event, 1))
        self.custom_1.Bind(wx.EVT_RIGHT_DOWN, self.on_custom_right_click)
        self.custom_1_assigned = False
        self.custom_1_type = 0
        self.custom_1_time = "HH:MM:SS"

        
        self.custom_2 = wx.Button(self.panel, label="Custom 2", name="Custom 2")
        self.custom_2.Bind(wx.EVT_BUTTON, lambda event: self.on_custom(event, 2))
        self.custom_2.Bind(wx.EVT_RIGHT_DOWN, self.on_custom_right_click)
        self.custom_2_assigned = False
        self.custom_2_type = 0
        self.custom_2_time = "HH:MM:SS"

        
        self.custom_3 = wx.Button(self.panel, label="Custom 3", name="Custom 3")
        self.custom_3.Bind(wx.EVT_BUTTON, lambda event: self.on_custom(event, 3))
        self.custom_3.Bind(wx.EVT_RIGHT_DOWN, self.on_custom_right_click)
        self.custom_3_assigned = False
        self.custom_3_type = 0
        self.custom_3_time = "HH:MM:SS"

        
        self.custom_4 = wx.Button(self.panel, label="Custom 4", name="Custom 4")
        self.custom_4.Bind(wx.EVT_BUTTON, lambda event: self.on_custom(event, 4))
        self.custom_4.Bind(wx.EVT_RIGHT_DOWN, self.on_custom_right_click)
        self.custom_4_assigned = False
        self.custom_4_type = 0
        self.custom_4_time = "HH:MM:SS"

        #Customization Buttons
        self.color_btn = wx.Button(self.panel, label="Color")
        self.color_btn.Bind(wx.EVT_BUTTON, self.get_color)
        self.brightness_btn = wx.Button(self.panel, label="Brightness")
        self.brightness_btn.Bind(wx.EVT_BUTTON, self.on_brightness)
        
        self.premade_timers_sizer.AddMany([(self.sixty_seconds, 1, wx.ALL | wx.EXPAND),
                                           (self.thirty_seconds, 1, wx.ALL | wx.EXPAND),
                                           (self.ten_seconds, 1, wx.ALL | wx.EXPAND),
                                           (self.five_seconds, 1, wx.ALL | wx.EXPAND),
                                           (self.custom_timer_button, 1, wx.ALL | wx.EXPAND),
                                           (self.custom_timer_field, 1, wx.ALL | wx.EXPAND),
                                           (self.custom_1, 1, wx.ALL | wx.EXPAND),
                                           (self.custom_2, 1, wx.ALL | wx.EXPAND),
                                           (self.custom_3, 1, wx.ALL | wx.EXPAND),
                                           (self.custom_4, 1, wx.ALL | wx.EXPAND),
                                           (self.color_btn, 1, wx.ALL | wx.EXPAND),
                                           (self.brightness_btn, 1, wx.ALL | wx.EXPAND)])
           
        self.wrapper.Add(self.premade_timers_sizer, 1, flag = wx.ALL | wx.EXPAND, border = 15)
        
        self.widgets = [self.real_time_button,
                        self.start_countdown_button,
                        self.countdown_field,
                        self.add_1,
                        self.add_10,
                        self.add_30,
                        self.add_60,
                        self.minus_1,
                        self.minus_10,
                        self.minus_30,
                        self.minus_60,
                        self.sixty_seconds,
                        self.thirty_seconds,
                        self.ten_seconds,
                        self.five_seconds,
                        self.custom_timer_button,
                        self.custom_timer_field,
                        self.custom_1,
                        self.custom_2,
                        self.custom_3,
                        self.custom_4,
                        self.color_btn,
                        self.brightness_btn]
        
        for widgets in self.widgets:
            widgets.SetFont(self.font)
        
        self.panel.SetSizer(self.wrapper)
        self.Layout()
        threading.Thread(target=self.announce_service,daemon=True).start()
        threading.Thread(target=self.host_program,args=[sock],daemon=True).start()
        self.Show()
        self.on_launch(wx.Event)
        
        '''Zeroconf listening class'''
        class MyListener:
            def update_service(self, zeroconf, type, name):
                print("Service %s removed" % (name,))

            def add_service(self, zeroconf, type, name):
                if name == "TimeMachine Clock Controller._http._tcp.local.":
                    info = zeroconf.get_service_info(type, name)
                    if info:
                        print("Found service:", name)
                        addresses = [socket.inet_ntoa(addr) for addr in info.addresses]
                        print("IP addresses:", addresses)
                    for hosts in addresses:
                        self.client_program(hosts)
                    zeroconf.close()
    
    '''Cross-Machine Comms'''
    def find_services(self):
        zeroconf = Zeroconf()
        listener = self.MyListener()
        browser = ServiceBrowser(zeroconf, "_http._tcp.local.", listener)
    
    
    def announce_service(self):
        sock = socket.gethostname()
        ip = socket.gethostbyname(sock)
        logging.basicConfig(level=logging.DEBUG)

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

        self.info = ServiceInfo(
            "_http._tcp.local.",
            "TimeMachine Clock Controller._http._tcp.local.",
            addresses=[socket.inet_aton(ip)],
            port=80,
            properties=desc,
            server="ash-2.local.",
        )

        self.zeroconf = Zeroconf(ip_version=ip_version)
        self.zeroconf.register_service(self.info)
    
    '''Find service and send data.'''
    def client_program(self, host):
        port = 5000
        client_socket = socket.socket()
        client_socket.connect((host,port))
        message = "QUIT"
        client_socket.send(message.encode())
        client_socket.close()
        
    '''Host to receive socket data.'''
    def host_program(self, host):
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
            if data == "Test Message":
                print('Test message action triggered.')
                dlg = wx.MessageDialog(self,f'Test data received successfully from {address}','Data Received',wx.OK|wx.ICON_INFORMATION)
                dlg.ShowModal()
            elif data == "QUIT":
                timer_status = self.red_timer.IsRunning()
                if timer_status == True:
                    self.red_timer.Stop()
                timer_status = self.real_timer.IsRunning()
                if timer_status == True:
                    self.real_timer.Stop()
                print('Timers stopped.')

        conn.close()  # close the connection
    
    def stop_timers(self):
        self.listener = self.MyListener()
        self.listener.add_service()
    
    '''Functions for control buttons.'''
    #Returns a total number of seconds as milliseconds
    def duration(self, time):
        time = int((time-10)*1000)
        return time
    
    #Runs timer
    def on_timer(self, event):
        threading.Thread(target=self.stop_timers,daemon=True)
        timer = event.GetEventObject()
        timer = timer.GetName()
        print(timer)
        if timer == 1:
            self.red_time(wx.Event)
        elif timer == 2:
            self.real_time(wx.Event)
    
    #Starts internal timers for automatic changing to red/real time
    def wait(self, event, duration):
        #Return the color to cyan first
        b1, b2, b3 = int("00", 16), int("FF", 16), int("FF", 16) #Cyan
        self.set_color(b1, b2, b3)
        
        timer_status = self.red_timer.IsRunning()
        
        if duration <= 10:
            wait_time = 0
        else:
            wait_time = self.duration(duration)
            
        if self.timer_enabled == True and timer_status == True:
            self.red_timer.Stop()
            self.real_timer.Stop()
            self.red_timer.Start(milliseconds=wait_time, oneShot=True)
            self.real_timer.Start(milliseconds=(wait_time+(10*1000))+(self.reset_delay*1000), oneShot=True)
        elif self.timer_enabled ==True and timer_status == False:
            self.red_timer.Start(milliseconds=wait_time, oneShot=True)
            self.real_timer.Start(milliseconds=(wait_time+(10*1000))+(self.reset_delay*1000), oneShot=True)
    
    #Makes clocks red when the internal timer expires (:10 left)
    def red_time(self, event):
        if self.red_enabled == True:
            for clock in self.clock_objs:
                if clock.enabled == True:
                    clock.get_info()
                    if clock.trt != 0:
                        b1, b2, b3 = int("FF", 16), int("00", 16), int("00", 16) #Red
                        self.statusbar.SetStatusText(f"Turning {clock.clock} red.")
                        self.set_color(b1, b2, b3)
        self.statusbar.SetStatusText("Ready.")
    
    #Starts a countdown on all enabled clocks
    def countdown(self, event):
        try:
            for clock in self.clock_objs:
                if clock.enabled == True:
                    if keyboard.is_pressed("alt"):
                        if clock.clock in self.excluded:
                            continue
                    self.statusbar.SetStatusText(f"Starting countdown on {clock.clock}.")
                    clock.countdown(self.countdown_field.GetValue())
                    clock.get_info()
                    self.wait_time = clock.trt
            self.wait(wx.Event, self.wait_time)
            self.statusbar.SetStatusText("Ready.")
        except Exception as e:
            print(e)
            logging.error(f"Error starting countdown: {e}")
            self.statusbar.SetStatusText(f"Error starting countdown on {clock.clock}. Check log.")
     
    #Switches all enabled clocks to real time
    def real_time(self, event):
        timer_status = self.red_timer.IsRunning()
        if timer_status == True:
            self.red_timer.Stop()
        try:
            for clock in self.clock_objs:
                if clock.enabled == True:
                    self.statusbar.SetStatusText(f"Setting {clock.clock} to real time.")
                    clock.real_time()
            self.statusbar.SetStatusText("Ready.")
        except Exception as e:
            print(e)
            logging.error(f"Error setting real time: {e}")
            self.statusbar.SetStatusText(f"Error setting real time on {clock.clock}. Check log.")
     
    #Starts a timer on all enabled clocks
    def timer(self, event, duration):
        try:
            for clock in self.clock_objs:
                if clock.enabled == True:
                    if keyboard.is_pressed("alt"):
                        if clock.clock in self.excluded:
                            continue
                    self.statusbar.SetStatusText(f"Starting timer on {clock.clock}.")
                    clock.timer(duration, False)
                    clock.get_info()
                    self.wait_time = clock.trt
            self.statusbar.SetStatusText("Ready.")
            self.wait(wx.Event, self.wait_time)
                
        except Exception as e:
            print(e)
            logging.error(f"Error starting timer: {e}")
            self.statusbar.SetStatusText(f"Error starting timer on {clock.clock}. Check log.")
     
    #Adds or removes time from all enabled clocks
    def adjust(self, event, adjustment):
        try:
            for clock in self.clock_objs:
                if clock.enabled == True:
                    if keyboard.is_pressed("alt"):
                        if clock.clock in self.excluded:
                            continue
                    self.statusbar.SetStatusText(f"Adjusting {clock.clock} by {adjustment} seconds.")
                    clock.adjust(adjustment)
                    clock.get_info()
                    self.wait_time = clock.trt
            self.statusbar.SetStatusText("Ready.")
            self.wait(wx.Event, self.wait_time)
        except Exception as e:
            print(e)
            logging.error(f"Error sending adjustment: {e}")
            self.statusbar.SetStatusText(f"Error sending adjustment to {clock.clock}. Check log.")
    
    #If a custom button is assigned, it runs. Else, it builds the button.
    def on_custom(self, event, button):         
        if button == 1 and self.custom_1_assigned == True:
            if self.custom_1_type == 1:
                self.countdown_field.SetValue(self.custom_1_time)
                self.countdown(wx.EVT_BUTTON)
            elif self.custom_1_type == 2:
                self.timer(wx.Event, self.custom_1_time)
        elif button == 2 and self.custom_2_assigned == True:
            if self.custom_2_type == 1:
                self.countdown_field.SetValue(self.custom_2_time)
                self.countdown(wx.EVT_BUTTON)
            elif self.custom_2_type == 2:
                self.timer(wx.Event, self.custom_2_time)
        elif button == 3 and self.custom_3_assigned == True:
            if self.custom_3_type == 1:
                self.countdown_field.SetValue(self.custom_3_time)
                self.countdown(wx.EVT_BUTTON)
            elif self.custom_3_type == 2:
                self.timer(wx.Event, self.custom_3_time)
        elif button == 4 and self.custom_4_assigned == True:
            if self.custom_4_type == 1:
                self.countdown_field.SetValue(self.custom_4_time)
                self.countdown(wx.EVT_BUTTON)
            elif self.custom_4_type == 2:
                self.timer(wx.Event, self.custom_4_time)
        else:
            message = "Clock Type"
            caption = "Choose a clock type:"
            choices = ["Countdown", "Timer"]
            parent = None
            dlg = wx.SingleChoiceDialog(parent, message, caption, choices, style=wx.OK | wx.CANCEL | wx.CENTRE, pos=wx.DefaultPosition)
            #dlg.ShowModal()
            if dlg.ShowModal() == wx.ID_OK:
                choice = dlg.GetStringSelection()
                if choice == "Countdown":
                    choice = 1
                elif choice == "Timer":
                    choice = 2
                dlg = wx.TextEntryDialog(self, 'Name the button:','Custom Button') 
                if dlg.ShowModal() == wx.ID_OK: 
                    if button == 1:
                        self.custom_1.SetLabel(dlg.GetValue())
                        self.custom_1_assigned = True
                        self.custom_1_type = choice
                    elif button == 2:
                        self.custom_2.SetLabel(dlg.GetValue())
                        self.custom_2_assigned = True
                        self.custom_2_type = choice
                    elif button == 3:
                        self.custom_3.SetLabel(dlg.GetValue())
                        self.custom_3_assigned = True
                        self.custom_3_type = choice
                    elif button == 4:
                        self.custom_4.SetLabel(dlg.GetValue())
                        self.custom_4_assigned = True
                        self.custom_4_type = choice
                    dlg = wx.TextEntryDialog(self, 'Set a time (HH:MM:SS):','Custom Button')
                    if dlg.ShowModal() == wx.ID_OK:
                        if button == 1:
                            self.custom_1_time = dlg.GetValue()
                        elif button == 2:
                            self.custom_2_time = dlg.GetValue()
                        elif button == 3:
                            self.custom_3_time = dlg.GetValue()
                        elif button == 4:
                            self.custom_4_time = dlg.GetValue()
    
    #Launches a color picker and passes the hex to set_color
    def get_color(self, event):
       dlg = wx.ColourDialog(self)
       dlg.GetColourData().SetChooseFull(True)
       if dlg.ShowModal() == wx.ID_OK:
            new_color = dlg.GetColourData().Colour
            new_color_string = new_color.GetAsString(flags=wx.C2S_HTML_SYNTAX)
            byte_1 = int(new_color_string[1:3], 16)
            byte_2 = int(new_color_string[3:5], 16)
            byte_3 = int(new_color_string[5:7], 16)
            self.set_color(byte_1, byte_2, byte_3)
   
    #Sets the color of enabled clocks
    def set_color(self, byte_1, byte_2, byte_3):
        try:
            for clock in self.clock_objs:
                if clock.enabled == True:
                    self.statusbar.SetStatusText(f"Changing color on {clock.clock}.")
                    clock.color(byte_1, byte_2, byte_3)
            self.statusbar.SetStatusText("Ready.")
        except Exception as e:
            print(e)
            logging.error(f"Error changing color: {e}")
            self.statusbar.SetStatusText(f"Error changing color on {clock.clock}. Check log.")
    
    #Launches brightness controls
    def on_brightness(self, event):
        BrightnessFrame()
    
    
    '''Functions for building the menu/executing options.'''
    
    #Creates menu bar & associated options
    def create_menu(self):
        menu_bar = wx.MenuBar()
        
        file_menu = wx.Menu()    
        new_option = file_menu.Append(wx.ID_ANY, 'New', 'Reset the custom buttons and build a new show.')
        self.Bind(event=wx.EVT_MENU,handler=self.on_new_option,source=new_option)
        
        open_option = file_menu.Append(wx.ID_ANY, 'Open', 'Open a custom button file.')
        self.Bind(event=wx.EVT_MENU,handler=self.on_open_option,source=open_option)
        
        save_option = file_menu.Append(wx.ID_ANY, 'Save', 'Save a custom button file.')
        self.Bind(event=wx.EVT_MENU,handler=self.on_save_option,source=save_option)
        
        configure_option = file_menu.Append(wx.ID_ANY, 'Configure', 'Configure clocks.')
        self.Bind(event=wx.EVT_MENU,handler=self.on_configure_option,source=configure_option)
        menu_bar.Append(file_menu, '&File')
        
        help_menu = wx.Menu()
        about_option = help_menu.Append(wx.ID_ANY, 'About','Information about this program.')
        self.Bind(event=wx.EVT_MENU,handler=self.on_about_option,source=about_option)
        
        documentation_option = help_menu.Append(wx.ID_ANY, 'Documention',"Opens a PDF of this program's documentation.")
        self.Bind(event=wx.EVT_MENU,handler=self.on_documentation_option,source=documentation_option)
        
        error_log_option = help_menu.Append(wx.ID_ANY, "Error Log","Opens the error log.")
        self.Bind(event=wx.EVT_MENU,handler=self.on_error_log_option,source=error_log_option)
        
        bug_report_option = help_menu.Append(wx.ID_ANY, "Bug Report","Report a bug via email.")
        self.Bind(event=wx.EVT_MENU,handler=self.on_bug_report_option,source=bug_report_option)
        
        menu_bar.Append(help_menu, '&Help')
        
        self.SetMenuBar(menu_bar)
    
    #Clears all customization
    def on_new_option(self, event):
        self.last_opened = None
        self.custom_1.SetLabel("Custom 1")
        self.custom_1_assigned = False
        self.custom_1_type = 0
        self.custom_1_time = "HH:MM:SS"
        
        self.custom_2.SetLabel("Custom 2")
        self.custom_2_assigned = False
        self.custom_2_type = 0
        self.custom_2_time = "HH:MM:SS"
        
        self.custom_3.SetLabel("Custom 3")
        self.custom_3_assigned =  False
        self.custom_3_type = 0
        self.custom_3_time = "HH:MM:SS"
        
        self.custom_4.SetLabel("Custom 4")
        self.custom_4_assigned = False
        self.custom_4_type = 0
        self.custom_4_time = "HH:MM:SS"
        
        self.SetTitle(self.title)
    
    #Opens custom button file
    def on_open_option(self, event):
        custom_1_name = None
        custom_2_name = None
        custom_3_name = None
        custom_4_name = None
        with wx.FileDialog(self, "Open show file", wildcard="show files (*.show)|*.show",
                       style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return     # the user changed their mind

        # Proceed loading the file chosen by the user
            pathname = fileDialog.GetPath()
            self.last_opened = pathname
            try:
                infile = open(pathname,'rb')
                [custom_1_name, self.custom_1_assigned, self.custom_1_time, self.custom_1_type,
                custom_2_name, self.custom_2_assigned, self.custom_2_time, self.custom_2_type,
                custom_3_name, self.custom_3_assigned, self.custom_3_time, self.custom_3_type,
                custom_4_name, self.custom_4_assigned, self.custom_4_time, self.custom_4_type] = pickle.load(infile)
                self.custom_1.SetLabel(custom_1_name)
                self.custom_2.SetLabel(custom_2_name)
                self.custom_3.SetLabel(custom_3_name)
                self.custom_4.SetLabel(custom_4_name)
                if self.last_opened:
                    last_slash = self.last_opened.rfind("\\")
                    last_period = self.last_opened.rfind(".")
                    file = self.last_opened[last_slash+1:last_period]
                    self.SetTitle(f"{self.title} - {file}")    
            except Exception as e:
                print(e)
                logging.error(f"Error opening {self.last_opened}: {e}")
    
    #Saves custom button file
    def on_save_option(self, event):
        with wx.FileDialog(self, "Save show file", wildcard="show files (*.show)|*.show", style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return     # the user changed their mind

            # save the current contents in the file
            pathname = fileDialog.GetPath()
            self.last_opened = pathname
            try:
                print("Writing settings to file.")
                custom_1_name = self.custom_1.GetLabel()
                custom_2_name = self.custom_2.GetLabel()
                custom_3_name = self.custom_3.GetLabel()
                custom_4_name = self.custom_4.GetLabel()
                outfile = open(pathname, 'wb')
                pickle.dump([custom_1_name, self.custom_1_assigned, self.custom_1_time, self.custom_1_type,
                             custom_2_name, self.custom_2_assigned, self.custom_2_time, self.custom_2_type,
                             custom_3_name, self.custom_3_assigned, self.custom_3_time, self.custom_3_type,
                             custom_4_name, self.custom_4_assigned, self.custom_4_time, self.custom_4_type], outfile)
                outfile.close()
                if self.last_opened:
                    last_slash = self.last_opened.rfind("\\")
                    last_period = self.last_opened.rfind(".")
                    file = self.last_opened[last_slash+1:last_period]
                    self.SetTitle(f"{self.title} - {file}")
            except Exception as e:
                print(e)
                logging.error(f"Error saving {self.last_opened}: {e}")
    
    #Launches configuration window
    def on_configure_option(self, event):
        ConfigFrame()
     
    #Launches about window
    def on_about_option(self, event):
        AboutFrame()
   
    #Opens documentation in default browser
    def on_documentation_option(self, event):
        path = 'http://studio.woodtv.net/timemachine/documentation.pdf'
        webbrowser.open_new(path)
     
    #Opens the error log in notepad
    def on_error_log_option(self, event):
        program_name = "notepad.exe"
        file_name = "TimeMachine Clock Controller Error Log.log"
        sp.Popen([program_name, file_name])
   
    #Launches an email composition window addressed to me for users to send in bugs
    def on_bug_report_option(self, event):
        win32api.ShellExecute(0,'open',f'mailto:thomas.smith@woodtv.com?subject={self.title} Bug Report',None,None,0)
    
    '''Data persistence functions'''
    #Writes information about the current state of the window to file for
    #loading next launch
    def on_close(self, event):
        print('Closing')
        print("Writing settings to file.")
        home_dir = os.path.expanduser("~")
        filename = f'{home_dir}\last_show'
        outfile = open(filename, 'wb')
        countdown = self.countdown_field.GetValue()
        timer = self.custom_timer_field.GetValue()
        pickle.dump([countdown, timer, self.last_opened, self.timer_enabled, 
                     self.reset_delay, self.red_enabled, self.excluded], outfile)
        outfile.close()
        self.zeroconf.unregister_service(self.info)
        self.zeroconf.close()
        self.Destroy()
    
    #Gets and loads info when program launches
    def on_launch(self, event):
        #Load clock info
        try:
            filename = 'clocks'
            infile = open(filename,'rb')
            self.clock_objs = pickle.load(infile)
            infile.close()
        except Exception as e:
            print(f"Error loading clock info: {e}")
            logging.error(f"Error loading clock info: {e}")
            
        #Load UDP Port info
        try:
            filename = 'udp_port'
            infile = open(filename,'rb')
            self.UDP_PORT = pickle.load(infile)
            infile.close()
        except Exception as e:
            print(f"Error loading UDP port info: {e}")
            logging.error(f"Error loading UDP port info: {e}")
            
        #Load timer and previous show info
        try:
            '''We save the file to the user's root directory so that each user
            sees their own buttons and settings on launch'''
            home_dir = os.path.expanduser("~")
            filename = f'{home_dir}\last_show'
            infile = open(filename,'rb')
            [countdown, timer, self.last_opened, self.timer_enabled, 
             self.reset_delay, self.red_enabled, self.excluded] = pickle.load(infile)
            self.countdown_field.SetValue(countdown)
            self.custom_timer_field.SetValue(timer)
            if self.last_opened:
                last_slash = self.last_opened.rfind("\\")
                last_period = self.last_opened.rfind(".")
                file = self.last_opened[last_slash+1:last_period]
                self.SetTitle(f"{self.title} - {file}")
            infile.close()
        except Exception as e:
            print(f"Error loading timer and previous show: {e}")
            logging.error(f"Error loading timer and previous show info: {e}")
            
        #Load custom buttons from last show
        try:
            filename = self.last_opened
            infile = open(filename,'rb')
            [custom_1_name, self.custom_1_assigned, self.custom_1_time, self.custom_1_type,
             custom_2_name, self.custom_2_assigned, self.custom_2_time, self.custom_2_type,
             custom_3_name, self.custom_3_assigned, self.custom_3_time, self.custom_3_type,
             custom_4_name, self.custom_4_assigned, self.custom_4_time, self.custom_4_type] = pickle.load(infile)
            self.custom_1.SetLabel(custom_1_name)
            self.custom_2.SetLabel(custom_2_name)
            self.custom_3.SetLabel(custom_3_name)
            self.custom_4.SetLabel(custom_4_name)
                    
        except Exception as e:
            print(f"Error loading custom buttons: {e}")
            logging.error(f"Error loading custom buttons: {e}")
            
        #Test clock connections and get info
        try:
            for clock in self.clock_objs:
                if clock.enabled == True:
                    clock.get_info()
                    if clock.timeout == True:
                        clock.enabled = False
                        dlg = wx.MessageDialog(None, f"Couldn't connect to {clock.clock}. Please check its connection for power and network.", 'Error', wx.OK | wx.ICON_ERROR)
                        dlg.ShowModal()
        except Exception as e:
            print(f"Error getting clock info or connection: {e}")
            logging.error(f"Error getting clock info or connection: {e}")
   
    '''UI Management/Hidden Option Functions'''
    '''Additionally, if ALT is held while clicking to start a countdown or timer,
    specified clocks will be excluded from that action.'''

    #Show but not start timer
    def load_timer(self, event, duration):
        try:
            for clock in self.clock_objs:
                if clock.enabled == True:
                    clock.timer(duration, True)
        except Exception as e:
            print(f"Error loading timer in {clock.clock}: {e}")
            logging.error(f"Error loading timer in {clock.clock}: {e}")
            
    #On enter for TextCtrl
    def on_enter(self, event):
        field = event.GetEventObject()
        field = field.GetName()
        print(field)
        if field == "Countdown":
            self.countdown(wx.Event)
        elif field == "Timer":
            self.timer(wx.Event, self.custom_timer_field.GetValue())
    
    #Shows context menu when right clicking on custom buttons, enabling them
    #to be cleared
    def on_custom_right_click(self, event):
        caller = event.GetEventObject()
        name = caller.GetName()
        print(name)
        self.PopupMenu(ContextMenu(self, name))
      
if __name__ == "__main__":
    app=[]; app = wx.App(None)
    frame = Controller()
    app.MainLoop()