#!/usr/bin/python3

#contains the functions for sun simulation and other interactions
#with the hue system
#temp is colour temperature, bright is brightness

import datetime
import numpy
import phue

import convert_colour
from parsed_config import config

BRIDGE_IP = config['hue']['BRIDGE_IP']

BRIDGE = phue.Bridge(BRIDGE_IP)
LAMPS = BRIDGE.get_light_objects()

lamps_by_time = numpy.array([[datetime.time( 8,00), 3500, 255],
                             [datetime.time(20,00), 3000, 255],
                             [datetime.time(20,30), 3000, 255],
                             [datetime.time(21,00), 2800, 255],
                             [datetime.time(21,30), 2500, 200],
                             [datetime.time(22,00), 2300, 150],
                             [datetime.time(22,30), 2000, 100],
                             [datetime.time(23,00), 2000,  50]]).transpose().tolist()

def lamp_probe():
    for lamp in LAMPS:
        name = lamp.name
        on = lamp.on
        if on:
            colortemp_k = lamp.colortemp_k
            bright = lamp.brightness
            xy = lamp.xy
            print("{} is set to {}K, colour {}, at brightness {}.".format(name, colortemp_k, xy, bright))
        else:
            print("{} is off.".format(name))

def set_to_temp(temp, bright, trans_time):
    for lamp_n in BRIDGE.get_api()['lights'].keys():
        BRIDGE.set_light(int(lamp_n), 'on', True)
        BRIDGE.set_light(int(lamp_n), 'ct', temp)
        BRIDGE.set_light(int(lamp_n), 'bri', 0)
        BRIDGE.set_light(int(lamp_n), 'bri', bright, transitiontime=trans_time)
    
    return temp, bright

def set_to_rgb(r, g, b):
    x, y, bright = convert_colour.rgb_to_xy(r, g, b)
    for lamp in LAMPS:
        lamp.on = True
        lamp.xy = (x, y)
        lamp.brightness = bright

def set_to_xy(x, y, bright):
    for lamp in LAMPS:
        lamp.on = True
        lamp.xy = (x, y)
        lamp.brightness = bright

def auto_value_now():
    hour = datetime.datetime.now().hour
    minute = datetime.datetime.now().minute
    time_to_check = datetime.time(hour, minute)
    
    n_times = len(lamps_by_time[0])
    
    for (i, time) in enumerate(lamps_by_time[0]):
        if time_to_check < time:
            if time_to_check >= lamps_by_time[0][i-1]:
                temp = lamps_by_time[1][i-1]
                bright = lamps_by_time[2][i-1]
                return temp, bright
    temp = lamps_by_time[1][n_times-1]
    bright = lamps_by_time[2][n_times-1]
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
    set_to_temp(2000, 100, 100)
    lamp_probe()
