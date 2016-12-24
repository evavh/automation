#!/usr/bin/python3

#testing the use of crontabs for alarms

from crontab import CronTab
import datetime

time_to_do = datetime.datetime(2016, 8, 24, 0, 45)

my_cron = CronTab(user=True) #load my crontab
my_cron.remove_all(comment="automatic_alarm") #clean up old entries

#create and setup new job
job = my_cron.new(command='/usr/bin/echo "froep" >> /home/eva/cron_test', comment="automatic_alarm")
job.hour.on(time_to_do.hour)
job.minute.also.on(time_to_do.minute)

my_cron.write() #write the changes to the crontab
