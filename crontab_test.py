#!/usr/bin/python3

#testing the use of crontabs for alarms

from crontab import CronTab
import datetime

cron = CronTab(tabfile='/etc/crontab', user='eva')

time_to_do = datetime.datetime(2016, 8, 24, 0, 45)

job = cron.new(command='/usr/bin/echo "froep" >> /home/eva/cron_test')
job.hour.on(time_to_do.hour)
job.minute.also.on(time_to_do.minute)

cron.write()
