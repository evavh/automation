#!/usr/bin/python3

#contains the functions for sun simulation and other interactions
#with the hue system

import datetime
import numpy
import phue

BRIDGE = phue.Bridge('192.168.0.100')
LIGHTS = BRIDGE.get_light_objects()

light_by_time = numpy.array([[datetime.time( 8,00), 3500, 255],
                          [datetime.time(20,00), 3000, 255],
                          [datetime.time(20,30), 3000, 255],
                          [datetime.time(21,00), 2800, 255],
                          [datetime.time(21,30), 2500, 200],
                          [datetime.time(22,00), 2300, 150],
                          [datetime.time(22,30), 2000, 100],
                          [datetime.time(23,00), 2000,  50]]).transpose().tolist()

def set_to_temp(temp, bright):
    for light in LIGHTS:
        light.on = True
        light.colortemp_k = temp
        light.brightness = bright
    
    return temp, bright

def auto_value_at_time(time_to_check):
    n_times = len(light_by_time[0])
    
    for (i, time) in enumerate(light_by_time[0]):
        if time_to_check < time:
            if time_to_check > light_by_time[0][i-1]:
                temperature = light_by_time[1][i-1]
                brightness = light_by_time[2][i-1]
                return temperature, brightness
    temp = light_by_time[1][n_times-1]
    bright = light_by_time[2][n_times-1]
    return temp, bright

def is_override():
    hour = datetime.datetime.now().hour
    minute = datetime.datetime.now().minute
    time_to_check = datetime.time(hour, minute)
    for light in LIGHTS:
        if light.on:
            auto_temp, auto_bright = auto_value_at_time(time_to_check)
            lamp_temp = light.colortemp_k
            lamp_bright = light.brightness
            if abs(lamp_temp-auto_temp) > 100 or abs(lamp_bright-auto_bright) > 10:
                return True #at least one light does not have auto's values -> not auto
    return False

def set_off():
    for light in LIGHTS:
        light.on = False

#returns None if no change is required, otherwise temp, bright for current time
def sun_sim(init=False):
    hour = datetime.datetime.now().hour
    minute = datetime.datetime.now().minute
    time_to_check = datetime.time(hour, minute)

    #currently at a change time, so return regardless
    if time_to_check in light_by_time[0]:
        index = light_by_time[0].index(time_to_check)
        temp = light_by_time[1][index]
        bright = light_by_time[2][index]
        return temp, bright
    #in between changes, so return if initializing
    else:
        if init:
            return auto_value_at_time(time_to_check)
        else:
            return None, None

def set_to_cur_time(init=False):
    sun_to_be_set = sun_sim(init)
    if sun_to_be_set:
        temp, bright = sun_to_be_set
        set_to_temp(temp, bright)
        return temp, bright
    else:
        return None, None

if __name__ == '__main__':
    print("Lights set to {}".format(set_to_cur_time()))
