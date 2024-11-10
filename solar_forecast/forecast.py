import json
import time
import datetime
import requests


def get_daily_yield(yield_list):
    daily_yield = 0.0
    prev_time = None
    prev_pv = None
    for rec in yield_list:
        if not prev_time:
            prev_time = rec['time']
            prev_pv = rec['pv']
            continue
        time_elapsed = rec['time']-prev_time
        mf = time_elapsed/3600
        daily_yield += ((rec['pv']+prev_pv)/2)*mf
        prev_pv =  rec['pv']
        prev_time = rec['time']
    
    return int(daily_yield*1000)

def get_72h_forecast(config_panels, config_forecast, config_location):
    '''
    Only one provider supported for the monent : solcast
    '''
    processed_forecast_list = []
    api_key = config_forecast['api_key']
    base_url = "https://api.solcast.com.au/"
    params = {}
    params['api_key'] = api_key
    params['format'] = 'json'
    params['longitude'] = config_location['longitude']
    params['latitude'] = config_location['latitude']
    params['hours'] = 72
    yield_today = []
    yield_tomorrow = []
    yield_day_after = []

    url = base_url + 'world_pv_power/forecasts'
    time_dict = {}
    for panel in config_panels:
        params['capacity'] = panel['pv']*panel['number_of_panels']/1000
        params['azimuth'] = panel['azimuth']
        params['tilt'] = panel['tilt']
        try:
            r = requests.get(url, auth=(api_key, ''), params=params)
        except Exception as e:
            print(e)
            continue

        if r.status_code == 200:
            data = r.json()
            prev_time = None
            cnt = 0
            for rec in data['forecasts']:
                dt_obj = datetime.datetime.strptime(rec['period_end'], '%Y-%m-%dT%H:%M:%S.0000000Z')
                epoch = int(dt_obj.timestamp())-time.timezone
                if not prev_time:
                    prev_time = epoch
                    continue
                prev_time = epoch
                if rec['pv_estimate'] > 0.0:

                    if epoch not in time_dict:
                        adict = {'pv': rec['pv_estimate'], 'dt_obj':dt_obj}
                        time_dict[epoch] = adict
                    else:
                        time_dict[epoch]['pv'] += rec['pv_estimate']
                cnt += 1

            yield_today = []
            yield_tomorrow = []
            yield_day_after = []
            for akey in sorted(time_dict):
                pe = time_dict[akey]
                t_now = datetime.datetime.now()
                adict = {'time': akey, 'pv': pe['pv']}
                if t_now.day == pe['dt_obj'].day:
                    yield_today.append(adict)
                if t_now.day+1 == pe['dt_obj'].day:
                    yield_tomorrow.append(adict)
                if t_now.day+2 == pe['dt_obj'].day:
                    yield_day_after.append(adict)    
        else:
            print("error code going to solcast", r.status_code)                

    return yield_today, yield_tomorrow, yield_day_after
