#!/usr/bin/python3

import requests
from http.server import BaseHTTPRequestHandler, HTTPServer
import ssl
import json

'''Reading configuration'''
import parsed_config

TOKEN = config['telegram']['TOKEN']
URL = config['telegram']['URL']
PORT = int(config['telegram']['PORT'])

#enable the webhook and upload the certificate 
def enableWebhook():
    params = {'url': URL+':'+str(PORT)+'/'}
    r = requests.get("https://api.telegram.org/bot"+TOKEN+"/setWebhook", 
                      params=params,
                      files={'certificate' : open('config/PUBLIC.pem', 'r')})
    print("server replies:",r.json())

def messageInfo(message):
    from_name = message['from']['first_name']
    
    if 'title' in message['chat']:
        chat_name = message['chat']['title']
    elif 'username' in message['chat']:
        chat_name = "@"+message['chat']['username']
    else:
        chat_name = "?"
    
    if 'text' in message.keys():
        text = message['text']
    else:
        text = 'no text was given'
    
    print("<"+chat_name+"> "+from_name+": "+text, end='\n')

def generate_handler():
#   used to pass above vars to myhandler class in a way that works..... je zet
#   eigl de vars in de scope van de class en daarom werky, soort constructor
    class my_handler(BaseHTTPRequestHandler):
    #   check http get requests and start the corresponding functions
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
            data = json.loads(post_body_str)
            
            messageInfo(data['message'])
            
            return
    return my_handler
    
def start_server():
    enableWebhook()
    botServer = HTTPServer(("", PORT), generate_handler())
    botServer.socket = ssl.wrap_socket(botServer.socket, 
                       certfile='config/PUBLIC.pem',
                       keyfile='config/PRIVATE.key',
                       server_side=True)
    try:
        print("starting botServer")
        botServer.serve_forever()
    except KeyboardInterrupt:
        pass
    botServer.server_close()

if __name__ == '__main__':
    start_server()
