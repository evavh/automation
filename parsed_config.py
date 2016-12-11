import os
import configparser

this_file = os.path.dirname(__file__)
config = configparser.RawConfigParser()
config.read(os.path.join(this_file, "config", "config.ini"))
