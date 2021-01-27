import os
from django.db import models

try:
    cia = os.environ['SOLAR_IP_ADDRESS']
except:
    cia = '127.0.0.1'

class System(models.Model):
    name = models.CharField(max_length=255, unique=True)
    forecast_api_key = models.CharField(max_length=255, blank=True, help_text="api key from solar forecast provider")
    forecast_provider = models.CharField(max_length=128, default='solcast', help_text="solar forecast provider")
    latitude = models.FloatField(help_text="location of the system")
    longitude = models.FloatField(help_text="location of the system")
    influxdb_host = models.GenericIPAddressField(blank=True, null=True, help_text="Reporting database host ip address")
    influxdb_database = models.CharField(max_length=64, default='solar', help_text="Reporting database name")
    influxdb_port = models.IntegerField(default=8086, help_text="Reporting database port")

    def __str__(self):
        return self.name

    def __unicode__(self):
        return self.name

class InverterType(models.Model):
    brand = models.CharField(max_length=255, unique=True)
    brand_type = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.brand+"-"+self.brand_type

    def __unicode__(self):
        return self.brand+"-"+self.brand_type

class Inverter(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.CharField(max_length=255, blank=True)
    max_power = models.FloatField(help_text="maximum power in Kw")
    system = models.ForeignKey('System', on_delete=models.CASCADE)
    host = models.GenericIPAddressField(blank=True, null=True)
    user = models.CharField(max_length=255, blank=True)
    password = models.CharField(max_length=255, blank=True)
    inverter_type = models.ForeignKey('InverterType', on_delete=models.CASCADE)

    def __str__(self):
        return self.name

    def __unicode__(self):
        return self.name


class SolarPanelGroup(models.Model):
    name = models.CharField(max_length=255, unique=True)
    power_per_panel = models.FloatField(help_text='power for single panel in kw')
    number_of_panels = models.IntegerField(help_text='number of panel with same orientation and tilt')
    tilt = models.IntegerField(help_text='0 is horizontal, 90 is vertical positoned')
    azimuth = models.IntegerField(help_text='-180 is north, -90 is east, 0 is south and 90 is west')
    inverter = models.ForeignKey('Inverter', on_delete=models.CASCADE)

    def __str__(self):
        return self.name

    def __unicode__(self):
        return self.name
