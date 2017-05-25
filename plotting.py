#!/usr/bin/python3

#functions for plotting, can be run with command line arguments day and
#hour to plot the last timeslot of temperature readings

import numpy as np
import math
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
import datetime
import time
import sys
import os

from config import *

def temp_plot(filename, plotname, begin_date, end_date, hour_interval=1, short_ticks=False):
    array = np.loadtxt(filename).transpose()
    
    timestamp = array[0]
    temperature = array[1]
    
    dates = np.tile(datetime.datetime(1900, 1, 1), len(timestamp))
    begin_found = False
    end_found = False
    
    for i, stamp in enumerate(timestamp):
        date = datetime.datetime.fromtimestamp(stamp)
        dates[i] = date
        if not begin_found and abs(date - begin_date) < datetime.timedelta(minutes=10):
            begin_index = i
        if not end_found and abs(date - end_date) < datetime.timedelta(minutes=10):
            end_index = i
        
    
    fig, ax = plt.subplots()
    
    day_locator = matplotlib.dates.DayLocator()
    hour_locator = matplotlib.dates.HourLocator()
    ax.xaxis.set_major_locator(matplotlib.dates.DayLocator())
    ax.xaxis.set_minor_locator(matplotlib.dates.HourLocator(byhour=np.arange(0, 24, hour_interval)))
    
    if short_ticks:
        ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%d'))
        plt.xlabel("Day")
    else:
        ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%d-%m'))
        ax.xaxis.set_minor_formatter(matplotlib.dates.DateFormatter('%H'))
        plt.tick_params(axis='x', pad=20)
        plt.xlabel("Hour and date")
    
    temperature_to_plot = temperature[begin_index:end_index]
    
    plt.ylabel("Temperature [C]")
    plt.ylim(math.floor(min(temperature_to_plot)), math.ceil(max(temperature_to_plot)))
    plt.xlim(begin_date, end_date)
    
    plt.grid(which='major', axis='both', linestyle='dashed')
    plt.grid(which='minor', axis='x', linestyle='dotted')
    
    plt.title("The temperature of the room")
    
    low_temp = temperature.copy()
    med_temp = temperature.copy()
    high_temp = temperature.copy()
    
    temperature_shift_up = np.append(temperature[1:], np.nan)
    
    for i in range(0, len(temperature)-1):
        if temperature[i] > 20 and temperature[i+1] > 20:
            low_temp[i] = np.nan
            if temperature[i] > 24 and temperature[i+1] > 24:
                med_temp[i] = np.nan
            elif temperature[i] <= 24 and temperature[i+1] <= 24:
                high_temp[i] = np.nan
        elif temperature[i] <= 20 and temperature[i+1] <=20:
            med_temp[i] = np.nan
            high_temp[i] = np.nan
    
    
    plt.plot(dates, low_temp, color='b')
    plt.plot(dates, med_temp, color='g')
    plt.plot(dates, high_temp, color='r')
    
    plt.tight_layout()
    plt.savefig(plotname)

def temp_plot_last(plotname, days=1, hours=0):
    now = datetime.datetime.now()
    
    begin_date = now - datetime.timedelta(days=days, hours=hours)
    end_date = now
    
    short_ticks = False
    
    if days > 1 or (days == 1 and hours > 6):
        if days > 3:
            if days > 6:
                hour_interval = 12
                if days > 10:
                    short_ticks = True
            else:
                hour_interval = 6
        else:
            hour_interval = 3
    else:
        hour_interval = 1
    
    cur_day = now.day
    
    if cur_day <= days:
        temp_plot(SERVER_DIRECTORY+"/logs/temp_log", plotname, begin_date, end_date, hour_interval, short_ticks)
    else:
        temp_plot(SERVER_DIRECTORY+"/logs/temp_log_{}".format(now.strftime("%Y-%m")), plotname, begin_date, end_date, hour_interval, short_ticks)

def convert_wrong_format(filename):
    faulty_array = np.loadtxt(filename, dtype=bytes, delimiter='\t')
    proper_array = np.array([["a", "b"]])
    print(faulty_array)
    for i, line in enumerate(faulty_array):
        dt_object = datetime.datetime.strptime(line[0].decode("utf-8") , "%Y-%m-%d %H:%M:%S")
        timestamp = str(time.mktime(dt_object.timetuple()))
        measurement = line[1].decode("utf-8")
        proper_array = np.append(proper_array, [[timestamp, measurement]], axis=0)
    print(proper_array)
    np.savetxt(filename+"_proper", proper_array, delimiter='\t', fmt="%s")

if __name__ == '__main__':
    arguments = sys.argv
    if len(arguments) == 2:
        temp_plot_last(SERVER_DIRECTORY+"/plots/temp_manual_plot", int(arguments[1]))
    elif len(arguments) == 3:
        temp_plot_last(SERVER_DIRECTORY+"/plots/temp_manual_plot", int(arguments[1]), int(arguments[2]))
    else:
        print("Invalid number of arguments: {}".format(len(sys.argv)-1))
