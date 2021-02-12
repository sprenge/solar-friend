# solar-friend : introduction

Solar-friend helps you to measure and optimize your electricity consumption inside your home.  the following function are implemented in this package.

- Electricity meter reading : read frequently consumption/injection
- Solar invertor data read out
- Solar forecast yield for the coming 3 days

Solar-friend does not reinvent the wheel for functions that can be full-filled :

- It is ready to integrate with home assistant (https://www.home-assistant.io/), the number one open source package for automating your home.
- Meter data (from electricity meter and inverter) are stored in an influxdb database.  How to install influxdb is described below.
- Data visualization can be done via grafana.  How to install grafana is described below together with graphical templates for data visualization.

# Installation

## Install packages

The installation is described for installation on a raspberry Pi (Raspberry Pi OS).  This does not mean that installation cannot be done on other platform but it might require a couple of small changes.  You can find a lot of guides on youtube how you install an operation on your raspberry Pi (for instance https://www.youtube.com/watch?v=y45hsd2AOpw).  You can also install this package on the Raspberry Pi that already contains home assistant (for instance https://www.youtube.com/watch?v=xNK3IDxSPHo).  The IP address 192.168.1.30 is the IP address of my Raspberry at home.  Please change that address to the IP address of your Raspberry Pi.  In the text below I assume that home assistant, solar-friend, influxdb and grafana are installed on one Raspberry Pi which does not have to be case.  You can perfectly split all these functions over different physical hardware platform (e.g. multiple Raspberry Pi's)

The next step is to open a terminal to your Raspberry Pi (e.g. using mobaxterm) and become root (sudo -i) 

## ![image-20210208084817569](./image-20210208084817569.png)



Perform the following installation steps (**adapt the timezone to your situation**) :

```bash
apt-get update
apt-get -y upgrade
apt-get install -y python3-pip
apt-get install -y git
apt-get install -y libatlas-base-dev
apt-get install -y libopenjp2-7-dev
apt install libtiff5
timedatectl set-timezone Europe/Brussels
cd
git clone https://github.com/sprenge/solar-friend.git
cd solar-friend
pip3 install -r install/requirements.txt
```
## Create your configuration file

Discover first the types that the current solar-friend version supports :

```bash
python3 main.py --capabilities
```
This list possible values for electricity meter types and inverter types (to be used to fill in the config file correctly

Now it is time to create a config file (e.g. /root/config.yml) which contains details about the devices in your home.  Copy first the example config file so you have a template to start from :

`cp /root/solar-friend/example_input.yml /root/config.yml`

Edit now the /root/config.yml file.  Customize the values to your environment and remove the sections you don't want to activate.  If you are not familiar with yaml editing, you can make use of one the online tools (e.g. https://onlineyamltools.com/edit-yaml).  Below is list which section (in bold) you need for which functionality :

- Metering value into the database : **influxdb** --> *db* and *host* are mandatory if you have an influxdb section.
- Electricity meter : **electricity_meter**--> *type* and *serial_port* are mandatory.
- solar system forecasting : **solar_system** --> please foresee *location*, *panels* and *forecast* sub sections:
  - location --> longitude and latitude of your home
- invertor : **solar_system** --> please foresee the *inverter* sub section --> *provider* and *api_key* are mandatory in case you foresee the inverter sub section.  Only one provider is supported for the moment namely solcast (https://solcast.com/).  Retrieving the api_key is free of charge in some conditions (not for commercial usage) --> see API toolkit / free registration.

## Installation of influxdb

The installation of  influxdb (in case you have raspbian buster)

```bash
wget -qO- https://repos.influxdata.com/influxdb.key | sudo apt-key add -
echo "deb https://repos.influxdata.com/debian buster stable" | sudo tee  /etc/apt/sources.list.d/influxdb.list
apt install influxdb
systemctl unmask influxdb
systemctl enable 
systemctl start influxdb
influx
> create database solar
```
tbc : install retention policy for the database



## Installation of grafana 

```bash
echo "deb https://packages.grafana.com/oss/deb stable main" | sudo tee -a /etc/apt/sources.list.d/grafana.list
apt-get install -y grafana
systemctl enable grafana-server
systemctl start grafana-server
```



## Dry run your installation

Test your installation/configuration on errors

```bash
# make sure you are still in the solar-friend directory
python3 main.py --dryrun /root/config.yml
```

Verify that database record have been created in the solar database :

```bash
influx -precision rfc3339
> use solar
> show measurements
> select * from daily_meter
> select * from inverter_total_power
```

Please note that the time is in UTC, not your local time (that is okay)

## Create service

```bash
cp install/start_solar.sh /root
chmod +x /root/start_solar.sh
cp install/meter.service /lib/systemd/system
systemctl enable meter.service
systemctl start meter.service
tail -f /var/log/syslog
```

Check in syslog that you see the following message :  Running on http://0.0.0.0:5300/, if so it means that the service is correctly started and running

## Link to home assistant

Make sure you know the IP address of the host where the solar-friend service is running and make sure that home assistant can reach that IP address.  Please replace the IP address mentioned below (192.168.1.30) with the IP address of your own service.

Edit now the home assistant yaml file and add following config :

```yaml
sensor:
  - platform: rest
    name: last_netto_consumption
    resource: http://192.168.1.30:5300/solar-friend/api/v1.0/last_netto_consumption
    value_template: '{{ value_json.watt }}'
    unit_of_measurement: W
  - platform: rest
    name: solar_forecast_day_after
    resource: http://192.168.1.30:5300/solar-friend/api/v1.0/day_forecast/day_after
    value_template: '{{ value_json.watt }}'
    unit_of_measurement: W
  - platform: rest
    name: solar_forecast_tomorrow
    resource: http://192.168.1.30:5300/solar-friend/api/v1.0/day_forecast/tomorrow
    value_template: '{{ value_json.watt }}'
    unit_of_measurement: W
  - platform: rest
    name: solar_forecast_today
    resource: http://192.168.1.30:5300/solar-friend/api/v1.0/day_forecast/today
    value_template: '{{ value_json.watt }}'
    unit_of_measurement: W

camera:
  - platform: generic
    name: "yield_today"
    still_image_url: "http://192.168.1.30:5300/solar-friend/api/v1.0/today_yield.png"
```

Restart your home assistant and you will discover new sensors which you can integrate now in your lovelace panels the way you want.
