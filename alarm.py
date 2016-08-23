#!/usr/bin/python3
import requests
import datetime
import math

import google_api
from config import alarm_config

if __name__ == '__main__':
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
    travel_minutes = round(travel_seconds/60)
    travel_time = datetime.timedelta(seconds=travel_seconds)
    
    print("Next event on the calendar is {} on {:%d-%m at %H:%M}".format(first_event['name'], first_event['start']))
    if travel_minutes > 60:
        print("Time to travel from home to {}: {} hours and {} minutes".format(expanded_location, math.floor(travel_minutes/60), travel_minutes%60))
    else:
        print("Time to travel from home to {}: {} minutes".format(expanded_location, travel_minutes))
