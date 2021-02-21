import yaml

valid_first_level_keywords = ['electricity_meter', 'influxdb', 'solar_system']
def parse(afile, debug=False):

    config = None
    with open(afile, 'r') as stream:
        try:
            config = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
    
    if debug:
        print("config from file", config)
    if config:
        for akey in config:
            if akey not in valid_first_level_keywords:
                print('invalid keyword at first level')
                return None
        if 'influxdb' in config:
            subconfig = config['influxdb']
            if 'host' not in subconfig:
                print('host is a mandatory parameter in influxdb')
                return None
            if 'db' not in subconfig:
                print('db is a mandatory parameter in influxdb')
                return None
            if 'port' not in subconfig:
                config['influxdb']['port'] = 8086
        if 'electricity_meter' in config:
            subconfig = config['electricity_meter']
            if 'type' not in subconfig:
                print('type is a mandatory parameter in electricity_meter')
                return None
            if 'serial_port' not in subconfig:
                print('serial_port is a mandatory parameter in electricity_meter')
                return None

        if 'solar_system' in config:
            subconfig = config['solar_system']
            if 'inverter' in subconfig:
                subsubconfig = subconfig['inverter']
                if 'type' not in subsubconfig:
                    print('type is a mandatory parameter in inverter')
                    return None
                if 'host' not in subsubconfig:
                    print('type is a mandatory parameter in inverter')
                    return None
                if 'password' not in subsubconfig:
                    print('password is a mandatory parameter in inverter')
                    return None                                        
            if 'panels' in subconfig:
                subsubconfig = subconfig['panels']
                rec_fields = ['name', 'number_of_panels', 'azimuth', 'tilt', 'pv']
                try:
                    for rec in subsubconfig:
                        for required_field in rec_fields:
                            if required_field not in rec:
                                print('{} is a mandatory parameter in a panel entry'.format(required_field))
                                return None
                except Exception as e:
                    print(e)         
                    return None 
            if 'forecast' in subconfig:
                subsubconfig = subconfig['forecast']
                if 'provider' not in subsubconfig:
                    print('provider is a mandatory parameter in forecast')       
                    return None        
                if 'api_key' not in subsubconfig:
                    print('api_key is a mandatory parameter in forecast')       
                    return None     
            if 'location' in subconfig:
                subsubconfig = subconfig['location']
                if 'longitude' not in subsubconfig:
                    print('longitude is a mandatory parameter in location')
                    return None         
                if 'latitude' not in subsubconfig:
                    print('latitude is a mandatory parameter in location')
                    return None                                
    return config

if __name__ == "__main__":
    config = parse('example_input.yml')
    print(config)