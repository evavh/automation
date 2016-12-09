#!/usr/bin/python3

#the main file, consisting of a loop that reads out the command queue
#and status queue, which are filled by several threads also started
#through this file. Also contains the light setter (a big if statement)
#and sensor functions

import configparser
import time
import os
import sys
import threading

from subprocess import check_output
from queue import Queue
import datetime

import lightcontrol
import tsl2561
import temp_sensor
import http_commands

present_thresh = 3

'''Reading configuration'''

this_file = os.path.dirname(__file__)
config = configparser.RawConfigParser()
config.read(os.path.join(this_file, "config", "main_config.ini"))

LOG_DATE_FORMAT = str(config['defaults']['LOG_DATE_FORMAT'])
USER_NAME = config['bluetooth']['USER_NAME']
USER_MAC = config['bluetooth']['USER_MAC']
BLUETOOTH_RATE = int(config['bluetooth']['BLUETOOTH_RATE'])
TIME_RATE = int(config['time']['TIME_RATE'])
TEMP_SENSOR_RATE = int(config['sensors']['TEMP_SENSOR_RATE'])
LIGHT_SENSOR_RATE = int(config['sensors']['LIGHT_SENSOR_RATE'])
TEMP_LOG_FILE = config['sensor_log']['TEMP_LOG_FILE']
LIGHT_LOG_FILE = config['sensor_log']['LIGHT_LOG_FILE']

SERVER_LOG_FILE = config['defaults']['server_log_file']
CURTAIN_THRESHHOLD = int(config['sensors']['curtain_threshhold'])

'''Helper functions'''

#writes <formatted date>\t<message>\n to log file <filename>
#parameters: date, filename, message
def write_log(message, filename=SERVER_LOG_FILE, date_format=LOG_DATE_FORMAT, date=None):
    if date is None:
        date = datetime.datetime.now()
    with open(os.path.join(this_file, "logs", filename), 'a') as f:
        if date_format is None:
            f.write("{}\t{}\n".format(time.time(), message))
        else:
            date_string = date.strftime("%Y-%m-%d %H:%M:%S")
            f.write("{}\t{}\n".format(date_string, message))
        f.close()

#simple light setting function to set light to daytime according to user presence
#parameters: user_present, prev_user_present
def light_setter(hour, minute, user_present, prev_user_present, curtain, prev_curtain, night_mode, night_mode_set, override):
    if night_mode and not night_mode_set: #night mode on, always works
        lightcontrol.set_off()
        off = True
        temperature = None
        brightness = None
        write_log("night mode on, all lights off")
    elif not night_mode and not night_mode_set and curtain and user_present: #night mode off, always works
        temperature, brightness = lightcontrol.set_to_cur_time(init=True)
        off = False
        write_log("night mode off, all lights on")
    elif user_present and not prev_user_present and curtain and not night_mode: #user entered, always works
        temperature, brightness = lightcontrol.set_to_cur_time(init=True)
        off = False
        write_log("user entered, all lights on")
    elif curtain and not prev_curtain and user_present and not night_mode and not override: #curtain closed, only when auto
        temperature, brightness = lightcontrol.set_to_cur_time(init=True)
        off = False
        write_log("curtains closed, all lights on")
    elif not user_present and prev_user_present and not night_mode: #user left, always works
        lightcontrol.set_off()
        off = True
        temperature = None
        brightness = None
        write_log("user left, all lights off")
    elif not curtain and prev_curtain and not night_mode and not override: #curtain opened, only when auto
        lightcontrol.set_off()
        off = True
        temperature = None
        brightness = None
        write_log("curtains opened, all lights off")
    elif curtain and user_present and not night_mode and not override: #time update, only when auto
        off = False
        temperature, brightness = lightcontrol.set_to_cur_time(init=True) #TODO: init does what except return things?
    else:
        off = None
        temperature = None
        brightness = None
    return off, temperature, brightness

#starts a thread running a function with some arguments, default not as daemon
#parameters: function, arguments (tuple), as_daemon (bool)
def startthread(function, arguments, as_daemon=False):
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
def main_function(commandqueue, statusqueue, user_event, day_event):
    #init
    user_present = None
    prev_user_present = None
    user_not_present_count = 0
    
    curtain = None
    prev_curtain = None
    
    night_mode = False
    night_mode_set = False
    
    light_level = -1
    prev_light_level = -1
    
    override = False
    override_detected = 0 #counts number of times we have found the lights not on auto
    
    lights_off = None
    lights_temp = None
    lights_brightness = None
    
    http_command = None
    
    hour = datetime.datetime.now().hour
    minute = datetime.datetime.now().minute
    
    while True:
        command = commandqueue.get(block=True)
        
        #bluetooth checking: sets user_present
        if "bluetooth:"+USER_NAME in command:
            if "in" in command:
                prev_user_present = user_present
                user_present = True
                user_not_present_count = 0
                user_event.set()
            elif "out" in command:
                user_not_present_count += 1
                if user_not_present_count > present_thresh: #we are sure the user is gone
                    user_event.clear()
                    prev_user_present = user_present
                    user_present = False
                
        
        #time checking: sets new hour and minute
        elif "time" in command:
            hour = int(command[5:7])
            minute = int(command[8:10])
        
        #sensor checking: sets temperature and light_level
        elif "sensors:temp" in command:
            temperature = float(command[13:])
            year_month = datetime.datetime.now().strftime("%Y-%m")
            write_log(str(temperature), filename=TEMP_LOG_FILE, date_format=None)
            write_log(str(temperature), filename=TEMP_LOG_FILE+"_"+year_month, date_format=None)
        
        elif "sensors:light" in command:
            light_level = int(command[14:])
            prev_curtain = curtain
            if light_level > CURTAIN_THRESHHOLD + 7:
                curtain = False
            elif light_level < CURTAIN_THRESHHOLD:
                curtain = True
        
        elif "http:request_status" in command:
            status = {'light_level':light_level, 'curtain':curtain,
                      'temperature':temperature, 'night_mode':night_mode,
                      'user_present':user_present, 'lights_temp':lights_temp
                     }
            if not lights_brightness is None:
                status['lights_brightness'] = round((lights_brightness/255)*100)
            statusqueue.put(status)
        
        elif "http:command" in command:
            http_command = command[13:]
            if http_command == "night_on":
                prev_night_mode = night_mode
                night_mode = True
                night_mode_set = False
                day_event.clear()
            elif http_command == "night_off":
                prev_night_mode = night_mode
                night_mode = False
                night_mode_set = False
                day_event.set()
        
        #unimplemented or faulty commands
        else:
            write_log("unknown command: {}".format(command))
        
        if lightcontrol.is_override(): #override detected
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
        
        off_new, temp_new, bright_new = light_setter(hour, minute, user_present, prev_user_present, curtain, prev_curtain, night_mode, night_mode_set, override)
        if off_new:
            lights_off = off_new
        if temp_new:
            lights_temp = temp_new
        if bright_new:
            lights_brightness = bright_new
        
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

        temperature = round(temp_sensor.read_temp(), 1)
        commandqueue.put("sensors:temp:{}".format(temperature))
        
        end = datetime.datetime.now()
        dt = (end - start).total_seconds()
        if TEMP_SENSOR_RATE > dt:
            time.sleep(TEMP_SENSOR_RATE-dt)

def light_sensor_function(commandqueue, user_event, day_event):
    tsl = tsl2561.TSL2561()
    while True:
        user_event.wait()
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
    
    user_event = threading.Event()
    user_event.set()
    
    day_event = threading.Event()
    day_event.set()
    
    startthread(main_function, (commandqueue, statusqueue, user_event, day_event), False)
    startthread(http_commands.http_function, (commandqueue, statusqueue), True)
    startthread(time_function, (commandqueue,), True)
    startthread(bluetooth_function, (commandqueue, day_event), True)
    startthread(temp_sensor_function, (commandqueue,), True)
    startthread(light_sensor_function, (commandqueue, user_event, day_event), True)
    
    commandqueue.join()
    statusqueue.join()
