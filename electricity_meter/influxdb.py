import os
import requests

def send_frequent_electricity_consumption(epoch, balance, config_influxdb, inject=None, consume=None, influx_port=8086):
    '''
    Send frequent consumption measurement (typically each 5 minutes) to influx.
    val in watt : 
    - negative means that energy is pulled from the electricity net (=consume)
    - positive means that energy is pushed intp the net (=return)
    Optionally, inject and consume in that perid can be included in the measurement
    '''

    url_string = 'http://{}:{}/write?db={}'
    url = url_string.format(config_influxdb['host'], config_influxdb['port'], config_influxdb['db'])
    start_millis = int(epoch) * 1000

    measurement = "frequent_consumption_measurement"
    istring = measurement+',period="{}"'.format("300s")+" "
    if inject is not None:
         istring += 'inject={},'.format(inject)
    if consume is not None:
        istring += 'consume={},'.format(consume)
    istring += 'balance={}'.format(balance)
    millis = start_millis
    istring += ' ' + str(millis) + '{0:06d}'.format(0)
    try:
        r = requests.post(url, data=istring, timeout=5)
    except Exception as e:
        print("influxdb post exception", str(e))

def send_daily_meter(epoch, adict, config_influxdb, period='morning'):
    '''
    Send frequent consumption measurement (typically each 5 minutes) to influx.
    val in watt : 
    - negative means that energy is pulled from the electricity net (=consume)
    - positive means that energy is pushed intp the net (=return)
    Optionally, inject and consume in that perid can be included in the measurement
    '''

    url_string = 'http://{}:{}/write?db={}'
    url = url_string.format(config_influxdb['host'], config_influxdb['port'], config_influxdb['db'])
    start_millis = int(epoch) * 1000

    measurement = "daily_meter"
    istring = measurement+',period="{}"'.format(period)+" "
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
        print("influxdb post exception", str(e))

if __name__ == "__main__":
    '''
    adict = {"return": 900, "return1":450, "return2": 450, "consume": 800, "consume1": 400, "consume2": 400}
    send_daily_meter('1612509145', adict, '192.168.1.30', 'morning')
    adict = {"return": 800, "return1":350, "return2": 450, "consume": 200, "consume1": 100, "consume2": 100}
    send_daily_meter('1612541545', adict, '192.168.1.30', 'evening')
    '''
    send_frequent_electricity_consumption('1612541545', -400, "192.168.1.30", inject=0, consume=400)