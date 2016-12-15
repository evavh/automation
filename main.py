#!/usr/bin/python3

#the main file, consisting of a loop that reads out the command queue
#and status queue, which are filled by several threads also started
#through this file. Also contains the lamp setter (a big if statement)
#and sensor functions

import time
import sys
import threading
import datetime
import os

from subprocess import check_output
from queue import Queue

import lamp_control
import tsl2561
import temp_sensor
import http_commands
import telegram_bot

'''Reading configuration'''
from parsed_config import config

USER_MAC = config['bluetooth']['USER_MAC']
USER_NAME = config['bluetooth']['USER_NAME']

BLUETOOTH_RATE = int(config['rates']['BLUETOOTH'])
LIGHT_SENSOR_RATE = int(config['rates']['LIGHT_SENSOR'])
TEMP_SENSOR_RATE = int(config['rates']['TEMP_SENSOR'])
TIME_RATE = int(config['rates']['TIME'])

CURTAIN_THRESHOLD = int(config['thresholds']['CURTAIN'])
CURTAIN_ERROR = int(config['thresholds']['LIGHT_ERROR'])
PRESENT_THRESHOLD = int(config['thresholds']['PRESENT'])

THIS_FILE = os.path.dirname(__file__)

'''Helper functions'''

#writes <formatted date>\t<message>\n to log file <filename>
#parameters: date, filename, message
def write_log(message, filename="server_log", date_format=True):
    date = datetime.datetime.now()
    with open(os.path.join(THIS_FILE, "logs", filename), 'a') as f:
        if date_format is False:
            f.write("{}\t{}\n".format(time.time(), message))
        else:
            date_string = date.strftime("%Y-%m-%d %H:%M:%S")
            f.write("{}\t{}\n".format(date_string, message))
        f.close()

#simple lamp setting function to set lamps to daytime according to user presence
#parameters: user_present, prev_user_present
def lamp_setter(present, prev_present, curtain, prev_curtain, night_mode, night_mode_set, override):
    if night_mode and not night_mode_set: #night mode on, always works
        lamp_control.set_off()
        new_off = True
        new_colour = None
        new_bright = None
        write_log("night mode on, all lamps off")
    elif not night_mode and not night_mode_set and curtain and present: #night mode off, always works
        new_colour, new_bright = lamp_control.set_to_cur_time(init=True)
        new_off = False
        write_log("night mode off, all lamps on")
    elif present and not prev_present and curtain and not night_mode: #user entered, always works
        new_colour, new_bright = lamp_control.set_to_cur_time(init=True)
        new_off = False
        write_log("user entered, all lamps on")
    elif curtain and not prev_curtain and present and not night_mode and not override: #curtain closed, only when auto
        new_colour, new_bright = lamp_control.set_to_cur_time(init=True)
        new_off = False
        write_log("curtains closed, all lamps on")
    elif not present and prev_present and not night_mode: #user left, always works
        lamp_control.set_off()
        new_off = True
        new_colour = None
        new_bright = None
        write_log("user left, all lamps off")
    elif not curtain and prev_curtain and not night_mode and not override: #curtain opened, only when auto
        lamp_control.set_off()
        new_off = True
        new_colour = None
        new_bright = None
        write_log("curtains opened, all lamps off")
    elif curtain and present and not night_mode and not override: #time update, only when auto
        new_off = False
        new_colour, new_bright = lamp_control.set_to_cur_time(init=False)
    else:
        new_off = None
        new_colour = None
        new_bright = None
    return new_off, new_colour, new_bright

#starts a thread running a function with some arguments, default not as daemon
#parameters: function, arguments (tuple), as_daemon (bool)
def start_thread(function, arguments, as_daemon=False):
    new_thread = threading.Thread(target=function, args=arguments)
    new_thread.daemon = as_daemon
    new_thread.start()

def thread_exception_handling(function):
    try:
        function
    except:
        pass
        

'''Main function'''

#reads commands from the queue and controls everything
def main_function(commandqueue, statusqueue, present_event, day_event):
    #init
    present = None
    prev_present = None
    not_present_count = 0
    
    curtain = None
    prev_curtain = None
    
    night_mode = False
    night_mode_set = False
    night_light = False
    night_light_set = False
    
    light_level = -1
    prev_light_level = -1
    
    override = False
    override_detected = 0 #counts number of times we have found the lamps not on auto
    
    lamps_off = None
    lamps_colour = None
    lamps_bright = None
    
    http_command = None
    
    hour = datetime.datetime.now().hour
    minute = datetime.datetime.now().minute
    
    while True:
        command = commandqueue.get(block=True)
        
        #bluetooth checking: sets present
        if "bluetooth:"+USER_NAME in command:
            if "in" in command:
                prev_present = present
                present = True
                not_present_count = 0
                present_event.set()
            elif "out" in command:
                not_present_count += 1
                if not_present_count > PRESENT_THRESHOLD: #we are sure the user is gone
                    present_event.clear()
                    prev_present = present
                    present = False
                
        
        #time checking: sets new hour and minute
        elif "time" in command:
            hour = int(command[5:7])
            minute = int(command[8:10])
        
        #sensor checking: sets temp and light_level
        elif "sensors:temp" in command:
            temp = float(command[13:])
            year_month = datetime.datetime.now().strftime("%Y-%m")
            write_log(str(temp), filename="temp_log", date_format=None)
            write_log(str(temp), filename="temp_log"+"_"+year_month, date_format=None)
        
        elif "sensors:light" in command:
            light_level = int(command[14:])
            write_log(light_level, "light_log")
            prev_curtain = curtain
            if light_level > CURTAIN_THRESHOLD + CURTAIN_ERROR:
                curtain = False
            elif light_level < CURTAIN_THRESHOLD - CURTAIN_ERROR:
                curtain = True
        
        elif "http:request_status" in command:
            status = {'light_level':light_level, 'curtain':curtain,
                      'temp':temp, 'night_mode':night_mode,
                      'present':present, 'lamps_colour':lamps_colour,
                      'lamps_bright':None, 'lamps_off':lamps_off
                     }
            if lamps_bright:
                status['lamps_bright'] = round((lamps_bright/255)*100)
            statusqueue.put(status)
        
        elif "http:command" in command:
            http_command = command[13:]
            if http_command == "night_on":
                night_mode = True
                night_mode_set = False
                day_event.clear()
            elif http_command == "night_off":
                night_mode = False
                night_mode_set = False
                day_event.set()
            elif http_command == "night_light_on":
                lamps_off = False
                lamps_colour, lamps_bright = lamp_control.night_light_on()
            elif http_command == "night_light_off":
                lamps_off = True
                lamps_colour, lamps_bright = None, None
                lamp_control.set_off()
        
        #unimplemented or faulty commands
        else:
            write_log("unknown command: {}".format(command))
        
        if lamp_control.is_override(): #override detected
            if not override: #start of override
                override_starttime = datetime.datetime.now()
                override = True
                write_log("override mode enabled")
        else: #auto detected
            if override: #a change
                override = False
                write_log("override mode disabled")
        
        #override timeout
        if override:
            if datetime.datetime.now() - override_starttime >= datetime.timedelta(hours=2):
                override = False
                write_log("override timed out")
        
        new_off, new_colour, new_bright = lamp_setter(present, prev_present, curtain, prev_curtain, night_mode, night_mode_set, override)
        if new_off is not None:
            lamps_off = new_off
        if new_colour:
            lamps_colour = new_colour
        if new_bright:
            lamps_bright = new_bright
        
        night_mode_set = True
        
        commandqueue.task_done()
    write_log("server stopped")
    


'''Thread functions'''

#send the time to the main thread every certain number of minutes
#commands: time:<hour>:<minute>
#parameters: commandqueue
#config: rate
def time_function(commandqueue):
    while True:
        hour = datetime.datetime.now().hour
        minute = datetime.datetime.now().minute
        time.sleep((TIME_RATE - (minute % TIME_RATE)) * 60)
        cur_time = datetime.datetime.now().strftime("%H:%M")
        hour = datetime.datetime.now().hour
        minute = datetime.datetime.now().minute
        command = "time:{}".format(cur_time)
        commandqueue.put(command)

#check the bluetooth presence of the user at a certain rate
#commands: bluetooth:<user_name>:[in, out]
#parameters: commandqueue
#config: rate, user_mac, user_name
def bluetooth_function(commandqueue, day_event):
    while True:
        day_event.wait()
        
        start = datetime.datetime.now()
        name = check_output(["hcitool", "name", USER_MAC]).decode("utf-8")[:-1]
        
        if name == USER_NAME:
            commandqueue.put("bluetooth:{}:in".format(USER_NAME))
        else:
            commandqueue.put("bluetooth:{}:out".format(USER_NAME))
        
        end = datetime.datetime.now()
        dt = (end - start).total_seconds()
        if BLUETOOTH_RATE > dt:
            time.sleep(BLUETOOTH_RATE-dt)
        

def temp_sensor_function(commandqueue):
    while True:
        start = datetime.datetime.now()

        temp = round(temp_sensor.read_temp(), 1)
        commandqueue.put("sensors:temp:{}".format(temp))
        
        end = datetime.datetime.now()
        dt = (end - start).total_seconds()
        if TEMP_SENSOR_RATE > dt:
            time.sleep(TEMP_SENSOR_RATE-dt)

def light_sensor_function(commandqueue, present_event, day_event):
    tsl = tsl2561.TSL2561()
    while True:
        present_event.wait()
        day_event.wait()
        
        start = datetime.datetime.now()
        
        light = int(tsl.lux())
        commandqueue.put("sensors:light:{}".format(light))
        
        end = datetime.datetime.now()
        dt = (end - start).total_seconds()
        if LIGHT_SENSOR_RATE > dt:
            time.sleep(LIGHT_SENSOR_RATE-dt)

if __name__ == '__main__':
    write_log("starting server")
    commandqueue = Queue()
    statusqueue = Queue()
    telegramqueue = Queue()
    
    present_event = threading.Event()
    present_event.set()
    
    day_event = threading.Event()
    day_event.set()
    
    start_thread(main_function, (commandqueue, statusqueue, present_event, day_event), False)
    
    start_thread(time_function, (commandqueue,), True)
    start_thread(bluetooth_function, (commandqueue, day_event), True)
    start_thread(temp_sensor_function, (commandqueue,), True)
    start_thread(light_sensor_function, (commandqueue, present_event, day_event), True)
    
    start_thread(http_commands.http_function, (commandqueue, statusqueue), True)
    start_thread(telegram_bot.bot_server_function, (telegramqueue,), True)
    
    commandqueue.join()
    statusqueue.join()
    telegramqueue.join()
