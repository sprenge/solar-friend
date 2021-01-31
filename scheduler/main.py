import time
import os
import schedule
import requests

current_power = 0

def send_daily_to_influx_db(data, influx_host, influx_port=8086, solar_db='solar', meas_per_hour=12):
    '''
    Send daily results to influx db
    '''
    prev_watt = data[0]['watt']
    for rec in data:
        if rec['watt'] != prev_watt:
            yield_watt = (rec['watt'] - prev_watt) * meas_per_hour
            epoch = rec['epoch']
            url = url_string.format(influx_host, influx_port, solar_db)
            start_millis = int(epoch) * 1000

            measurement = "invertor_detail_result"
            istring = measurement+',yield_watt={}'.format(yield_watt)+" "
            istring += 'epoch="{}"'.format(epoch)
            millis = start_millis
            istring += ' ' + str(millis) + '{0:06d}'.format(0)
            print("istring", istring)
            print("url", url)
            try:
                r = requests.post(url, data=istring, timeout=5)
            except Exception as e:
                print("influxdb post exception", str(e))

def to_influx_db():
    pass

def get_systems():
    params = {"format": "json"}
    url = "http://{}:8002/rest/system/".format(cia)
    systems_list = []
    try:
        r = requests.get(url, params=params)
        if r.status_code==200:
            systems_list = r.json()
    except Exception as e:
        print(e)
    return systems_list

def get_inverters():
    params = {"format": "json"}
    url = "http://{}:8002/rest/inverter/".format(cia)
    inverter_list = []
    try:
        r = requests.get(url, params=params)
        if r.status_code==200:
            inverter_list = r.json()
    except Exception as e:
        print(e)
    return inverter_list

def get_inverter_types():
    params = {"format": "json"}
    url = "http://{}:8002/rest/inverter_type".format(cia)
    inverter_types = []
    try:
        r = requests.get(url, params=params)
        if r.status_code==200:
            inverter_types = r.json()
    except Exception as e:
        print(e)
    return inverter_types

def daily_data_to_influx():
    systems = get_systems()
    inverter_types = get_inverter_types()
    types_dict = {}
    for inverter_type in inverter_types:
        types_dict[inverter_type['id']] = inverter_type['brand']
    print(types_dict)
    for system in systems:
        inverters = get_inverters()
        for inverter in inverters:
            print(inverter, system)
            if inverter['system'] == system['id']:
                params = {"host": inverter['host'], "password": inverter['password']}
                params['inverter_brand'] = types_dict[inverter['inverter_type']]
                try:
                    r = requests.get("http://{}:5200/inverter/api/v1.0/get_today_yield".format(cia), params=params)
                    if r.status_code == 200:
                        send_daily_to_influx_db(r.json(), system['influxdb_host'])
                except:
                    pass

def get_current_power():
    print("get_current_power")


# schedule.every().day.at("22:00").do(daily_data_to_influx)
schedule.every(2).minutes.do(daily_data_to_influx)
schedule.every(5).minutes.do(get_current_power)

try:
    cia = os.environ['CONCIERGE_IP_ADDRESS']
except:
    cia = '192.168.1.59'

print("cia", cia)
while True:
    schedule.run_pending()
    time.sleep(1)

