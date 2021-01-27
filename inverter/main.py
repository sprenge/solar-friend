import os
from flask import Flask, jsonify
from flask_restful import Resource, Api, reqparse
from sunny_boy import SunnyBoyInverter

app = Flask(__name__)
api = Api(app)

class GetCurrentPower(Resource):
    '''
    tbc
    '''
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('password', type = str, required = True)
        self.reqparse.add_argument('host', type = str, required = True)
        self.reqparse.add_argument('inverter_brand', type = str, required = True)
        super(GetCurrentPower, self).__init__()

    def get(self):
        '''
        '''
        args = self.reqparse.parse_args()
        if args['inverter_brand'] == "SunnyBoy":
            sma = SunnyBoyInverter(args['host'], password=args['password'])
            sma.login()
            if sma.sid:
                current_power = sma.get_current_power()
                sma.logout()
                adict = {"current_power": current_power}
                return adict, 200

api.add_resource(GetCurrentPower, '/inverter/api/v1.0/get_current_power', endpoint = 'get_current_power')

app.run(host="0.0.0.0", port=5200)