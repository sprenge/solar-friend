import time
from base import InvertorBase
import requests

class SunnyBoyInverter(InvertorBase):
    def logout(self):
        try:
            r = requests.post("https://{}/dyn/logout.json?sid={}".format(self.host, self.sid), verify=False)
        except:
            print("logout failed")

    def login(self):
        sleep_time = 30
        max_retries = 5
        login_dict = {"right":"usr","pass":self.password}
        nbr_retries = 0
        self.sid = None
        while nbr_retries<max_retries and not self.sid:
            r = requests.post("https://{}/dyn/login.json".format(self.host), json=login_dict, verify=False)
            try:
                if r.status_code != 200:
                    print("login failed {}".format(r.status_code))
            except:
                print("login error")

            try:
                self.sid = r.json()['result']['sid']
            except:
                print("no sid retrieved", r.json())
                self.sid = None
            nbr_retries += 1
            if not self.sid:
                time.sleep(sleep_time)

    def get_today_yield(self):
        params = {}
        params["destDev"] = []
        params["key"] = 28672
        params["tStart"] = 1611529200 # 1611442500
        params["tEnd"] = 1611615600 # 1611528900
        r = requests.post("https://{}/dyn/getLogger.json?sid={}".format(self.host, self.sid), json=params, verify=False)
        # result': {'0199-B31DB208'
        out_list = []
        try:
            alist = r.json()['result']['0199-B31DB208']
            for el in alist:
                adict = {"epoch": el['t'], "watt": el['v']}
                out_list.append(adict)
        except:
            pass
        return out_list

    def get_current_power(self):
        params = {}
        params["destDev"] = []
        # 6100_40263F00
        params["keys"] = ["6100_004F4E00","6800_0883D800","6100_002F7A00","6800_0883D900","6400_00432200","6400_00496700","6400_00496800","6100_00295A00","6180_08495E00","6100_00496900","6100_00496A00","6100_00696E00","6100_40263F00","6800_00832A00","6180_08214800","6180_08414900","6400_00462500","6400_00462400","6100_40463700","6100_40463600","6800_08862500","6182_08434C00","6100_4046F200","6180_08522F00","6800_008AA200","6400_00260100","6100_402F2000","6100_402F1E00","6800_088F2000","6800_088F2100","6800_10852400","6800_00853400","6180_08652600","6800_00852F00","6180_08652400","6180_08653A00","6100_00653100","6100_00653200","6800_08811F00","6400_00462E00"]
        params["keys"] = ["6100_40263F00"]
        r = requests.post("https://{}/dyn/getValues.json?sid={}".format(self.host, self.sid), json=params, verify=False)
        print(r)
        adict = r.json()['result']['0199-B31DB208']
        for rec in adict:
            print(rec, adict[rec])
        try:
            power = adict['6100_40263F00']['1'][0]['val']
        except:
            power = 0
        return power



if __name__ == "__main__":
    sma = SunnyBoyInverter('192.168.1.49', password="xxxxx")
    sma.sid = login(sma)
    if sma.sid:
        ty = sma.get_today_yield()
        current_power = sma.get_current_power()
        print('current_power', current_power)
        logout(sma, sma.sid)
