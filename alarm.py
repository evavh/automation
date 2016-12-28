#!/usr/bin/python3

#experimental program that as of now only calculates the time to get up

import requests
import datetime
import math
from crontab import CronTab

import google_api
import music
from config import alarm_config

SLEEP_HOURS = 10
WAKEUP_PLAYLIST = "wakeup"

def first_event_timing():
    first_event = google_api.first_event()
    if not first_event:
        return None
    
    time_at_destination = first_event['start']
    if "location" in first_event:
        location = first_event['location']
        
        known_locations = alarm_config.known_locations
        
        expanded_location = location
        for key in known_locations:
            if location.startswith(key):
                expanded_location = known_locations[key]
                break
        
        url = "https://maps.googleapis.com/maps/api/distancematrix/json"
        parameters = {'mode':"walking", 'origins':known_locations['Thuis'], 'destinations':expanded_location, 'key':alarm_config.api_key}
        r = requests.get(url, params=parameters)
        distance_matrix = r.json()
        
        travel_seconds = distance_matrix['rows'][0]['elements'][0]['duration']['value']/3
        travel_time = datetime.timedelta(seconds=travel_seconds)
    else:
        travel_time = datetime.timedelta(minutes=60)
    
    return first_event, travel_time

def alarm_time():
    timing = first_event_timing()
    sleep_delta = datetime.timedelta(hours=SLEEP_HOURS)
    if timing:
        first_event, travel_time = first_event_timing()
        routine = datetime.timedelta(minutes=45)
        extra = datetime.timedelta(minutes=10)
        total_time = travel_time + routine + extra
        
        getup_time = first_event['start'] - total_time
        
        #if there is plenty of time to sleep
        if getup_time - datetime.datetime.now() > sleep_delta:
            return datetime.datetime.now() + sleep_delta
        else:
            return getup_time
    else:
        return datetime.datetime.now() + sleep_delta

def set_cron_alarm(alarm_time):
    my_cron = CronTab(user=True) #load my crontab
    my_cron.remove_all(comment="automatic_alarm") #clean up old entries
    
    #create and setup new job
    job = my_cron.new(command='/home/eva/server/alarm.py', comment="automatic_alarm")
    job.hour.on(alarm_time.hour)
    job.minute.also.on(alarm_time.minute)
    
    my_cron.write() #write the changes to the crontab

def clear_alarm():
    my_cron = CronTab(user=True) #load my crontab
    my_cron.remove_all(comment="automatic_alarm") #clean up old entries
    my_cron.write() #write the changes to the crontab

if __name__ == '__main__':
    music.start_shuffle_playlist(WAKEUP_PLAYLIST)
    commands = {'command': 'night_off'}
    requests.post("192.168.0.111:8080", params=commands)
