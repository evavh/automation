#!/usr/bin/python3
import requests
import datetime
import math

import google_api
from config import alarm_config

def timing():
    first_event = google_api.first_event()
    time_at_destination = first_event['start']
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
    
    return first_event, travel_time

def getup_time(first_event, travel_time):
    sleep_at = datetime.datetime.now()
    needed_sleep = datetime.timedelta(hours=9, minutes=30)
    
    routine = datetime.timedelta(minutes=45)
    extra = datetime.timedelta(minutes=10)
    
    total_time = travel_time + routine + extra
    
    if sleep_at + needed_sleep + total_time > first_event['start']:
        getup_time = first_event['start'] - total_time
        enough_sleep = False
    else:
        getup_time = sleep_at + needed_sleep
        enough_sleep = True
    
    return getup_time, enough_sleep

if __name__ == '__main__':
    first_event, travel_time = timing()
    travel_seconds = travel_time.total_seconds()
    travel_minutes = math.ceil(travel_seconds/60)
    
    if travel_minutes > 60:
        timestring = "{} hours and {} minutes".format(math.floor(travel_minutes/60), travel_minutes%60)
    else:
        timestring = "{} minutes".format(travel_minutes)
    
    print("Time to travel to {} at {:%H:%M}: {}".format(first_event['name'], first_event['start'], timestring))
    
    getup_time, enough_sleep = getup_time(first_event, travel_time)
    
    if enough_sleep:
        enoughstring = ""
    else:
        enoughstring = "not "
    
    print("Time to get up: {:%H:%M} ({}enough sleep)".format(getup_time, enoughstring))
