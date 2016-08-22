import random
import time
import datetime
import numpy as np

from phue import Bridge
import colourconvert

bridge = Bridge('192.168.0.100')

lights = bridge.get_light_objects()

lightbytime = np.array([[datetime.time( 8,00), 4000, 255],
               [datetime.time(20,00), 3500, 255],
               [datetime.time(20,30), 3500, 255],
               [datetime.time(21,00), 3000, 200],
               [datetime.time(21,30), 3000, 200],
               [datetime.time(22,00), 2500, 150],
               [datetime.time(22,30), 2000, 100],
               [datetime.time(23,00), 1700,  50]]).transpose().tolist()


def set_to_temp(temperature, brightness=-1):
    rgb = colourconvert.temp_to_rgb(temperature)
    xyb = colourconvert.rgb_to_xy(rgb[0], rgb[1], rgb[2])
    xy = [xyb[0], xyb[1]]
    
    if brightness == -1:
        if temperature < 6600:
            brightness = xyb[2]
        else:
            brightness = 255
    
    print("Lights set to", str(temperature)+"K at brightness", brightness)
    
    for light in lights:
        light.on = True
        light.xy = xy
    temperature = 3500
    light.brightness = brightness
    
    return temperature, brightness

def set_off():
    for light in lights:
        light.on = False
    print("Lights set to off")

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
            for (i, time) in enumerate(lightbytime[0]):
                if timetocheck < time:
                    if timetocheck > lightbytime[0][i-1]:
                        temperature = lightbytime[1][i-1]
                        brightness = lightbytime[2][i-1]
                        return temperature, brightness
            temperature = lightbytime[1][n_times-1]
            brightness = lightbytime[2][n_times-1]
            return temperature, brightness
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
