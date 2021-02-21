import os
import time
import requests
from inverter.sunny_boy import SunnyBoyInverter

invertor_types = {
    "SunnyBoy": SunnyBoyInverter,
}


def register_inverter(config):
    if config['type'] in invertor_types:
        inverter_used = invertor_types[config['type']](config)
        return inverter_used
    return None

def get_total_power(inverter_used):
    return inverter_used.get_total_power()

def get_today_yield(inverter_used):

    return inverter_used.get_today_yield()

def send_daily_yield(today_yield, config_influxdb):
    if len(today_yield) == 0:
        return
    prev_5min_watt = int(today_yield[0]['watt'])
    prev_5min_epoch = int(today_yield[0]['epoch'])

    for rec in today_yield:
        try:
            yield_5min = int(rec['watt'])- prev_5min_watt
        except:
            yield_5min = 0
        if yield_5min > 0:
            epoch = int(rec['epoch'])
            time_elapsed = epoch - prev_5min_epoch
            yield_watt = int(3600/time_elapsed*yield_5min)

            url_string = 'http://{}:{}/write?db={}'
            url = url_string.format(config_influxdb['host'], config_influxdb['port'], config_influxdb['db'])
            start_millis = int(epoch) * 1000

            measurement = "inverter_daily"
            istring = measurement+',period="{}"'.format("300s")+" "
            istring += 'watt={}'.format(yield_watt)
            millis = start_millis
            istring += ' ' + str(millis) + '{0:06d}'.format(0)
            try:
                r = requests.post(url, data=istring, timeout=5)
            except Exception as e:
                print("influxdb post exception", str(e))

        prev_5min_watt = int(rec['watt'])
        prev_5min_epoch = int(rec['epoch'])

def send_daily_total_power(total_power, yesterday_total_power, config_influxdb):
    epoch = int(time.time())
    url_string = 'http://{}:{}/write?db={}'
    url = url_string.format(config_influxdb['host'], config_influxdb['port'], config_influxdb['db'])
    start_millis = int(epoch) * 1000
    measurement = "inverter_total_power"
    istring = measurement+',period="{}"'.format("1d")+" "
    istring += 'watt={}'.format(total_power)
    if yesterday_total_power:
        istring += ' today={}'.format(total_power-yesterday_total_power)
    millis = start_millis
    istring += ' ' + str(millis) + '{0:06d}'.format(0)
    try:
        r = requests.post(url, data=istring, timeout=5)
    except Exception as e:
        print("influxdb post exception", str(e))    