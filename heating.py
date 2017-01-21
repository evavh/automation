import serial

from config import *

NO_HEATING = 0
LOW_TEMP = 50
HIGH_TEMP = 150

def set_servo(target)
	with serial.Serial('/dev/ttyAMA0', 9600, timeout=1) as servo:
		servo.write(target)
		
		while !response:
			response = servo.readline()
		
		return response

def off():
	set_servo(NO_HEATING)

def low():
	set_servo(LOW_TEMP)

def high():
	set_servo(HIGH_TEMP)

if __name__ == '__main__':
	target = input("Servo target: ")
	set_servo(target)
