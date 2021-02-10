import os
import time
import requests
from inverter.sunny_boy import SunnyBoyInverter

def get_total_power(config):
    
    if config['type'] == "SunnyBoy":
        print("config_inverter", config)
        sma = SunnyBoyInverter(config['host'], password=config['password'])
        sma.login()
        if sma.sid:
            print("sma.sid", sma.sid)
            total_power = sma.get_total_power()
            sma.logout()
            return total_power
    return None

def get_today_yield(config):

    if config['type'] == "SunnyBoy":
        print("config_inverter", config)
        sma = SunnyBoyInverter(config['host'], password=config['password'])
        sma.login()
        if sma.sid:
            print("sma.sid", sma.sid)
            today_yield = sma.get_today_yield()
            sma.logout()
            return today_yield
    return None

def send_daily_yield(today_yield, influx_host, solar_db, influx_port=8086):
    if len(today_yield) == 0:
        return
    prev_5min_watt = int(today_yield[0]['watt'])
    prev_5min_epoch = int(today_yield[0]['epoch'])

    for rec in today_yield:
        yield_5min = int(rec['watt'])- prev_5min_watt
        if yield_5min > 0:
            epoch = int(rec['epoch'])
            time_elapsed = epoch - prev_5min_epoch
            yield_watt = int(3600/time_elapsed*yield_5min)

            url_string = 'http://{}:{}/write?db={}'
            url = url_string.format(influx_host, influx_port, solar_db)
            start_millis = int(epoch) * 1000

            measurement = "inverter_daily"
            istring = measurement+',period="{}"'.format("300s")+" "
            istring += 'watt={}'.format(yield_watt)
            millis = start_millis
            istring += ' ' + str(millis) + '{0:06d}'.format(0)
            print("istring", istring)
            print("url", url)
            try:
                r = requests.post(url, data=istring, timeout=5)
                print(r)
            except Exception as e:
                print("influxdb post exception", str(e))

        prev_5min_watt = int(rec['watt'])
        prev_5min_epoch = int(rec['epoch'])

def send_daily_total_power(total_power, influx_host, solar_db, influx_port=8086):
    epoch = int(time.time())
    url_string = 'http://{}:{}/write?db={}'
    url = url_string.format(influx_host, influx_port, solar_db)
    start_millis = int(epoch) * 1000
    measurement = "inverter_total_power"
    istring = measurement+',period="{}"'.format("1d")+" "
    istring += 'watt={}'.format(total_power)
    millis = start_millis
    istring += ' ' + str(millis) + '{0:06d}'.format(0)
    print("istring", istring)
    print("url", url)
    try:
        r = requests.post(url, data=istring, timeout=5)
        print(r)
    except Exception as e:
        print("influxdb post exception", str(e))    