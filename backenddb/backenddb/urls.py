"""backenddb URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework import routers, serializers, viewsets
from solar.models import System
from solar.models import Inverter
from solar.models import InverterType
from solar.models import SolarPanelGroup

class SystemSerializer(serializers.ModelSerializer):
    class Meta:
        model = System
        fields = ['id', 'name', 'forecast_api_key', 'forecast_provider', 'latitude', 'longitude', 'influxdb_host', 'influxdb_database', 'influxdb_port']

class SystemViewSet(viewsets.ModelViewSet):
    queryset = System.objects.all()
    serializer_class = SystemSerializer

class InverterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Inverter
        fields = ['id', 'name', 'max_power', 'system', 'host', 'user', 'password', 'inverter_type']

class InverterViewSet(viewsets.ModelViewSet):
    queryset = Inverter.objects.all()
    serializer_class = InverterSerializer

class InverterTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = InverterType
        fields = ['id', 'brand', 'brand_type']

class InverterTypeViewSet(viewsets.ModelViewSet):
    queryset = InverterType.objects.all()
    serializer_class = InverterTypeSerializer

class SolarPanelGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = SolarPanelGroup
        fields = ['id', 'name', 'power_per_panel', 'number_of_panels', 'tilt', 'azimuth', 'inverter']

class SolarPanelGroupViewSet(viewsets.ModelViewSet):
    queryset = SolarPanelGroup.objects.all()
    serializer_class = SolarPanelGroupSerializer

router = routers.DefaultRouter()
router.register(r'system', SystemViewSet)
router.register(r'inverter', InverterViewSet)
router.register(r'inverter_type', InverterTypeViewSet)
router.register(r'solar_panel_group', SolarPanelGroupViewSet)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('rest/', include(router.urls)),
    path('api-auth/', include('rest_framework.urls'))

]
