#!/usr/bin/python3

#an implementation for the google calendar api, with as main use to
#get the first upcoming event and its properties

import requests
import time
import configparser
import os
import datetime

import helpers
from config import *

def authorization_init():
    scopes = ["https://www.googleapis.com/auth/calendar.readonly"]
    auth_response = requests.post("https://accounts.google.com/o/oauth2/device/code",
                                  params={'client_id':GOOGLE_CLIENT_ID, 'scope':scopes})
    
    auth_response = auth_response.json()
    
    user_code = auth_response['user_code']
    verification_url = auth_response['verification_url']
    device_code = auth_response['device_code']
    interval = auth_response['interval']
    
    print("Go to {} and enter the code {}".format(verification_url, user_code))
    
    print("Authorization pending...")
    
    access = False
    while not access:
        access_response = requests.post("https://www.googleapis.com/oauth2/v4/token",
                                        params={'client_id':GOOGLE_CLIENT_ID,
                                        'client_secret':GOOGLE_CLIENT_SECRET,
                                        'code':device_code,
                                        'grant_type':"http://oauth.net/grant_type/device/1.0"})
        access_response = access_response.json()
        
        if 'error' in access_response:
            if not access_response['error'] == "authorization_pending":
                print(access_response['error'], access_response['error_description'])
                break
            time.sleep(interval)
        else:
            print("Access granted by user\n")
            access = True

    access_token = access_response['access_token']
    refresh_token = access_response['refresh_token']
    
    return access_token, refresh_token

def refresh_access():
    refresh_response = requests.post("https://www.googleapis.com/oauth2/v4/token",
                                     params={'client_id':GOOGLE_CLIENT_ID,
                                             'client_secret':GOOGLE_CLIENT_SECRET,
                                             'refresh_token':GOOGLE_REFRESH_TOKEN,
                                             'grant_type':"refresh_token"})
    refresh_response = refresh_response.json()
    
    access_token = refresh_response['access_token']
    
    return access_token

def setup():   
    #Use old refresh token if available
    if GOOGLE_REFRESH_TOKEN:
        access_token = refresh_access()
    else:
        #Initiate new authorization
        access_token, refresh_token = authorization_init()
        
        #Write new refresh token to file and log the fact
        with open(os.path_join(SERVER_DIRECTORY, "config", "NEW_GOOGLE_REFRESH_TOKEN"), 'w') as tokenfile:
            tokenfile.write(refresh_token)
        helpers.write_log("new refresh token created, copy contents of config/NEW_GOOGLE_REFRESH_TOKEN to the appropriate place in config.py")
    
    return access_token
    
def first_event():
    access_token = setup()
    
    #Get calendar list
    url = "https://www.googleapis.com/calendar/v3/users/me/calendarList"
    headers = {'Authorization':"Bearer "+access_token}
    r = requests.get(url, headers=headers)
    calendar_list = r.json()
    
    #Calculate necessary timestamps for limits
    utc_now = datetime.datetime.utcnow()
    utc_max = utc_now + datetime.timedelta(hours=ALARM_HOURS_AHEAD)
    utc_now = utc_now.isoformat('T')[:19]+'Z'
    utc_max = utc_max.isoformat('T')[:19]+'Z'
    
    #Run through calendar list
    next_event_list = []
    for calendar in calendar_list['items']:
        if calendar['summary'] in GOOGLE_CAL_TARGETS:
            
            #Get event list for this calendar
            parameters = {'timeMin':utc_now, 'timeMax':utc_max, 'singleEvents':True, 'orderBy':'startTime'}
            url = "https://www.googleapis.com/calendar/v3/calendars/{}/events".format(calendar['id'])
            headers = {'Authorization':"Bearer "+access_token}
            r = requests.get(url, headers=headers, params=parameters)
            event_list = r.json()['items']
            
            if not event_list == []:
                next_event = None
                #Run through events to find the first one that matches the conditions
                #(has name, has start time, is marked as busy)
                for event in event_list:
                    if 'summary' in event and 'dateTime' in event['start']: #event has name and start time (not all day)
                        if not 'transparency' in event: #event is marked as busy
                            next_event = {}
                            next_event['name'] = event['summary']
                            
                            start_timestamp = event['start']['dateTime']
                            next_event['start'] = datetime.datetime.strptime(start_timestamp[:19], '%Y-%m-%dT%H:%M:%S')
                        
                            if 'location' in event:
                                next_event['location'] = event['location']
                            
                            break #first event that matches breaks the loop
                
                if next_event:
                    next_event_list.append(next_event)
    if next_event_list == []:
        first_event = None
    else:
        sorted_list = sorted(next_event_list, key=lambda k: k['start'])
        first_event = sorted_list[0]
    
    return first_event

if __name__ == '__main__':
    print(first_event())
