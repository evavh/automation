#!/usr/bin/python3

import requests
import datetime
from crontab import CronTab

import google_api
import music
import helpers

from config import *

def first_event_timing():
    first_event = google_api.first_event()
    if not first_event:
        return None
    
    time_at_destination = first_event['start']
    if "location" in first_event:
        location = first_event['location']
        
        expanded_location = location
        for key in KNOWN_LOCATIONS:
            if location.startswith(key):
                expanded_location = KNOWN_LOCATIONS[key]
                break
        
        url = "https://maps.googleapis.com/maps/api/distancematrix/json"
        parameters = {'mode':"walking", 'origins':KNOWN_LOCATIONS['Thuis'], 'destinations':expanded_location, 'key':GOOGLE_MAPS_API_KEY}
        r = requests.get(url, params=parameters)
        distance_matrix = r.json()
        
        if distance_matrix['rows'][0]['elements'][0]['status'] == 'OK':
            travel_seconds = distance_matrix['rows'][0]['elements'][0]['duration']['value']/3
            travel_time = datetime.timedelta(seconds=travel_seconds)
        else:
            travel_time = datetime.timedelta(minutes=30)
            helpers.write_log("WARNING: first event location not recognised, using default timing.")
    else:
        travel_time = datetime.timedelta(minutes=30)
        helpers.write_log("WARNING: first event has no location, using default timing.")
    
    return first_event, travel_time

def alarm_time():
    timing = first_event_timing()
    sleep_delta = datetime.timedelta(hours=OPTIMAL_SLEEP_HOURS)
    if timing:
        first_event, travel_time = timing
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
    job = my_cron.new(command=ALARM_FILE, comment="automatic_alarm")
    job.hour.on(alarm_time.hour)
    job.minute.also.on(alarm_time.minute)
    
    my_cron.write() #write the changes to the crontab

def get_cron_alarm():
    my_cron = CronTab(user=True) #load my crontab
    alarms = list(my_cron.find_comment("automatic_alarm"))
    if alarms:
        schedule = alarms[0].schedule(date_from=datetime.datetime.now())
        return schedule.get_next()
    else:
        return None

def clear_alarm():
    my_cron = CronTab(user=True) #load my crontab
    my_cron.remove_all(comment="automatic_alarm") #clean up old entries
    my_cron.write() #write the changes to the crontab

if __name__ == '__main__':
    music.start_shuffle_playlist(WAKEUP_PLAYLIST)
    commands = {'command': 'night_off'}
    requests.post("http://127.0.0.1:"+str(HTTP_PORT), data=commands)
