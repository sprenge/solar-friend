from django.contrib import admin
from solar.models import System
from solar.models import Inverter
from solar.models import InverterType
from solar.models import SolarPanelGroup

class SystemAdmin(admin.ModelAdmin):
    model = System
    list_display = ['name', 'forecast_api_key', 'forecast_provider', 'latitude', 'longitude', 'influxdb_host', 'influxdb_database', 'influxdb_port']


class InverterTypeAdmin(admin.ModelAdmin):
    model = InverterType
    list_display = ['id', 'brand', 'brand_type']

class InverterAdmin(admin.ModelAdmin):
    model = Inverter
    list_display = ['name', 'max_power', 'system', 'host', 'user', 'password', 'inverter_type']

class SolarPanelGroupAdmin(admin.ModelAdmin):
    model = SolarPanelGroup
    list_display = ['name', 'power_per_panel', 'number_of_panels', 'tilt', 'azimuth', 'inverter']

# Register your models here.
admin.site.register(System, SystemAdmin)
admin.site.register(Inverter, InverterAdmin)
admin.site.register(InverterType, InverterTypeAdmin)
admin.site.register(SolarPanelGroup, SolarPanelGroupAdmin)