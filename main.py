import os
import traceback
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
import influxdb
import requests
from parse_input import parse
from electricity_meter.meter import get_meter_value, meter_types
from electricity_meter.influxdb import send_frequent_electricity_consumption, send_daily_meter
from inverter.inverter import get_today_yield, send_daily_yield, get_total_power, send_daily_total_power, register_inverter, invertor_types
from solar_forecast.forecast import get_72h_forecast, get_daily_yield
from solar_forecast.influxdb import save_forecast

app = Flask(__name__)
api = Api(app)

VERSION = "0.1"
time_read_inverter_daily = "22:00"
time_read_inverter_power = "23:02"
time_self_consumption = "23:15" # a little bit later than meter reading / inverter reading
time_read_meter_evening = "23:00"
time_read_meter_morning = "07:00"
time_read_forecast = "07:30"

last_balance = 0
last_w1 = 0
last_w2 = 0
last_wtotal = 0
i1 = 0.0
i2 = 0.0
i3 = 0.0
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
inverter_ref = None
debug = False

last_meter_value = None # meter value refreshed every 5 minutes
stop_the_thread = False
self_yesterday = 0
cons_yesterday = 0

def signal_handler(sig, frame):
    '''
    Handle request to stop the program gracefully
    '''
    global stop_the_thread

    stop_the_thread = True
    sys.exit(0)

def handle_schedule():
    '''
    Main thread for all scheduled functions
    '''
    while not stop_the_thread:
        try:
            schedule.run_pending()
        except Exception as e:
            print("solar thread exception detected", e)
            print(traceback.format_exc())
        time.sleep(1)
    signal.pause()

@app.route('/solar-friend/api/v1.0/today_yield.png')
def today_yield():
    '''
    Build the graph for the expected solar yield for today, returns a png image
    '''
    global debug

    dt = []
    if yield_today is None:
        return ''
    if len(yield_today) == 0:
        return ''
    if debug:
        print('yield_today', yield_today)
    for rec in yield_today:
        value = datetime.datetime.fromtimestamp(rec['time'])
        tt = value.strftime('%H:%M')
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
    Get the cached forecast figures (total yield in watt for the desired day) for one of the coming days (days, tomorrow or day after).
    '''
    def __init__(self):
        super(SolarForecast, self).__init__()

    def get(self, day):
        global watt_day_after
        global watt_tomorrow
        global watt_today
        global debug

        watts = 0
        if day == 'tomorrow':
            watts = watt_tomorrow
        if day == 'day_after':
            watts = watt_day_after       
        if day == 'today':
            watts = watt_today          

        adict = {"watt": watts}
        if debug:
            print("SolarForecast", adict)
        return adict, 200

def calculate_balance_from_current():
    pass

class BalanceYesterday(Resource):
    '''
    Calcuate the balance figures of yesterday.
    '''
    def __init__(self):
        super(BalanceYesterday, self).__init__()

    def get(self):
        '''
        '''
        global self_yesterday
        global cons_yesterday

        adict = {"self_yesterday": self_yesterday, "cons_yesterday": cons_yesterday}
        if debug:
            print("Yesterday", adict)        
        return adict, 200


class GetMeterValues(Resource):
    '''
    Absolute injection meter value in kWh
    '''
    def __init__(self):
        super(GetMeterValues, self).__init__()

    def get(self):
        '''
        '''
        global last_w1
        global last_w2
        global last_wtotal
        v = get_meter_value(config_electricity_meter)

        adict = {}
        try:
            if v['w1'] > 0:
                last_w1 = v['w1']
                last_wtotal = 0 - last_w1
            if v['w2'] > 0:
                last_w2 = v['w2'] 
                last_total = last_w2   
            adict = {
                "injection": str(v['injection']/1000), 
                "consumption": str(v['consumption']/1000),
                "i1": v["i1"], "i2": v["i2"], "i3": v["i3"],
                "w1": last_w1,
                "w2": last_w2,
                "wtotal": last_wtotal,
            }
        except:
            print(v)
        if debug:
            print("Yesterday", adict)        
        return adict, 200


class ElectricityBalance(Resource):
    '''
    Get the cached balance figure (in watt) 
    '''
    def __init__(self):
        super(ElectricityBalance, self).__init__()

    def get(self):
        '''
        Receive request to find shapes in an image file or video file
        Supports two file formats (file suffixes) : jpg and mp4
        '''
        global last_balance
        global debug

        adict = {"watt": last_balance}
        if debug:
            print("ElectricityBalance", adict)        
        return adict, 200

def calculate_electricity_consumption(current_measurement):
    '''
    Calculate current electricity balance, injection and consumption
    '''
    global last_balance
    global last_meter_value
    global debug

    time_elapsed = current_measurement['timestamp'] - last_meter_value['timestamp']
    mf = 3600/time_elapsed  # multiplication for watts/h
    last_return = last_meter_value['injection']
    last_consume = last_meter_value['consumption']
    return_now = current_measurement['injection']
    consume_now = current_measurement['consumption']
    
    balance = ((return_now-last_return)-(consume_now-last_consume))*mf
    last_balance = int(balance)
    if debug:
        print("Balance in last {} seconds : {}".format(time_elapsed, balance))
    injection = (return_now-last_return)*mf
    consumption = (consume_now-last_consume)*mf
    if debug:
        print("injection, consumption", injection, consumption)
    
    return int(balance), int(injection), int(consumption)

def periodic_get_meter_value():
    '''
    Get new meter values (typically trigger every 5 minutes) and return them as a dictionary
    '''
    global last_meter_value
    global config_influxdb
    global debug

    v = 1
    try:
        v = get_meter_value(config_electricity_meter)
    except Exception as e:
        print("periodic failed !!!")
        print(e)
        return v
    if debug:
        print("meter values", v, last_meter_value)
    if last_meter_value:
        try:
            balance, injection, consumption = calculate_electricity_consumption(v)
        except Exception as e:
            print(f"calculate_electricity_consumption exception : {e}")
            return v
        if config_influxdb:
            # send report to influx db
            send_frequent_electricity_consumption(v['timestamp'], balance, config_influxdb, inject=injection, consume=consumption)
        last_meter_value = copy.deepcopy(v)
    else:
        last_meter_value = copy.deepcopy(v)
    return v

import influxdb

def diff_twice_a_day(current_meter, morning_or_evening):
    '''
    Calculate the half consumption/injection and return the values in watt
    '''
    global config_influxdb

    try:
        client = influxdb.InfluxDBClient(host=config_influxdb['host'], port=config_influxdb['port'])
        client.switch_database(config_influxdb['db'])
        query = "select * FROM daily_meter WHERE time > now() - 18h and \"period\"='\"{}\"'".format(morning_or_evening)
        results = client.query(query)
        total_meter_rows = results.raw['series'][0]['values']
        idx = 0
        col2idx_meter = {}
        for col in results.raw['series'][0]['columns']:
            col2idx_meter[col] = idx
            idx += 1

        if len(total_meter_rows) == 1:
            cons1 = int(total_meter_rows[0][col2idx_meter['consumption']])
            inj1 = int(total_meter_rows[0][col2idx_meter['injection']])
            day_cons = current_meter['consumption']-cons1
            day_inj = current_meter['injection'] - inj1

            return day_cons, day_inj

    except Exception as e:
        print("diff_twice_a_day exception", e)

    return None, None


def morning_meter_registration():
    '''
    Register the morning values (cached values) and log them into the influx database
    '''
    global last_meter_value
    global config_influxdb
    global debug

    if last_meter_value:
        if debug:
            print("morning_meter_registration", last_meter_value)        
        epoch = last_meter_value['timestamp']
        adict = copy.deepcopy(last_meter_value)
        del adict['timestamp']
        if config_influxdb:
            consumption_delta, injection_delta = diff_twice_a_day(last_meter_value, "evening")
            if consumption_delta:
                adict['consumption_delta'] = consumption_delta
                adict['injection_delta'] = injection_delta
            send_daily_meter(epoch, adict, config_influxdb, 'morning')


def evening_meter_registration():
    '''
    Register the evening values (cached values) and log them into the influx database
    '''
    global last_meter_value
    global config_influxdb
    global debug

    if last_meter_value:
        if debug:
            print("evening_meter_registration", last_meter_value)
        epoch = last_meter_value['timestamp']
        adict = copy.deepcopy(last_meter_value)
        del adict['timestamp']
        if config_influxdb:
            consumption_delta, injection_delta = diff_twice_a_day(last_meter_value, "morning")
            if consumption_delta:
                adict['consumption_delta'] = consumption_delta
                adict['injection_delta'] = injection_delta
            send_daily_meter(epoch, adict, config_influxdb, 'evening')


def read_daily_inverter():
    '''
    Read the todays values of the inverter (typically 5 minute values) at the end of the day (after sunset) and write into influx database
    '''
    global inverter_ref
    global debug

    if inverter_ref:
        today_yield = get_today_yield(inverter_ref)
        if debug:
            print("read_daily_inverter", today_yield)
        send_daily_yield(today_yield, config_influxdb)

def read_total_power():
    '''
    Read the absolute total power (in watt since the installation of the inverter) after sunset and write into influx database
    '''
    global inverter_ref
    global debug

    if inverter_ref:
        total_power = get_total_power(inverter_ref)
        if debug:
            print("read_total_power", total_power)        
        send_daily_total_power(total_power, config_influxdb)
        return total_power
    return 0

def calc_daily_self_consumption():
    '''
    Calculate the todays self consumption, along with injection and consumption figures and write into influx database
    '''
    global config_influxdb
    global self_yesterday
    global cons_yesterday

    solar_yield = None
    day_cons = None
    day_inj = None

    try:
        client = influxdb.InfluxDBClient(host=config_influxdb['host'], port=config_influxdb['port'])
        client.switch_database(config_influxdb['db'])
        query = "select * FROM inverter_total_power WHERE time > now() - 30h"
        results = client.query(query)
        total_inv_rows = results.raw['series'][0]['values']
        idx = 0
        col2idx_inv = {}
        for col in results.raw['series'][0]['columns']:
            col2idx_inv[col] = idx
            idx += 1

        if len(total_inv_rows) == 2:
            solar_yield = int(total_inv_rows[1][col2idx_inv['watt']] - total_inv_rows[0][col2idx_inv['watt']])

        query = "select * FROM daily_meter WHERE time > now() - 30h and \"period\"='\"evening\"'"
        results = client.query(query)
        total_meter_rows = results.raw['series'][0]['values']
        idx = 0
        col2idx_meter = {}
        for col in results.raw['series'][0]['columns']:
            col2idx_meter[col] = idx
            idx += 1
        if len(total_meter_rows) == 2:
            cons1 = int(total_meter_rows[0][col2idx_meter['consumption']])
            inj1 = int(total_meter_rows[0][col2idx_meter['injection']])
            cons2 = int(total_meter_rows[1][col2idx_meter['consumption']])
            inj2 = int(total_meter_rows[1][col2idx_meter['injection']] )
            day_cons = cons2-cons1
            day_inj = inj2 - inj1
            cons_yesterday = day_cons
    except Exception as e:
        print(e)
    
    if solar_yield and day_cons and day_inj:
        url_string = 'http://{}:{}/write?db={}'
        url = url_string.format(config_influxdb['host'], config_influxdb['port'], config_influxdb['db'])
        start_millis = int(time.time()) * 1000

        measurement = "self_consumption"
        istring = measurement+',period="{}"'.format("1d")+" "
        istring += 'solar_day_yield={},'.format(solar_yield)
        istring += 'day_inj={},'.format(day_inj)
        istring += 'day_cons={},'.format(day_cons)
        self_yesterday = solar_yield-day_inj
        istring += 'day_self={}'.format(self_yesterday)
        millis = start_millis
        istring += ' ' + str(millis) + '{0:06d}'.format(0)
        try:
            r = requests.post(url, data=istring, timeout=5)
        except Exception as e:
            print("influxdb post exception", str(e))

def get_forecast():
    '''
    Get the solar forecast for the next three days, write into the influx database and return these values
    '''
    global config_panels
    global config_forecast
    global config_location
    global yield_today
    global yield_tomorrow
    global yield_day_after
    global watt_tomorrow
    global watt_day_after
    global watt_today
    global config_influxdb
    global debug

    yield_today, yield_tomorrow, yield_day_after = get_72h_forecast(config_panels, config_forecast, config_location)
    if debug:
        print("get_forecast", yield_today, yield_tomorrow, yield_day_after)    
    watt_today = get_daily_yield(yield_today)
    watt_tomorrow = get_daily_yield(yield_tomorrow)
    watt_day_after = get_daily_yield(yield_day_after)
    adict = {"today": watt_today, "tomorrow":watt_tomorrow, "day_after": watt_day_after}
    if debug:
        print("get_forecast", adict)    
    watt_today = get_daily_yield(yield_today)    
    save_forecast(adict, config_influxdb)

if __name__ == "__main__":
    '''
    Starting point of the solar-friend application
    '''
    print("Starting solar-friend, version ", VERSION)
    parser = argparse.ArgumentParser()
    parser.add_argument("config_yaml", nargs='?', default="test.yml", help='Full path to yaml file (default : test.json)')
    parser.add_argument('-d', '--dryrun', action='store_true', help="run in dryrun mode")
    parser.add_argument('-c', '--capabilities', action='store_true', help="Show capabilities and exit")
    parser.add_argument('-v', '--verbose', action='store_true', help="output more traces to syslog")
    parser.add_argument('-p', '--pretest', action='store_true', help="for debug testing")
    args = parser.parse_args()

    if args.dryrun:
        print("Executing dry run")

    if args.capabilities:
        print("discovering capabilities now ...")
        print("solcast is the only forecast provider supported")
        print("")
        print("electricity meters supported :")
        print("----------------------------")
        for meter in meter_types:
            print("{} ({})".format(meter, meter_types[meter]))
        print("")
        print("inverters supported :")
        print("----------------------------")
        for inverter in invertor_types:
            print(inverter)
        sys.exit(0)
    if args.verbose:
        debug = True

    config = parse(args.config_yaml, debug=debug)
    if not config:
        print("error in config yaml file")
        sys.exit(1)
    if 'influxdb' in config:
        config_influxdb = config['influxdb']
        solar_db = config_influxdb['db']
        print("Influxdb client enabled")
    if args.pretest:
        calc_daily_self_consumption()
        sys.exit(0)
    if 'electricity_meter' in config:
        config_electricity_meter = config['electricity_meter']
        if args.dryrun:
            print("Start dryrun electricity meter")
            if not periodic_get_meter_value():
                print("Cannot retrieve meter value")
                sys.exit(1)
            morning_meter_registration()
            evening_meter_registration()
        else:
            print("Started the measurement of the electricity meter every 5 minutes")
            schedule.every(300).seconds.do(periodic_get_meter_value)
            schedule.every().day.at(time_read_meter_morning).do(morning_meter_registration)
            schedule.every().day.at(time_read_meter_evening).do(evening_meter_registration)
    if 'solar_system' in config:
        subconfig = config['solar_system']
        if 'inverter' in subconfig:
            print("Started inverter daily readout")
            config_inverter = subconfig['inverter']
            inverter_ref = register_inverter(config_inverter)
            if args.dryrun:
                # read_daily_inverter()
                tp = read_total_power()
                if tp == 0:
                    print("Cannot read total power of inverter")
                    sys.exit(1)
            else:
                schedule.every().day.at(time_read_inverter_daily).do(read_daily_inverter)
                schedule.every().day.at(time_read_inverter_power).do(read_total_power)
                if 'electricity_meter' in config:
                    schedule.every().day.at(time_self_consumption).do(calc_daily_self_consumption)
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
            get_forecast()
            if args.dryrun:
                print("dryrun finished, everything looks ok")
                sys.exit(0)
            else:
                schedule.every().day.at(time_read_forecast).do(get_forecast)

        api.add_resource(GetMeterValues, '/solar-friend/api/v1.0/meter_values', endpoint = 'meter_values')
        api.add_resource(ElectricityBalance, '/solar-friend/api/v1.0/electricity_balance', endpoint = 'electricity_balance')
        api.add_resource(SolarForecast, '/solar-friend/api/v1.0/day_forecast/<day>', endpoint = 'day_forecast')
        api.add_resource(BalanceYesterday, '/solar-friend/api/v1.0/balance_yesterday', endpoint = 'balance_yesterday')
        schedule_handler = threading.Thread(target=handle_schedule, args=())
        schedule_handler.start()  # run scheduler thread
        signal.signal(signal.SIGINT, signal_handler)  # graceful thread shutdown support

        app.run(host="0.0.0.0", port=5300)  # run webserver
