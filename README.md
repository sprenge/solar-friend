# solar-friend : introduction

Solar-friend helps you to measure and optimize your electricity consumption inside your home.  the following functions are implemented in this package.

- Electricity meter reading : read frequently (each 5 minutes) consumption/injection and calculate the actual electricity balance (Do I consume or inject electricity).
- Solar invertor data read out
- Solar forecast yield for the coming 3 days

All measurements are stored into a database in order to perform data analysis lateron.  It could for instance be used lateron to make a correction decision for the selection of a home battery.
This package will be extended lateron with functions to help you with the optimal choice of a home battery.  The price of home batteries does not guarantee currently return on investment but I expect that prices will decrease in the coming years.

Solar-friend does not reinvent the wheel for functions that can be full-filled by other excellent free available software :

- It is ready to integrate with home assistant (https://www.home-assistant.io/), the number one open source package for automating your home.
- Meter data (from electricity meter and inverter) are stored in an influxdb database.  How to install influxdb is described below.
- Data visualization can be done via grafana.  How to install grafana is described below together with some screenshots how to create your custom graphs.

The follow diagram is an example how solar-friend can be deployed (=my home setup in Belgium).  The raspberry pi hosts all software packages and connects to the digital electricity meter (via P1 cable), to the solar inverter and to the internet (forecast).

## ![solar-friend.jpg](./doc/solar-friend.jpg)

# Installation

## Install packages

The installation is described for installation on a raspberry Pi (Raspberry Pi OS).  This does not mean that installation cannot be done on other platforms but it might require a couple of small changes.  You can find a lot of guides on youtube how you install an operating system on your raspberry Pi (for instance https://www.youtube.com/watch?v=y45hsd2AOpw).  You can also install this package on the Raspberry Pi that already contains home assistant (for instance https://www.youtube.com/watch?v=xNK3IDxSPHo).  **The IP address 192.168.1.30 used below in the text is the IP address of my Raspberry at home.  Please replace this address with the IP address of your Raspberry Pi.**  In the text below I assume that home assistant, solar-friend, influxdb and grafana are installed on one Raspberry Pi which does not have to be case.  You can perfectly split all these functions over different physical hardware platform (e.g. multiple Raspberry Pi's)

The next step is to open a terminal to your Raspberry Pi (e.g. using mobaxterm) and become root (sudo -i) 

## ![terminal.png](./doc/terminal.png)



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
This lists possible values for electricity meter types and inverter types (to be used to fill in the config file correctly)

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
apt-get update
apt install influxdb
systemctl unmask influxdb
systemctl enable influxdb
systemctl start influxdb
influx
> create database solar
```
tbc : install retention policy for the database



## Installation of grafana 

```bash
wget -q -O - https://packages.grafana.com/gpg.key | sudo apt-key add -
echo "deb https://packages.grafana.com/oss/deb stable main" | sudo tee -a /etc/apt/sources.list.d/grafana.list
apt-get update
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

The next step is to install solar-friend as a service on your raspberry PI, so that it automatically starts in case of power failure at your home.

```bash
cp install/start_solar.sh /root
chmod +x /root/start_solar.sh
cp install/meter.service /lib/systemd/system
systemctl enable meter.service
systemctl start meter.service
tail -f /var/log/syslog
```

Check in syslog that you see the following message :  Running on http://0.0.0.0:5300/, if so it means that the service is correctly started and running

## API service

Solar-friend offers an API service so that it can easily be integrated with other packages (e.g. home assistant).
The following endpoints are available (replace host by the IP address on which the solar-friend service is started):

* http://192.168.1.30:5300/solar-friend/api/v1.0/today_yield.png : get graph with the solar yield for today
* http://192.168.1.30:5300/solar-friend/api/v1.0/electricity_balance : returns the current consumption (via the key watt), a negative value indicate that more energy was pulled from the electricity net than injected, a positive value means that more energy is injected in the electricity net than consumed.
* http://192.168.1.30:5300/solar-friend/api/v1.0/day_forecast/today : returns the forecast (via the key watt) for today
* http://192.168.1.30:5300/solar-friend/api/v1.0/day_forecast/tomorrow : returns the forecast (via the key watt) for tomorrow
* http://192.168.1.30:5300/solar-friend/api/v1.0/day_forecast/day_afer : returns the forecast (via the key watt) for the day after
* http://192.168.1.30:5300/solar-friend/api/v1.0/meter_values : get back the meter values (injection and consumption)

## Logging to influx database

*Time based measurements are logged into the influx database indicated in the configuration file (see influx installation)*
Every measurement has the *time* field, indicating the exact time of recording.  This measurements are useful for consulting lateron as historical data.

The following measurements are recorded :

### daily_meter

*Electricity meter values are logged every morning and evening into this measurements*

* *consumption* = total power consumption from the electricity net since the commisioning of the electricity meter in watt.
* *injection* = total power insertion into the electricity net since the commissioning of the electricity meter in watt.
* *consumption_delta* = consumption difference in watt with the last measurement (so the consumption of about half a day)
* *injection_delta* = inject difference in watt with the last measurement.
* *period* = evening or morning, the moment the meter values are recorded

Other fields migth be present that are generated by your meter (e.g. day/night counters).

### frequent_consumption_measurement

*The electricity balance (see API service) is logged every 5 minutes along with the consumption and injection values*

* *balance* = a positive value means that you have been selling electricity for the last 5 minutes and a negative value means that you have been buying electricity (inject-consume)
* *consume* = pulled from the electricity net in the last 5 minutes
* *inject* = pushed to the electricity net in the last 5 minutes
* *period* = period between two measurements

### inverter_daily

*Detailed inverter yield values are retrieved every evening from the inverter and stored in this mesurement (in watt).*

These measurements are created at the end of the day

* *watt* = electricity yield in the last 5 minutes
* *period* = interval between two measurements
  
### inverter_total_power

*The total inverter power (in watt) since the commissioning of the inverter is logged every evening into this measurements.*

* *watt* = total power generated by the inverter since the installation of the inverter.
* 
### self_consumption

* *day_cons* = daily consumed from the electricity net 
* *day_inj* = daily injected 
* *day_self* = direct consumption  
* *solar_day_yield* = total solar yield for that day

All values in watt.  This measurement is generated at the end of the day based on existing measurements (only if they are present).

## Link to home assistant as sensor

Make sure you know the IP address of the host where the solar-friend service is running and make sure that home assistant can reach that IP address.  Please replace the IP address mentioned below (192.168.1.30) with the IP address of your own service.

Edit now the home assistant yaml file and add following config :

```yaml
sensor:
  - platform: rest
    name: last_netto_consumption
    resource: http://192.168.1.30:5300/solar-friend/api/v1.0/electricity_balance
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

Screenshot of values integrated in my home assistant 

## ![pic4.jpg](./doc/pic4.jpg)

## link to home assistant via the custom integration component provided in this package

Copy the custom_components directory to the config/custom_components directory (so you install a custom integration) of your installation and restart home assistant.

Add now following config to your configuration.yaml and restart home assistant.  You should see two new sensors now (injection/consumption).

```yaml
sensor:
  - platform: electricity_meter
    scan_interval: 60
    host: 192.168.1.30
```

The integration component talks now to the daemon and two sensor are added (injection/consumption) that can be used in the Energy tab (new in home assistant 2021.8.1).


## Exploring data with grafana

Open up a browser and navigate to the following url : http://192.168.1.30:3000
The first time you can loging with user **admin** and password **admin**

### Connect grafana to influxdb

Add a so called data source and press save and test to verify that grafana can connect to your database.

## ![pic1.jpg](./doc/pic1.jpg)

## ![pic2.jpg](./doc/pic2.jpg)

### Get an overview of your netto consumption

You can do this easily by adding a new dashboard (plus sign on the left side) and adding a new panel in the dashboard.

Once you have the panel follow these steps :
1) Select your data source created in the previous step.
2) Select your measurement.
3) Select the field from the measurement you are interested in (e.g. balance).
4) Aggregate per 5 minutes.
5) Select the time window you are interested in.

The graph represents the moments you inject electricity (you sell energy) which are the points above zero and the moments where you consume electricity (you buy energy) which are the points zero.  The unit of injection/consumption is watt.

## ![pic3.jpg](./doc/pic3.jpg)

## Development guide

It is possible to add support from electricity meters and inverter that are not yet supported.  I would love to add this in advance but I only have one type of electricity meter and one type of inverter at my home so I cannot really test other types.  Feel free to add new types, please contact me (sprengee54@gmail.com) in case you have questions.

### Add electricity meters

Electricity meters can be added by mapping the meter to a profile (see electricity_meter/meter.py --> meter_types).  Extra profiles can be developed if a certain meter cannot be mapped to an existing profile (make sure the same function signature is used a for the existing profiles).  Electricity meters are currently only supported via the serial port.

The profile specific function (see val_profile1 for an example) gets as input the profile data (e.g. baudrate) and the serial port reference.
it must be return a dictionary (or None in case of error) with at least the following fields :
- consumption : integer with the total power consumption in watt since the installation of the meter
- injection : integer with the total power injection in watt since the installation of the meter

Extra fields can be added to the dictionary and these fields will be logged in the influx database (examples are return1, return2, ...).

### Add inverter type

New inverter types can be added by adding entries to the variable invertor_types in inverter/inverter.py
Each inverter type has to be linked to an implemented inverter class which inherits from the class InvertorBase (see inverter/base.py).