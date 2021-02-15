import os
import time
import requests


def save_forecast(adict, config):
    '''
    Send frequent consumption measurement (typically each 5 minutes) to influx.
    val in watt : 
    - negative means that energy is pulled from the electricity net (=consume)
    - positive means that energy is pushed intp the net (=return)
    Optionally, inject and consume in that perid can be included in the measurement
    '''

    epoch = int(time.time())
    url_string = 'http://{}:{}/write?db={}'
    url = url_string.format(config['host'], config['port'], config['db'])
    start_millis = int(epoch) * 1000

    measurement = "forecast"
    istring = measurement+',period="daily"'+" "
    astring = ''
    for akey in adict:
        astring += '{}={},'.format(akey, adict[akey])
    istring += astring
    istring = istring[:-1]
    millis = start_millis
    istring += ' ' + str(millis) + '{0:06d}'.format(0)
    try:
        r = requests.post(url, data=istring, timeout=5)
    except Exception as e:
        print("influxdb post exception forecast", str(e))

if __name__ == "__main__":
    adict = {"today": 900, "tomorrow":450, "day_after": 450}
    config = {"host": "192.168.1.30", "port": 8086, "db": "solar"}
    save_forecast(adict, config)