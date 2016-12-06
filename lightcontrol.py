#contains the functions for sun simulation and other interactions
#with the hue system

import random
import time
import datetime
import numpy as np
import math

from phue import Bridge

bridge = Bridge('192.168.0.100')

lights = bridge.get_light_objects()

lightbytime = np.array([[datetime.time( 8,00), 3500, 255],
               [datetime.time(20,00), 3000, 255],
               [datetime.time(20,30), 3000, 255],
               [datetime.time(21,00), 2800, 255],
               [datetime.time(21,30), 2500, 200],
               [datetime.time(22,00), 2300, 150],
               [datetime.time(22,30), 2000, 100],
               [datetime.time(23,00), 2000,  50]]).transpose().tolist()


def set_to_temp(temperature, brightness):
    for light in lights:
        light.on = True
        light.colortemp_k = temperature
        light.brightness = brightness
    
    return temperature, brightness

def if_auto_now():
    hour = datetime.datetime.now().hour
    minute = datetime.datetime.now().minute
    timetocheck = datetime.time(hour, minute)
    n_times = len(lightbytime[0])
    
    for (i, time) in enumerate(lightbytime[0]):
        if timetocheck < time:
            if timetocheck > lightbytime[0][i-1]:
                temperature = lightbytime[1][i-1]
                brightness = lightbytime[2][i-1]
                return temperature, brightness
    temperature = lightbytime[1][n_times-1]
    brightness = lightbytime[2][n_times-1]
    return temperature, brightness

def is_override():
    for light in lights:
        if light.on:
            temperature, brightness = if_auto_now()
            lamp_temp = light.colortemp_k
            lamp_bri = light.brightness
            if abs(lamp_temp-temperature) > 100 or abs(lamp_bri-brightness) > 10:
                return True #at least one light does not have auto's values -> not auto
    return False

def set_off():
    for light in lights:
        light.on = False

def sun_sim(hour, minute, init=False):
    timetocheck = datetime.time(hour, minute)
    n_times = len(lightbytime[0])

    if timetocheck in lightbytime[0]:
        index = lightbytime[0].index(timetocheck)
        temperature = lightbytime[1][index]
        brightness = lightbytime[2][index]
        return temperature, brightness
    else:
        if init:
            return if_auto_now()
        else:
            return None

def set_to_time(hour, minute, init=False):
    sun = sun_sim(hour, minute, init)
    if sun:
        return set_to_temp(sun[0], sun[1])
    return None

def set_to_cur_time(init=False):
    hour = datetime.datetime.now().hour
    minute = datetime.datetime.now().minute
    return set_to_time(hour, minute, init)
