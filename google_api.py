#!/usr/bin/python3

import requests
import time
import configparser
import os
import datetime

def authorization_init(client_id, client_secret, scopes):
    auth_response = requests.post("https://accounts.google.com/o/oauth2/device/code",
                                  params={'client_id':client_id, 'scope':scopes})
    
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
                                        params={'client_id':client_id,
                                        'client_secret':client_secret,
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
    expires_in = access_response['expires_in']
    refresh_token = access_response['refresh_token']
    
    return access_token, expires_in, refresh_token

def refresh_access(client_id, client_secret, refresh_token):
    refresh_response = requests.post("https://www.googleapis.com/oauth2/v4/token",
                                     params={'client_id':client_id,
                                             'client_secret':client_secret,
                                             'refresh_token':refresh_token,
                                             'grant_type':"refresh_token"})
    refresh_response = refresh_response.json()
    
    access_token = refresh_response['access_token']
    expires_in = refresh_response['expires_in']
    
    return access_token, expires_in

def setup():
    #Load config
    this_file = os.path.dirname(__file__)
    config = configparser.RawConfigParser()
    config.read(os.path.join(this_file, "google_config.ini"))
    
    #Check whether config is complete
    for key in ['client_id', 'client_secret', 'targets', 'hours_ahead']:
        if not key in config['client_data'] and not key in config['practical']:
            raise KeyError("Missing key '{}' in config file".format(key))
    
    #Load config data
    client_id = config['client_data']['client_id']
    client_secret = config['client_data']['client_secret']
    targets = config['practical']['targets'].split(',')
    hours_ahead = int(config['practical']['hours_ahead'])
    
    #Use old refresh token if available
    if 'refresh_token' in config['tokens']:
        refresh_token = config['tokens']['refresh_token']
        access_token, expires_in = refresh_access(client_id, client_secret, refresh_token)
    else:
        #Initiate new authorization
        access_token, expires_in, refresh_token = authorization_init(client_id,
                                                                     client_secret,
                                                                     ["https://www.googleapis.com/auth/calendar.readonly"])
        #Write new refresh token to config
        config['tokens']['refresh_token'] = refresh_token
        with open("google_config.ini", 'w') as configfile:
            config.write(configfile)
    
    return access_token, targets, hours_ahead
    
    
def first_event():
    access_token, targets, hours_ahead = setup()
    
    #Get calendar list
    url = "https://www.googleapis.com/calendar/v3/users/me/calendarList"
    headers = {'Authorization':"Bearer "+access_token}
    r = requests.get(url, headers=headers)
    calendar_list = r.json()
    
    #Calculate necessary timestamps for limits
    utc_now = datetime.datetime.utcnow()
    utc_max = utc_now + datetime.timedelta(hours=hours_ahead)
    utc_now = utc_now.isoformat('T')[:19]+'Z'
    utc_max = utc_max.isoformat('T')[:19]+'Z'
    
    #Run through calendar list
    next_event_list = []
    for calendar in calendar_list['items']:
        if calendar['summary'] in targets:
            
            #Get event list for this calendar
            parameters = {'timeMin':utc_now, 'timeMax':utc_max, 'singleEvents':True, 'orderBy':'startTime'}
            url = "https://www.googleapis.com/calendar/v3/calendars/{}/events".format(calendar['id'])
            headers = {'Authorization':"Bearer "+access_token}
            r = requests.get(url, headers=headers, params=parameters)
            event_list = r.json()['items']
            
            if event_list == []:
                print("No events within {} hours in {}".format(hours_ahead, calendar['summary']))
            else:
                print("{} events within {} hours in {}".format(len(event_list), hours_ahead, calendar['summary']))
                #Run through events to find the first one that matches the conditions
                #(has name, has start time, is marked as busy)
                for event in event_list:
                    if 'summary' in event and 'dateTime' in event['start']: #event has name and start time (not all day)
                        if 'transparency' in event and event['transparency'] == 'transparent':
                            print("Event {} marked as available".format(event['summary']))
                        else: #event is marked as busy
                            next_event = {}
                            next_event['name'] = event['summary']
                            
                            start_timestamp = event['start']['dateTime']
                            next_event['start'] = datetime.datetime.strptime(start_timestamp[:19], '%Y-%m-%dT%H:%M:%S')
                        
                            if 'location' in event:
                                next_event['location'] = event['location']
                            
                            break #first event that matches breaks the loop
                
                next_event_list.append(next_event)
    if next_event_list == []:
        print("No events found within {} hours, feel free to sleep however long!".format(hours_ahead))
        first_event = None
    else:
        sorted_list = sorted(next_event_list, key=lambda k: k['start'])
        first_event = sorted_list[0]
        print("The first event to occur is {} on datetime {}".format(first_event['name'], first_event['start']))
    
    return first_event

if __name__ == '__main__':
    print(first_event())
