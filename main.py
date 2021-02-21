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
from electricity_meter.meter import get_meter_value, meter_types
from electricity_meter.influxdb import send_frequent_electricity_consumption, send_daily_meter
from inverter.inverter import get_today_yield, send_daily_yield, get_total_power, send_daily_total_power, register_inverter, invertor_types
from solar_forecast.forecast import get_72h_forecast, get_daily_yield
from solar_forecast.influxdb import save_forecast

app = Flask(__name__)
api = Api(app)

time_read_inverter_daily = "22:00"
time_read_inverter_power = "23:02"  # a little bit later than meter reading
time_read_meter_evening = "23:00"
time_read_meter_morning = "07:00"
time_read_forecast = "07:30"

last_balance = 0
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

last_em = None  # meter value refreshed each 5 minutes
last_daily_em = None  # meter values refreshed twice a day
yesterday_em = None
yesterday_total_power = None
stop_the_thread = False

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
        schedule.run_pending()
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
    Get the cached forecast figure (total yield in watt for the desired day) for one of the coming days (days, tomorrow or day after).
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
    global last_em
    global last_balance
    global debug

    time_elapsed = current_measurement['timestamp'] - last_em['timestamp']
    mf = 3600/time_elapsed  # multiplication for watts/h
    last_return = last_em['return1'] + last_em['return2']
    last_consume = last_em['consume1'] + last_em['consume2']
    return_now = current_measurement['return1'] + current_measurement['return2']
    consume_now = current_measurement['consume1'] + current_measurement['consume2']
    
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
    global last_em
    global config_influxdb
    global debug

    v = get_meter_value(config_electricity_meter)
    if debug:
        print("meter values", v, last_em)
    if last_em:
        balance, injection, consumption = calculate_electricity_consumption(v)
        if config_influxdb:
            # send report to influx db
            send_frequent_electricity_consumption(v['timestamp'], balance, config_influxdb, inject=injection, consume=consumption)
        last_em = copy.deepcopy(v)
    else:
        last_em = copy.deepcopy(v)
    return v

def morning_meter_registration():
    global last_em
    global last_daily_em
    global config_influxdb
    global debug

    if debug:
        print("last_em", last_em)
    
    if not last_daily_em:
        last_daily_em = copy.deepcopy(last_em)
        return

    if last_em:
        epoch = last_em['timestamp']
        adict = copy.deepcopy(last_em)
        del adict['timestamp']
        if config_influxdb:
            adict['injection_delta'] = (adict['return1']+adict['return2']) - (last_daily_em['return1']+last_daily_em['return2'])
            adict['consumption_delta'] = (adict['consume1']+adict['consume2']) - (last_daily_em['consume1']+last_daily_em['consume2'])
            send_daily_meter(epoch, adict, config_influxdb, 'morning')

        last_daily_em = copy.deepcopy(last_em)

def evening_meter_registration():
    global last_em
    global last_daily_em
    global yesterday_em
    global config_influxdb
    global debug

    if not last_daily_em:
        last_daily_em = copy.deepcopy(last_em)
        return

    if last_em:
        if debug:
            print("evening_meter_registration", last_em)
        epoch = last_em['timestamp']
        adict = copy.deepcopy(last_em)
        del adict['timestamp']
        if config_influxdb:
            adict['injection_delta'] = (adict['return1']+adict['return2']) - (last_daily_em['return1']+last_daily_em['return2'])
            adict['consumption_delta'] = (adict['consume1']+adict['consume2']) - (last_daily_em['consume1']+last_daily_em['consume2'])
            if yesterday_em:
                pass
            else:
                yesterday_em = copy.deepcopy(last_em)
            send_daily_meter(epoch, adict, config_influxdb, 'evening')

        last_daily_em = copy.deepcopy(last_em)

def read_daily_inverter():
    global inverter_ref
    global debug

    if inverter_ref:
        today_yield = get_today_yield(inverter_ref)
        if debug:
            print("read_daily_inverter", today_yield)
        send_daily_yield(today_yield, config_influxdb)

def read_total_power():
    global inverter_ref
    global debug
    global yesterday_total_power

    if inverter_ref:
        total_power = get_total_power(inverter_ref)
        if debug:
            print("read_total_power", total_power)        
        send_daily_total_power(total_power, yesterday_total_power, config_influxdb)
        yesterday_total_power = total_power
        return total_power
    return 0

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
    parser = argparse.ArgumentParser()
    parser.add_argument("config_yaml", nargs='?', default="test.yml", help='Full path to yaml file (default : test.json)')
    parser.add_argument('-d', '--dryrun', action='store_true', help="run in dryrun mode")
    parser.add_argument('-c', '--capabilities', action='store_true', help="Show capabilities and exit")
    parser.add_argument('-v', '--verbose', action='store_true', help="output more traces to syslog")
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
        print("Influxdb client enabled")
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
                print("dryrun finished, everything looks ok")
                sys.exit(0)
            else:
                schedule.every().day.at(time_read_forecast).do(get_forecast)

        api.add_resource(ElectricityBalance, '/solar-friend/api/v1.0/electricity_balance', endpoint = 'electricity_balance')
        api.add_resource(SolarForecast, '/solar-friend/api/v1.0/day_forecast/<day>', endpoint = 'day_forecast')
        schedule_handler = threading.Thread(target=handle_schedule, args=())
        schedule_handler.start()
        signal.signal(signal.SIGINT, signal_handler)

        app.run(host="0.0.0.0", port=5300)