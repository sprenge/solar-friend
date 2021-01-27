import os

class InvertorBase():
    '''
    Base class for inverter
    '''
    def __init__(self, host, user='', password=''):
        self.host = host
        self.user = user
        self.password = password

    def get_today_yield(self):
        '''
        Returns a list of absolute power values (in watt) together with the epoch time (local time)
        '''
        pass

    def get_current_power(self):
        '''
        Returns the current output power in watt of the inverter
        '''
        pass