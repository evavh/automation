#!/usr/bin/python3

import requests
from http.server import BaseHTTPRequestHandler, HTTPServer
import ssl
import json

'''Reading configuration'''
from parsed_config import config

if 'HOST_NAME' in config['http']:
    HOST_NAME = config['http']['HOST_NAME']
else:
    HOST_NAME = ""
TOKEN = config['telegram']['TOKEN']
URL = config['telegram']['URL']
PORT = int(config['telegram']['PORT'])


#enable the webhook and upload the certificate 
def init_webhook():
    params = {'url': URL+':'+str(PORT)+'/'}
    r = requests.get("https://api.telegram.org/bot"+TOKEN+"/setWebhook", 
                      params=params,
                      files={'certificate' : open('config/PUBLIC.pem', 'r')})
    print("server replies:",r.json())

def generate_handler(telegramqueue):
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
            data = json.loads(post_body_str)
            
            if telegramqueue:
                telegramqueue.put(data)
            else:
                print(data)
            
            return
    return my_handler
    
def bot_server_function(telegramqueue=None):
    init_webhook()
    bot_server = HTTPServer((HOST_NAME, PORT), generate_handler(telegramqueue))
    bot_server.socket = ssl.wrap_socket(bot_server.socket, 
                                        certfile='config/PUBLIC.pem',
                                        keyfile='config/PRIVATE.key',
                                        server_side=True)
    try:
        print("starting telegram bot server")
        bot_server.serve_forever()
    except KeyboardInterrupt:
        pass
    bot_server.server_close()

if __name__ == '__main__':
    bot_server_function()
