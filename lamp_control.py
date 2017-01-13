#!/usr/bin/python3

#contains the functions for sun simulation and other interactions
#with the hue system
#temp is colour temperature, bright is brightness

import datetime
import phue

from config import *

BRIDGE = phue.Bridge(BRIDGE_IP)
LAMPS = BRIDGE.get_light_objects()

def lamp_probe():
    for lamp in LAMPS:
        number = lamp.light_id
        name = lamp.name
        on = lamp.on
        if on:
            colortemp_k = lamp.colortemp_k
            bright = lamp.brightness
            xy = lamp.xy
            print("Lamp {} ({}) is set to {}K, colour {}, at brightness {}.".format(number, name, colortemp_k, xy, bright))
        else:
            print("Lamp {} ({}) is off.".format(number, name))

def set_to_temp(temp, bright, trans_time):
    for lamp in LAMPS:
        lamp.on = True
        lamp.colortemp_k = temp
        lamp.brightness = 1
        BRIDGE.set_light(lamp.light_id, 'bri', bright, transitiontime=trans_time)
    
    return temp, bright

def set_to_xy(x, y, bright):
    for lamp in LAMPS:
        lamp.on = True
        lamp.xy = (x, y)
        lamp.brightness = bright

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
    for lamp in LAMPS:
        if lamp.on:
            auto_temp, auto_bright = auto_value_now()
            lamp_temp = lamp.colortemp_k
            lamp_bright = lamp.brightness
            if abs(lamp_temp-auto_temp) > 100 or abs(lamp_bright-auto_bright) > 10:
                return True #at least one lamp does not have auto's values -> not auto
    return False

def set_off():
    for lamp in LAMPS:
        lamp.on = False

def night_light_on():
    set_to_xy(0.675, 0.322, 1)

def set_to_cur_time(trans_time):
    temp, bright = auto_value_now()
    set_to_temp(temp, bright, trans_time)
    return temp, bright

if __name__ == '__main__':
    lamp_probe()
