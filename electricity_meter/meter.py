import re
import time
import copy
import serial

meter_types = {
    'sagemcom_T211' : 'profile1'
}


def get_meter_value(config):
    '''
    Public generic function to retrieve digital meter values from electricity meter
    return a dictionary with for value pairs
    - returnX (injection in watt) where X is equal to 1,2, ...
    - consumeX (consumption in watt) where x is equal to 1,2 ...
    '''
    if config['type'] not in meter_types:
        print("not supported meter type")
        return None
    profile = meter_types[config['type']]
    adict = meter_profiles[profile]['meter_func'](meter_profiles[profile], config['serial_port'])  # call function
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

    adict = {}
    ser.open()
    checksum_found = False
    while not checksum_found:
        telegram_line = ser.readline()  # Read in serial line.
        if re.match(b'(?=!)', telegram_line):
            checksum_found = True
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
    adict['timestamp'] = int(time.time())
    ser.close()
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
