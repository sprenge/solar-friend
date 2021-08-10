import logging
import requests
from homeassistant.const import ENERGY_KILO_WATT_HOUR
from homeassistant.helpers.entity import Entity
from homeassistant.components.sensor import SensorEntity
from homeassistant.util.dt import utc_from_timestamp


_LOGGER = logging.getLogger(__name__)

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the sensor platform."""
    try:
        host = config['host']
    except:
        host = 'localhost'
    add_entities([ElectricityInjection(host), ElectricityConsumption(host)])


class ElectricityInjection(SensorEntity):
    """Representation of a Sensor."""

    def __init__(self, host):
        """Initialize the sensor."""
        self._state = None
        self.host = host
        try:
            r = requests.get("http://{}:5300/solar-friend/api/v1.0/meter_values".format(self.host))
            v = r.json()["injection"]
            self._state = float(v)
        except:
            pass

    @property
    def name(self):
        """Return the name of the sensor."""
        return 'injection'

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return ENERGY_KILO_WATT_HOUR

    @property
    def state_class(self):
        return "measurement"

    @property
    def device_class(self):
        return "energy"

    @property
    def last_reset(self):
        return utc_from_timestamp(0)

    @property
    def unique_id(self):
        return "electricity_injection"

    def update(self):
        """Fetch new state data for the sensor.
        This is the only method that should fetch new data for Home Assistant.
        """
        # _LOGGER.error("update called injection {}".format(self.host))
        try:
            r = requests.get("http://{}:5300/solar-friend/api/v1.0/meter_values".format(self.host))
            v = r.json()["injection"]
            self._state = float(v)
        except:
            pass

class ElectricityConsumption(SensorEntity):
    """Representation of a Sensor."""

    def __init__(self, host):
        """Initialize the sensor."""
        self._state = None
        self.host = host
        try:
            r = requests.get("http://{}:5300/solar-friend/api/v1.0/meter_values".format(self.host))
            v = r.json()["consumption"]
            self._state = float(v)
        except:
            pass

    @property
    def name(self):
        """Return the name of the sensor."""
        return 'consumption'

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return ENERGY_KILO_WATT_HOUR

    @property
    def state_class(self):
        return "measurement"

    @property
    def device_class(self):
        return "energy"

    @property
    def last_reset(self):
        return utc_from_timestamp(0)

    @property
    def unique_id(self):
        return "electricity_consumption"

    def update(self):
        """Fetch new state data for the sensor.
        This is the only method that should fetch new data for Home Assistant.
        """
        # _LOGGER.error("update called consumption {}".format(self.host))
        try:
            r = requests.get("http://{}:5300/solar-friend/api/v1.0/meter_values".format(self.host))
            v = r.json()["consumption"]
            self._state = float(v)
        except:
            pass
