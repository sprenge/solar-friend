import re
import time
import copy
import serial

meter_types = {
    'sagemcom_T211' : 'profile1'
}

last_val = None

def get_meter_value(config):
    '''
    Public generic function to retrieve digital meter values from electricity meter
    return a dictionary with for key/value pairs
    - consumption : absolute TOTAL consumption in watt (since commissioning meter)
    - injection : absolute TOTAL consumption in watt (since commisioning meter)
    - timestamp : epoch time in seconds
    - (optional) returnX (injection in watt) where X is equal to 1,2, ...
    - (optional) consumeX (consumption in watt) where x is equal to 1,2 ...
    '''
    global last_val

    if config['type'] not in meter_types:
        print("not supported meter type")
        return None
    profile = meter_types[config['type']]
    try:
        adict = meter_profiles[profile]['meter_func'](meter_profiles[profile], config['serial_port'])  # call function
    except Exception as e:
        print("Exception found in get_meter_value", e)
        return None
    if not adict:
        return None
    if last_val:
        if 'consumption' not in adict:
            print('consumption not found in get_meter_value', adict)
            return None
        if 'injection' not in adict:
            print('injection not found in get_meter_value', adict)
            return None            
        if adict['consumption'] < last_val['consumption']:
            print('inconsistency in get_meter_value', adict, last_val)
            last_val = None
            return None
        if adict['injection'] < last_val['injection']:
            print('inconsistency in get_meter_value', adict, last_val)
            last_val = None
            return None            
        last_val = copy.deepcopy(adict)
    else:
        last_val = copy.deepcopy(adict)

    adict['timestamp'] = int(time.time())
    
    return adict

def val_profile1(profile_data, serial_port):
    '''
    Specific implementation for meters mapped to profile1
    return a dictionary as described in the get_meter_value
    '''
    ser = serial.Serial()

    ser.baudrate = profile_data['baudrate']
    ser.bytesize = profile_data['bytesize']
    ser.parity = profile_data['parity']
    ser.stopbits =profile_data['stopbits']
    ser.xonxoff = profile_data['xonxoff']
    ser.rtscts = profile_data['rtscts']
    ser.timeout = 12
    ser.port = serial_port

    fields_expected = ['consume1', 'consume2', 'return1', 'return2']
    i_translate = {"31": "1", "51": "2", "71": "3"}
    adict = {"i1": 128.0, "i2": 128.0, "i3": 128.0, "w1": 0, "w2": 0}
    ser.open()
    exception_fnd = False
    checksum_found = False
    safety_loop_cnt = 0
    while not checksum_found:
        telegram_line = ser.readline()  # Read in serial line.
        if re.match(b'(?=!)', telegram_line):
            for afield in fields_expected:
                if afield not in adict:
                    print("field not found in meter readout", afield)
                    print(telegram_line)
                    exception_fnd = True
            else:
                try:
                    adict['consumption'] = int(adict['consume1']) + int(adict['consume2'])
                    adict['injection'] = int(adict['return1']) + int(adict['return2'])
                    checksum_found = True
                except Exception as e:
                    print("exception found in meter readout during calculation")
                    print(e)
                    exception_fnd = True
        try:
            ser_data = telegram_line.decode('ascii').strip()
            match = re.match('.*1-0:(\d)\.8\.(\d)\((\d+)\.(\d+)\*kWh.*', ser_data)
            if match:
                watt = int(match.group(3))*1000 + int(match.group(4))
                if match.group(1) == '1':
                    akey = 'consume'+match.group(2)
                else:
                    akey = 'return'+match.group(2)
                adict[akey] = watt
        except Exception as e:
            pass
        try:
            ser_data = telegram_line.decode('ascii').strip()
            regex = r'1-0:(\d+)\.(7)\.(\d+)\((\d+(\.\d+)?)\*A\)'
            match = re.match(regex, ser_data)
            if match:
                phase = i_translate[match.group(1)]
                adict[f'i{phase}'] = float(match.group(4))
        except Exception as e:
            print(e)
        try:
            ser_data = telegram_line.decode('ascii').strip()
            regex = r'1-0:(\d+)\.(7)\.(\d+)\((\d+(\.\d+)?)\*kW\)'
            match = re.match(regex, ser_data)
            if match:
                inout = match.group(1)
                if inout == '1' or inout == '2':
                    adict[f'w{inout}'] = int(float(match.group(4))*1000)
        except Exception as e:
            print(f'except2 {e}')            
        safety_loop_cnt += 1
        if safety_loop_cnt > 300:
            print("safety_loop_cnt exceeded")
            checksum_found = True
            exception_fnd = True
            adict = {}
    
    ser.close()
    if exception_fnd:
       return None
    return adict


meter_profiles = {
    'profile1' : {
        'baudrate': 115200,
        'bytesize': serial.EIGHTBITS,
        'parity': serial.PARITY_NONE,
        'stopbits': serial.STOPBITS_ONE,
        'xonxoff': 1,
        'rtscts': 0,
        'meter_func': val_profile1,
    }
}

if __name__ == "__main__":
    config = {'type': 'sagemcom_T211', 'serial_port': '/dev/ttyUSB0'}
    values = get_meter_value(config)
    print(values)
