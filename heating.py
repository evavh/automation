#!/usr/bin/python3
import serial

from config import *

NO_HEATING = 0
LOW_TEMP = 50
HIGH_TEMP = 150

def set_servo(target):
    with serial.Serial('/dev/ttyUSB0', 9600, timeout=1) as servo:
        servo.write((str(target)+'\n').encode('utf-8'))
        print((str(target)+'\n').encode('utf-8'))
        
        print("written to servo")
        
        response = servo.readline()
        print(response)
        while not response:
            response = servo.readline()
            print(response)
        
        return response

def off():
    set_servo(NO_HEATING)

def low():
    set_servo(LOW_TEMP)

def high():
    set_servo(HIGH_TEMP)

if __name__ == '__main__':
    while True:
        target = input("Servo target: ")
        print(set_servo(target))
