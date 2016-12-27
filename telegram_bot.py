#!/usr/bin/python3

import requests
from http.server import BaseHTTPRequestHandler, HTTPServer
import ssl
import json
import os
import time

from main import write_log

'''Reading configuration'''
from parsed_config import config

if 'HOST_NAME' in config['http']:
    HOST_NAME = config['http']['HOST_NAME']
else:
    HOST_NAME = ""
TOKEN = config['telegram']['TOKEN']
URL = config['telegram']['URL']
PORT = int(config['telegram']['PORT'])
USER_ID = int(config['telegram']['USER_ID'])

THIS_FILE = os.path.dirname(__file__)
PUBLIC_KEY = os.path.join(THIS_FILE, "config", "PUBLIC.pem")
PRIVATE_KEY = os.path.join(THIS_FILE, "config", "PRIVATE.key")

def send_message(text, chat_id, message_id=None):
    if message_id:
        bot_message = {'text': text, 'chat_id': chat_id, 'reply_to_message_id': message_id}
    else:
        bot_message = {'text': text, 'chat_id': chat_id}
    requests.post("https://api.telegram.org/bot"+TOKEN+"/sendMessage", params=bot_message)

def determine_reply(message_text, command_queue, status_queue):
    if "/status" in message_text:
        command_queue.put("telegram:request_status")
        status = status_queue.get(block=True)
        light_level = status['light_level']
        curtain = status['curtain']
        temp = status['temp']
        night_mode = status['night_mode']
        present = status['present']
        lamps_colour = status['lamps_colour']
        lamps_bright = status['lamps_bright']
        lamps_off = status['lamps_off']
        reply_text = "System status:\nTemperature: {}C\nLight level: {}\nLamp colour: {}K\nLamp brightness: {}\n".format(temp, light_level, lamps_colour, lamps_bright)
    elif "/night_on" in message_text:
        command_queue.put("command:night_on")
        reply_text = "It is now night."
    elif "/night_off" in message_text:
        command_queue.put("command:night_off")
        reply_text = "It is now day."
    elif "/night_light_on" in message_text:
        command_queue.put("command:night_light_on")
        reply_text = "Temporary light on."
    elif "/night_light_off" in message_text:
        command_queue.put("command:night_light_off")
        reply_text = "Darkness returns."
    
    return reply_text

def handle_message(message, command_queue, status_queue):
    if message:
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
        
        if message['date'] > time.time() - 60:
            if from_id == USER_ID:
                reply_text = determine_reply(message_text, command_queue, status_queue)
                if is_group:
                    send_message(reply_text, chat_id, message_id)
                else:
                    send_message(reply_text, chat_id)
            else:
                if is_group:
                    send_message("No! 3:!", chat_id, message_id)
                else:
                    send_message("No! 3:!", chat_id)

#enable the webhook and upload the certificate 
def init_webhook():
    params = {'url': URL+':'+str(PORT)+'/'}
    r = requests.get("https://api.telegram.org/bot"+TOKEN+"/setWebhook", 
                      params=params,
                      files={'certificate' : open(PUBLIC_KEY, 'r')})
    reply = r.json()
    if reply['result'] and reply['ok']:
        write_log("telegram webhook set succesfully")
    else:
        write_log("no telegram webhook set, server replied: {}".format(reply))

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
    
def bot_server_function(command_queue, status_queue):
    init_webhook()
    bot_server = HTTPServer((HOST_NAME, PORT), generate_handler(command_queue, status_queue))
    bot_server.socket = ssl.wrap_socket(bot_server.socket, 
                                        certfile=PUBLIC_KEY,
                                        keyfile=PRIVATE_KEY,
                                        server_side=True)
    try:
        bot_server.serve_forever()
    except KeyboardInterrupt:
        pass
    bot_server.server_close()

if __name__ == '__main__':
    bot_server_function()
