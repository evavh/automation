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
import traceback

from subprocess import check_output
from queue import Queue

import lamp_control
import tsl2561 #module for light sensor
import temp_sensor
import http_commands
import telegram_bot
import alarm

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
#only run when something's changed
def lamp_setter(override, priority_change, trans_time, present, curtain, night_mode):
    if not override or priority_change: #we are on auto or the change is important
        if present and curtain and not night_mode: #lamps should be on
            new_colour, new_bright = lamp_control.set_to_cur_time()
            new_off = False
            write_log("lamps set to on, with automatic configuration")
        else: #lamps should be off
            lamp_control.set_off()
            new_colour, new_bright = None, None
            new_off = True
            write_log("lamps set to off")
    else: #we are on override and the change has no priority over it
        new_colour, new_bright = None, None
        new_off = None
        
    return new_off, new_colour, new_bright

#starts a thread running a function with some arguments, default not as daemon
#parameters: function, arguments (tuple), as_daemon (bool)

def thread_exception_handling(function, args):
    try:
        function(*args)
    except:
        write_log(traceback.format_exception_only(sys.exc_info()[0], sys.exc_info()[1])[0][:-1])

def start_thread(function, args, as_daemon=False):
    new_thread = threading.Thread(target=thread_exception_handling, args=(function,args))
    new_thread.daemon = as_daemon
    new_thread.start()

'''Main function'''

#reads commands from the queue and controls everything
def main_function(command_queue, http_status_queue, telegram_status_queue, present_event, day_event):
    #init
    present = None
    prev_present = None
    not_present_count = 0
    
    curtain = None
    prev_curtain = None
    
    night_mode = False
    night_light = False
    alarm_time = None
    
    light_level = -1
    
    override = False
    override_detected = 0 #counts number of times we have found the lamps not on auto
    
    #nothing has changed yet
    change = False
    priority_change = False
    trans_time = None
    
    lamps_off = None
    lamps_colour = None
    lamps_bright = None
    
    while True:
        command = command_queue.get(block=True)
        
        #bluetooth checking: sets present
        if "bluetooth:"+USER_NAME in command:
            prev_present = present
            if "in" in command:
                present = True
                not_present_count = 0
                present_event.set()
            elif "out" in command:
                not_present_count += 1
                if not_present_count > PRESENT_THRESHOLD: #we are sure the user is gone
                    present_event.clear()
                    present = False
            if present != prev_present:
                priority_change = True
                
        
        #time checking: sets new hour and minute
        elif "time" in command:
            hour = int(command[5:7])
            minute = int(command[8:10])
            change = True
            trans_time = 5
        
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
            if curtain != prev_curtain:
                change = True
        
        elif "request_status" in command:
            status = {'light_level':light_level, 'curtain':curtain,
                      'temp':temp, 'night_mode':night_mode,
                      'present':present, 'lamps_colour':lamps_colour,
                      'lamps_bright':None, 'lamps_off':lamps_off,
                      'override':override, 'alarm_time':alarm_time
                     }
            if lamps_bright:
                status['lamps_bright'] = round((lamps_bright/255)*100)
            if "http" in command:
                http_status_queue.put(status)
            elif "telegram" in command:
                telegram_status_queue.put(status)
        
        elif "command" in command:
            http_command = command[8:]
            if http_command == "night_on":
                alarm_time = alarm.alarm_time()
                alarm.set_cron_alarm(alarm_time)
                night_mode = True
                priority_change = True
                day_event.clear()
            elif http_command == "night_off":
                alarm_time = None
                night_mode = False
                priority_change = True
                trans_time = 30
                day_event.set()
            elif http_command == "night_light_on":
                lamps_off = False
                lamps_colour = 1000
                lamps_bright = 3
                lamp_control.night_light_on()
            elif http_command == "night_light_off":
                lamps_off = True
                lamps_colour, lamps_bright = None, None
                lamp_control.set_off()
            elif http_command == "clear_alarm":
                alarm_time = None
                alarm.clear_alarm()
                
        
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
        
        #setting the lights if something has changed
        if change or priority_change:
            new_off, new_colour, new_bright = lamp_setter(override, priority_change, trans_time, present, curtain, night_mode)
            change = False
            priority_change = False
            trans_time = None
            if new_off is not None:
                lamps_off = new_off
            if new_colour:
                lamps_colour = new_colour
            if new_bright:
                lamps_bright = new_bright
        
        command_queue.task_done()
    write_log("server stopped")
    


'''Thread functions'''

#send the time to the main thread every certain number of minutes
#commands: time:<hour>:<minute>
#parameters: command_queue
#config: rate
def time_function(command_queue):
    while True:
        #wait TIME_RATE minutes between each check
        minute = datetime.datetime.now().minute
        time.sleep((TIME_RATE - (minute % TIME_RATE)) * 60)
        
        #check if we need to send a command, if so send it
        hour = datetime.datetime.now().hour
        minute = datetime.datetime.now().minute
        if datetime.time(hour, minute) in lamp_control.lamps_by_time[0]:
            cur_time = datetime.datetime.now().strftime("%H:%M")
            command = "time:{}".format(cur_time)
            command_queue.put(command)

#check the bluetooth presence of the user at a certain rate
#commands: bluetooth:<user_name>:[in, out]
#parameters: command_queue
#config: rate, user_mac, user_name
def bluetooth_function(command_queue, day_event):
    while True:
        day_event.wait()
        
        start = datetime.datetime.now()
        name = check_output(["hcitool", "name", USER_MAC]).decode("utf-8")[:-1]
        
        if name == USER_NAME:
            command_queue.put("bluetooth:{}:in".format(USER_NAME))
        else:
            command_queue.put("bluetooth:{}:out".format(USER_NAME))
        
        end = datetime.datetime.now()
        dt = (end - start).total_seconds()
        if BLUETOOTH_RATE > dt:
            time.sleep(BLUETOOTH_RATE-dt)
        

def temp_sensor_function(command_queue):
    while True:
        start = datetime.datetime.now()

        temp = round(temp_sensor.read_temp(), 1)
        command_queue.put("sensors:temp:{}".format(temp))
        
        end = datetime.datetime.now()
        dt = (end - start).total_seconds()
        if TEMP_SENSOR_RATE > dt:
            time.sleep(TEMP_SENSOR_RATE-dt)

def light_sensor_function(command_queue, present_event, day_event):
    tsl = tsl2561.TSL2561()
    while True:
        present_event.wait()
        day_event.wait()
        
        start = datetime.datetime.now()
        
        light = int(tsl.lux())
        command_queue.put("sensors:light:{}".format(light))
        
        end = datetime.datetime.now()
        dt = (end - start).total_seconds()
        if LIGHT_SENSOR_RATE > dt:
            time.sleep(LIGHT_SENSOR_RATE-dt)

if __name__ == '__main__':
    write_log("starting server")
    command_queue = Queue()
    http_status_queue = Queue()
    telegram_status_queue = Queue()
    
    present_event = threading.Event()
    present_event.set()
    
    day_event = threading.Event()
    day_event.set()
    
    start_thread(main_function, (command_queue, http_status_queue, telegram_status_queue, present_event, day_event), False)
    
    start_thread(time_function, (command_queue,), True)
    start_thread(bluetooth_function, (command_queue, day_event), True)
    start_thread(temp_sensor_function, (command_queue,), True)
    start_thread(light_sensor_function, (command_queue, present_event, day_event), True)
    
    start_thread(http_commands.http_function, (command_queue, http_status_queue), True)
    start_thread(telegram_bot.bot_server_function, (command_queue, telegram_status_queue,), True)
    
    command_queue.join()
    http_status_queue.join()
    telegram_status_queue.join()
