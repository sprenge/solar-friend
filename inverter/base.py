import os

class InvertorBase():
    '''
    Base class for inverter, implement the function below for each inverter (type)
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
        Returns a list of absolute power values (in watt) together with the epoch time (local time)
        following fields are expected in each dictionary element of the list :
        - watt
        - epoch
        '''
        pass

    def get_total_power(self):
        '''
        Returns the accumulated total yield in watt of the inverter (since installation)
        '''
        pass