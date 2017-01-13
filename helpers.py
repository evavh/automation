import os
import datetime
import time

THIS_FILE = os.path.dirname(__file__)

def write_log(message, filename="server_log", date_format=True):
    date = datetime.datetime.now()
    with open(os.path.join(THIS_FILE, "logs", filename), 'a') as f:
        if date_format is False:
            f.write("{}\t{}\n".format(time.time(), message))
        else:
            date_string = date.strftime("%Y-%m-%d %H:%M:%S")
            f.write("{}\t{}\n".format(date_string, message))
        f.close()

def to_int_if_possible(variable, list_argument=None):
    try:
        if list_argument is None:
            integer = int(variable)
        else:
            integer = int(variable[list_argument])
        return integer
    except Exception:
        return None
