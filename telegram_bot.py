#!/usr/bin/python3

import requests
from http.server import BaseHTTPRequestHandler, HTTPServer
import ssl
import json
import os
import time
import emoji

import plotting
import helpers
import alarm
from config import *

KEYBOARD = ([["status", "get_alarm", "graph_temp"],
             ["alarm-15", "clear_alarm", "alarm+15"],
             ["night_on", "night_off"],
             ["night_light_on", "night_light_off"]])

def send_message(text, chat_id, message_id=None):
    if message_id:
        bot_message = {'text': text, 'chat_id': chat_id, 'reply_to_message_id': message_id,
                       'reply_markup': json.dumps({"selective": True, "keyboard": KEYBOARD})}
    else:
        bot_message = {'text': text, 'chat_id': chat_id,
                       'reply_markup': json.dumps({"selective": False, "keyboard": KEYBOARD})}
    
    if text == "<plot>":
        my_files={'photo': open(TELEGRAM_PLOT_FILE, 'rb')}
        requests.post("https://api.telegram.org/bot"+TELEGRAM_TOKEN+"/sendPhoto", params=bot_message, files=my_files)
    else:
        requests.post("https://api.telegram.org/bot"+TELEGRAM_TOKEN+"/sendMessage", params=bot_message)  
    

def status_text(command_queue, status_queue):
    command_queue.put("telegram:request_status")
    status = status_queue.get(block=True)
    
    temp = status['temp']
    light_level = status['light_level']
    
    curtain = status['curtain']
    present = status['present']
    night_mode = status['night_mode']
    override = status['override']
    
    lamps_off = status['lamps_off']
    lamps_colour = status['lamps_colour']
    lamps_bright = status['lamps_bright']
    
    alarm_time = status['alarm_time']
    
    reply_text = "---Current system status---\n:thermometer:{}°C   :candle:{}".format(temp, light_level)
    
    if present:
        reply_text += "    :monkey_face:"
    else:
        reply_text += "    :see_no_evil:"
    
    if night_mode:
        reply_text += ":crescent_moon:"
    else:
        reply_text += ":sunny:"
    
    if override:
        reply_text += ":unlock:"
    else:
        reply_text += ":lock:"
    
    reply_text += '\n'
    
    if lamps_off:
        reply_text += ":bulb: off\n"
    else:
        reply_text += ":bulb: {}K at {}%\n".format(lamps_colour, round(lamps_bright/2.55))
    
    if alarm_time:
        reply_text += ":alarm_clock: {:%H:%M}".format(alarm_time)
    else:
        reply_text += ":alarm_clock: none"
    
    return emoji.emojize(reply_text, use_aliases=True)

def determine_reply(message_text, command_queue, status_queue):
    reply_text = None
    if "status" in message_text:
        reply_text = status_text(command_queue, status_queue)
    elif "night_on" in message_text:
        command_queue.put("command:night_on")
        reply_text = status_text(command_queue, status_queue)
    elif "night_off" in message_text:
        command_queue.put("command:night_off")
        reply_text = status_text(command_queue, status_queue)
    elif "night_light_on" in message_text:
        command_queue.put("command:night_light_on")
        reply_text = status_text(command_queue, status_queue)
    elif "night_light_off" in message_text:
        command_queue.put("command:night_light_off")
        reply_text = status_text(command_queue, status_queue)
    elif "get_alarm" in message_text:
        reply_text = "Alarm would be set for {:%H:%M}.".format(alarm.alarm_time())
    elif "clear_alarm" in message_text:
        command_queue.put("command:clear_alarm")
        reply_text = status_text(command_queue, status_queue)
    elif "alarm+15" in message_text:
        old_alarm_time = alarm.get_cron_alarm()
        if old_alarm_time:
            alarm.set_cron_alarm(old_alarm_time + datetime.timedelta(minutes=15))
            reply_text = status_text(command_queue, status_queue)
        else:
            reply_text = "No alarm set."
    elif "alarm-15" in message_text:
        old_alarm_time = alarm.get_cron_alarm()
        if old_alarm_time:
            alarm.set_cron_alarm(old_alarm_time - datetime.timedelta(minutes=15))
            reply_text = status_text(command_queue, status_queue)
        else:
            reply_text = "No alarm set."
    elif "graph_temp" in message_text:
        start_command = message_text.find("graph_temp")
        arguments = message_text[start_command:].split()[1:]
        days = helpers.to_int_if_possible(arguments, 0)
        if days is not None:
            hours = helpers.to_int_if_possible(arguments, 1)
            if hours is not None:
                plotting.temp_plot_last(TELEGRAM_PLOT_FILE, days, hours)
            else:
                plotting.temp_plot_last(TELEGRAM_PLOT_FILE, days)
        else:
            plotting.temp_plot_last(TELEGRAM_PLOT_FILE)
        reply_text = '<plot>' #gets replaced by a plotted picture in send function
    
    return reply_text

def handle_message(message, command_queue, status_queue):
    if message:
        if message['date'] > time.time() - 60:
            #extract information
            message_id = message['message_id']
            from_id = message['from']['id']
            from_name = message['from']['first_name']
            chat_id = message['chat']['id']
            message_text = message['text']
            if 'title' in message['chat']:
                is_group = True
            else:
                is_group = False
            
            print(from_id, from_name)
            if from_id in TELEGRAM_USER_IDS:
                reply_text = determine_reply(message_text, command_queue, status_queue)
                if is_group: #reply to specific message
                    if reply_text: #we recognise a command to respond to
                        send_message(reply_text, chat_id, message_id)
                else: #send to private chat
                    if reply_text:
                        send_message(reply_text, chat_id)
            else:
                if is_group:
                    send_message("{}, no! 3:!".format(from_name), chat_id, message_id)
                else:
                    send_message("{}, no! 3:!".format(from_name), chat_id)

#enable the webhook and upload the certificate 
def init_webhook():
    params = {'url': MY_URL+':'+str(TELEGRAM_PORT)+'/'}
    r = requests.get("https://api.telegram.org/bot"+TELEGRAM_TOKEN+"/setWebhook", 
                      params=params,
                      files={'certificate' : open(TELEGRAM_PUBLIC_KEY, 'r')})
    reply = r.json()
    if reply['result'] and reply['ok']:
        helpers.write_log("telegram webhook set succesfully")
    else:
        helpers.write_log("no telegram webhook set, server replied: {}".format(reply))

def generate_handler(command_queue, status_queue):
    #used to pass above vars to myhandler class in a way that works..... je zet
    #eigl de vars in de scope van de class en daarom werky, soort constructor
    class my_handler(BaseHTTPRequestHandler):
        #check http get requests and start the corresponding functions
        def do_POST(self):
            #reply data recieved succesfully (otherwise endless spam)
            message = json.dumps({})
            self.send_response(200)
            self.send_header('Content-type','application/json')
            self.end_headers()
            self.wfile.write(message.encode('utf-8')) #send bytestring not utf8  
            
            #decode and read the data
            content_len = int(self.headers['content-length'])
            post_body = self.rfile.read(content_len)
            post_body_str = post_body.decode("utf-8")
            message = json.loads(post_body_str)['message']
            
            handle_message(message, command_queue, status_queue)
            
            return
    return my_handler
    
def bot_server_function(command_queue=None, status_queue=None):
    init_webhook()
    bot_server = HTTPServer((HOST_NAME, TELEGRAM_PORT), generate_handler(command_queue, status_queue))
    bot_server.socket = ssl.wrap_socket(bot_server.socket, 
                                        certfile=TELEGRAM_PUBLIC_KEY,
                                        keyfile=TELEGRAM_PRIVATE_KEY,
                                        server_side=True)
    try:
        bot_server.serve_forever()
    except KeyboardInterrupt:
        pass
    bot_server.server_close()

if __name__ == '__main__':
    bot_server_function()
