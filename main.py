import os
import io
import sys
import time
import datetime
import copy
import threading
import signal
import argparse
import schedule
from flask import Flask, jsonify
from flask_restful import Resource, Api, reqparse
from flask import send_file
import matplotlib.pyplot as plt
import numpy as np
from parse_input import parse
from electricity_meter.meter import get_meter_value
from electricity_meter.influxdb import send_frequent_electricity_consumption, send_daily_meter
from inverter.inverter import get_today_yield, send_daily_yield, get_total_power, send_daily_total_power
from solar_forecast.forecast import get_72h_forecast, get_daily_yield

app = Flask(__name__)
api = Api(app)

last_netto_consumption = 0
forecast_raw = None
config_electricity_meter = None
config_influxdb = None
config_inverter = None
config_forecast = None
config_panels = None
config_location = None
yield_today = None
yield_tomorrow = None 
yield_day_after = None
watt_today = 0
watt_day_after = 0
watt_tomorrow = 0

last_em = None
stop_the_thread = False

def signal_handler(sig, frame):
    global stop_the_thread
    stop_the_thread = True
    sys.exit(0)

def handle_schedule():
    while not stop_the_thread:
        schedule.run_pending()
        time.sleep(1)
    signal.pause()

@app.route('/solar-friend/api/v1.0/today_yield.png')
def today_yield():
    dt = []
    if yield_today is None:
        return ''
    if len(yield_today) == 0:
        return ''
    print('yield_today', yield_today)
    for rec in yield_today:
        value = datetime.datetime.fromtimestamp(rec['time'])
        tt = value.strftime('%H:%M')
        print(tt)
        dt.append(tt)

    x_axis = np.array([rec for rec in dt])
    vals = np.array([1000*rec['pv'] for rec in yield_today])

    plt.clf()
    plt.plot(x_axis, vals)
    plt.xticks(rotation=45)
    frame_io = io.BytesIO()
    plt.savefig(frame_io, dpi=100)
    frame_io.seek(0)
    return send_file(frame_io, mimetype='image/png')


class SolarForecast(Resource):
    '''
    REST API class getting 
    '''
    def __init__(self):
        super(SolarForecast, self).__init__()

    def get(self, day):
        '''
        Receive request to find shapes in an image file or video file
        Supports two file formats (file suffixes) : jpg and mp4
        '''
        global watt_day_after
        global watt_tomorrow
        global watt_today

        watts = 0
        if day == 'tomorrow':
            watts = watt_tomorrow
        if day == 'day_after':
            watts = watt_day_after       
        if day == 'today':
            watts = watt_today          

        adict = {"watt": watts}
        return adict, 200

class LastNettoConsumption(Resource):
    '''
    REST API class getting 
    '''
    def __init__(self):
        super(LastNettoConsumption, self).__init__()

    def get(self):
        '''
        Receive request to find shapes in an image file or video file
        Supports two file formats (file suffixes) : jpg and mp4
        '''
        global last_netto_consumption
        adict = {"watt": last_netto_consumption}
        return adict, 200

def calculate_electricity_consumption(current_measurement):
    global last_em
    global last_netto_consumption

    time_elapsed = current_measurement['timestamp'] - last_em['timestamp']
    mf = 3600/time_elapsed  # multiplication for watts/h
    last_return = last_em['return1'] + last_em['return2']
    last_consume = last_em['consume1'] + last_em['consume2']
    return_now = current_measurement['return1'] + current_measurement['return2']
    consume_now = current_measurement['consume1'] + current_measurement['consume2']
    
    netto_consumption = ((return_now-last_return)-(consume_now-last_consume))*mf
    last_netto_consumption = int(netto_consumption)
    # print("Netto consumption/injection in last {} seconds : {}".format(time_elapsed, netto_consumption))
    injection = (return_now-last_return)*mf
    consumption = (consume_now-last_consume)*mf
    # print(injection, consumption)
    
    return int(netto_consumption), int(injection), int(consumption)

def periodic_get_meter_value():
    global last_em
    global config_influxdb

    v = get_meter_value(config_electricity_meter)
    if last_em:
        netto_consumption, injection, consumption = calculate_electricity_consumption(v)
        if config_influxdb:
            # send report to influx db
            send_frequent_electricity_consumption(v['timestamp'], netto_consumption, config_influxdb['host'], inject=injection, consume=consumption, solar_db=config_influxdb['db'])
        last_em = copy.deepcopy(v)
    else:
        last_em = copy.deepcopy(v)

def morning_meter_registration():
    global last_em
    global config_influxdb

    if last_em:
        epoch = last_em['timestamp']
        adict = copy.deepcopy(last_em)
        del adict['timestamp']
        if config_influxdb:
            send_daily_meter(epoch, adict, config_influxdb['host'], 'morning')

def evening_meter_registration():
    global last_em
    global config_influxdb

    if last_em:
        epoch = last_em['timestamp']
        adict = copy.deepcopy(last_em)
        del adict['timestamp']
        if config_influxdb:
            send_daily_meter(epoch, adict, config_influxdb['host'], 'evening')

def read_daily_inverter():
    global config_inverter

    if config_inverter:
        today_yield = get_today_yield(config_inverter)
        send_daily_yield(today_yield, config_influxdb['host'], config_influxdb['db'])

def read_total_power():
    global config_inverter
    if config_inverter:
        total_power = get_total_power(config_inverter)
        send_daily_total_power(total_power, config_influxdb['host'], config_influxdb['db'])
        print("total_power", total_power)

def get_forecast():
    global config_panels
    global config_forecast
    global config_location
    global yield_today
    global yield_tomorrow
    global yield_day_after
    global watt_tomorrow
    global watt_day_after
    global watt_today

    yield_today, yield_tomorrow, yield_day_after = get_72h_forecast(config_panels, config_forecast, config_location)
    watt_today = get_daily_yield(yield_today)
    watt_tomorrow = get_daily_yield(yield_tomorrow)
    watt_day_after = get_daily_yield(yield_day_after)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("config_yaml", nargs='?', default="test.yml", help='Full path to yaml file (default : test.json)')
    parser.add_argument('-d', '--dryrun', action='store_true', help="run in dryrun mode")
    args = parser.parse_args()

    if args.dryrun:
        print("Executing dry run")
    config = parse(args.config_yaml)
    if not config:
        print("error in config yaml file")
        sys.exit(1)
    if 'influxdb' in config:
        config_influxdb = config['influxdb']
        print("Influxdb client enabled")
    if 'electricity_meter' in config:
        print("Started the measurement of the electricity meter every 5 minutes")
        config_electricity_meter = config['electricity_meter']
        if args.dryrun:
            periodic_get_meter_value()
            morning_meter_registration()
            evening_meter_registration()
        else:
            schedule.every(300).seconds.do(periodic_get_meter_value)
            schedule.every().day.at("07:00").do(morning_meter_registration)
            schedule.every().day.at("23:00").do(evening_meter_registration)
    if 'solar_system' in config:
        subconfig = config['solar_system']
        if 'inverter' in subconfig:
            print("Started inverter daily readout")
            config_inverter = subconfig['inverter']
            if args.dryrun:
                # read_daily_inverter()
                read_total_power()
            else:
                schedule.every().day.at("22:00").do(read_daily_inverter)
                schedule.every().day.at("23:00").do(read_total_power)
        if 'panels' in subconfig:
            if 'forecast' not in subconfig:
                print("error : forecast must be provided in case panels is defined")
                sys.exit(1)
            if 'location' not in subconfig:
                print("error : location must be provided in case panels is defined")
                sys.exit(1)
            print("Started solar forecast")
            config_panels = subconfig['panels']
            config_forecast = subconfig['forecast']
            config_location = subconfig['location']
            if args.dryrun:
                get_forecast()
                print("dryrun finished, exit now")
                sys.exit(0)
            else:
                schedule.every().day.at("08:05").do(get_forecast)

        api.add_resource(LastNettoConsumption, '/solar-friend/api/v1.0/last_netto_consumption', endpoint = 'last_netto_consumption')
        api.add_resource(SolarForecast, '/solar-friend/api/v1.0/day_forecast/<day>', endpoint = 'day_forecast')
        schedule_handler = threading.Thread(target=handle_schedule, args=())
        schedule_handler.start()
        signal.signal(signal.SIGINT, signal_handler)

        app.run(host="0.0.0.0", port=5300)