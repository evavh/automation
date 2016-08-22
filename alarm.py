#!/usr/bin/python3
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
            expanded_location = known_locations[location]
            break

    print(expanded_location)
