#!/usr/bin/python3

#contains the functions for sun simulation and other interactions
#with the hue system
#temp is colour temperature, bright is brightness

import datetime
import qhue
import time

from config import *

BRIDGE = qhue.Bridge(BRIDGE_IP, BRIDGE_USERNAME)
LAMPS = BRIDGE.lights()

def lamp_probe():
    for lamp_num in LAMPS:
        lamp = BRIDGE.lights[lamp_num]()
        name = lamp['name']
        if lamp['state']['on']:
            temp_mir = lamp['state']['ct']
            temp_k = int(1000000 / temp_mir)
            bright = lamp['state']['bri']
            xy = lamp['state']['xy']
            print("Lamp {} ({}) is set to {}K, colour {}, at brightness {}.".format(lamp_num, name, temp_k, xy, bright))
        else:
            print("Lamp {} ({}) is off.".format(lamp_num, name))

def set_to_temp(temp_k, bright, trans_time_s=0.4):
    trans_time_ds = 10*trans_time_s
    temp_mir = int(1000000 / temp_k)
    for lamp_num in LAMPS:
        BRIDGE.lights[lamp_num].state(on=True)
        BRIDGE.lights[lamp_num].state(ct=temp_mir, bri=bright, transitiontime=trans_time_ds)
    
    return temp_k, bright

def set_off():
    for lamp_num in LAMPS:
        BRIDGE.lights[lamp_num].state(on=False)

def set_to_xy(x, y, bright):
    for lamp_num in LAMPS:
        BRIDGE.lights[lamp_num].state(on=True)
        BRIDGE.lights[lamp_num].state(xy=(x, y), bri=bright)

def auto_value_now():
    hour = datetime.datetime.now().hour
    minute = datetime.datetime.now().minute
    time_to_check = datetime.time(hour, minute)
    
    n_times = len(LAMPS_BY_TIME[0])
    
    for (i, time) in enumerate(LAMPS_BY_TIME[0]):
        if time_to_check < time:
            if time_to_check >= LAMPS_BY_TIME[0][i-1]:
                temp = LAMPS_BY_TIME[1][i-1]
                bright = LAMPS_BY_TIME[2][i-1]
                return temp, bright
    temp = LAMPS_BY_TIME[1][n_times-1]
    bright = LAMPS_BY_TIME[2][n_times-1]
    return temp, bright

def is_override():
    hour = datetime.datetime.now().hour
    minute = datetime.datetime.now().minute
    time_to_check = datetime.time(hour, minute)
    for lamp_num in LAMPS:
        lamp = BRIDGE.lights[lamp_num]()
        if lamp['state']['on']:
            auto_temp, auto_bright = auto_value_now()
            lamp_temp_mir = lamp['state']['ct']
            lamp_temp_k = int(1000000 / lamp_temp_mir)
            lamp_bright = lamp['state']['bri']
            if abs(lamp_temp_k-auto_temp) > 100 or abs(lamp_bright-auto_bright) > 10:
                return True #at least one lamp does not have auto's values -> not auto
    return False

def night_light_on():
    set_to_xy(0.675, 0.322, 1)

def set_to_cur_time(trans_time):
    temp, bright = auto_value_now()
    set_to_temp(temp, bright, trans_time)
    return temp, bright

if __name__ == '__main__':
    lamp_probe()
