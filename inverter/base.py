import os

class InvertorBase():
    '''
    Base class for inverter, implement the functions get_today_yield and get_total_power below for each inverter (type)
    '''
    def __init__(self, config):
        if 'host' in config:
            self.host = config['host']
        if 'user' in config:
            self.user = config['user']
        if 'password' in config:
            self.password = config['password']

    def get_today_yield(self):
        '''
        Returns a list of absolute power values (in watt) together with the epoch time (local time).
        The following fields (integer type) are expected as a list of each dictionary elements :
        - watt
        - epoch
        example return [{"watt": -100, "epoch": 1613461079}, {"watt": 150, "epoch": 1613461279}]
        '''
        pass

    def get_total_power(self):
        '''
        Returns the accumulated total yield in watt (integer type) of the inverter (yield since installation)
        '''
        pass