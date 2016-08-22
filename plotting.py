#!/usr/bin/python3
import numpy as np
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from datetime import datetime, timedelta
import sys

def temp_plot(filename, plotname, begin_date, end_date, hour_interval=1, short_ticks=False):
    array = np.loadtxt(filename).transpose()
    
    timestamp = array[0]
    temperature = array[1]
    
    dates = np.tile(datetime(1900, 1, 1), len(timestamp))
    
    for i, stamp in enumerate(timestamp):
        date = datetime.fromtimestamp(stamp)
        dates[i] = date
    
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
    
    plt.ylabel("Temperature [C]")
    plt.xlim(begin_date, end_date)
    
    plt.grid(which='major', axis='both', linestyle='dashed')
    plt.grid(which='minor', axis='x', linestyle='dotted')
    
    plt.title("The temperature of the room")
    
    low_temp = temperature.copy()
    high_temp = temperature.copy()
    
    temperature_shift_up = np.append(temperature[1:], np.nan)
    
    for i in range(0, len(temperature)-1):
        if temperature[i] > 24 and temperature[i+1] > 24:
            low_temp[i] = np.nan
        elif temperature[i] <= 24 and temperature[i+1] <= 24:
            high_temp[i] = np.nan
    
    #print(len(low_temp))
    #print(len(high_temp), len(dates))
    
    plt.plot(dates, low_temp, color='b')
    plt.plot(dates, high_temp, color='r')
    
    plt.tight_layout()
    plt.savefig(plotname)

def temp_plot_last(plotname, days=1, hours=0):
    now = datetime.now()
    
    begin_date = now - timedelta(days=days, hours=hours)
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
        temp_plot("logs/temp_log", plotname, begin_date, end_date, hour_interval, short_ticks)
    else:
        temp_plot("logs/temp_log_{}".format(now.strftime("%Y-%m")), plotname, begin_date, end_date, hour_interval, short_ticks)

if __name__ == '__main__':
    arguments = sys.argv
    if len(arguments) == 2:
        temp_plot_last("plots/temp_manual_plot", int(arguments[1]))
    elif len(arguments) == 3:
        temp_plot_last("plots/temp_manual_plot", int(arguments[1]), int(arguments[2]))
    else:
        print("Invalid number of arguments: {}".format(len(sys.argv)-1))
