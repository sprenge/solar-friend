import time
import os
import schedule
import requests

current_power = 0

def to_influx_db():
    pass

def get_systems():
    params = {"format": "json"}
    url = "http://{}:8002/rest/".format(cia)
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
    url = "http://{}:8002/rest/".format(cia)
    inverter_list = []
    try:
        r = requests.get(url, params=params)
        if r.status_code==200:
            inverter_list = r.json()
    except Exception as e:
        print(e)
    return inverter_list

def daily_data_to_influx():
    pass

def get_current_power():
    print("get_current_power")


schedule.every().day.at("22:00").do(daily_data_to_influx)
schedule.every(5).minutes.do(get_current_power)

try:
    cia = os.environ['CONCIERGE_IP_ADDRESS']
except:
    cia = '192.168.1.59'

while True:
    schedule.run_pending()
    time.sleep(1)

