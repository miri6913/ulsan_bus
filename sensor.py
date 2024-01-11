import logging
import requests
import math
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from datetime import timedelta
from datetime import datetime

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (CONF_NAME, CONF_API_KEY, CONF_ICON)
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle

REQUIREMENTS = ['xmltodict==0.12.0']

_LOGGER = logging.getLogger(__name__)

CONF_STATIONS   = 'stations'
CONF_STATION_ID = 'station_id'
CONF_BUS_ID = 'bus_id'
CONF_VIEW_TYPE = 'view_type'
CONF_STATION_UPDATE_TIME = 'update_time'

ULSAN_BUS_API_URL = 'http://openapi.its.ulsan.kr/UlsanAPI/getBusArrivalInfo.xo?stopid={}&pageNo=1&numOfRows=100&type=json\&serviceKey={}'

_BUS_PROPERTIES = {
    'busRouteId': '노선ID',
    'rtNm': '버스번호',
    'syncDate': 'Sync Date',
    'isUpdate': 'is Update'
}

DEFAULT_VIEW_TYPE = 'S'
ICON_STATION      = 'mdi:nature-people'
ICON_BUS          = 'mdi:bus'
ICON_BUS_READY    = 'mdi:bus-clock'
ICON_BUS_ALERT    = 'mdi:bus-alert'
ICON_SIGN_CAUTION = 'mdi:sign-caution'
ICON_EYE_OFF      = 'mdi:eye-off'

DEFAULT_START_HOUR = 5
DEFAULT_END_HOUR   = 24
DEFAULT_STATION_NAME = '삼호교'

MIN_TIME_BETWEEN_API_UPDATES    = timedelta(seconds=120)

MIN_TIME_BETWEEN_STATION_SENSOR_UPDATES = timedelta(seconds=90) 
MIN_TIME_BETWEEN_BUS_SENSOR_UPDATES = timedelta(seconds=10)

ATTR_ROUTE_ID = 'busRouteId'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_API_KEY): cv.string,
    vol.Required(CONF_STATIONS): vol.All(cv.ensure_list, [{
        vol.Required(CONF_STATION_ID): cv.string,
        vol.Optional(CONF_NAME, default = DEFAULT_STATION_NAME): cv.string,
    }])   
})

def second2min(val):
    try:
        if 60 >  int(val):
            return '{}초'.format(val)
        else:
            min = math.floor(int(val)/60)
            sec = int(val)%60
            return '{}분{}초'.format(str(min), str(sec))
    except Exception as ex:
        _LOGGER.error('Failed to second2min() Seoul Bus Method Error: %s', ex)

    return val

def setup_platform(hass, config, add_entities, discovery_info=None):
    name = config.get(CONF_NAME)
    api_key         = config.get(CONF_API_KEY)
    stations        = config.get(CONF_STATIONS)

    sensors = []


    # sensor add
    for station in stations:
        api = UlsanBusAPI(api_key, station[CONF_STATION_ID])

        # station sensor add
        sensor = BusStationSensor(station[CONF_STATION_ID], station[CONF_NAME], api)
        sensor.update()
        sensors += [sensor]

        # bus sensor add
        for bus_id, value in sensor.buses.items():
            try:
                sensors += [BusSensor(station[CONF_STATION_ID], station[CONF_NAME], bus_id, value.get(CONF_NAME, ''), value, api)]
            except Exception as ex:
                _LOGGER.error('[Seoul Bus] Failed to BusSensor add  Error: %s', ex)

    add_entities(sensors, True)

class UlsanBusAPI:
    def __init__(self, api_key, station_id):
        """Initialize the Seoul Bus API."""
        self._api_key = api_key
        self._station_id  = station_id
        self._isUpdate  = True

        self._isError   = False
        self._errorCd   = None
        self._errorMsg  = None

        self._sync_date = None
        self.result = {}
    
    def update(self):
        """Update function for updating api information."""
        dt = datetime.now()
        syncDate = dt.strftime("%Y-%m-%d %H:%M:%S")

        self._sync_date = syncDate

        if dt.hour > DEFAULT_START_HOUR and dt.hour < DEFAULT_END_HOUR:
            self._isUpdate = True
        else:
            self._isUpdate = False
        
        import xmltodict
        try:
            url = ULSAN_BUS_API_URL.format(self._api_key, self._station_id)
            
            bus_dict = {}
            response = requests.get(url)
            self._isError   = False
            self._errorCd   = None
            self._errorMsg  = None
            
            d = xmltodict.parse(html)
            jsonst = json.dumps(d['tableInfo']['list']['row'])
            rows = json.loads(jsonst)
            for i in range(len(rows)):
                bus_dict[row[i]['ROUTEID']] = {
                    'busRouteId': row[i]['ROUTEID']
                    'rtNm': row[i]['ROUTENM']
                    'present': row[i]['PRESENTSTOPNM']
                    'syncDate': syncDate,
                    'isUpdate': self._isUpdate
                }
            
            self.result = bus_dict

class BusStationSensor(Entity):
    def __init__(self, id, name, api):
        self._station_id = id
        self._station_name = name
        self._isUpdate = None
        self._stt_time = None
        self._end_time = None

        self._sync_date = None

        self._api   = api
        self._icon  = ICON_STATION
        self._state = None
        self.buses  = {}
        
        def entity_id(self):
            return 'sensor.ulsan_bus_s{}'.format(self._station_id)
        
        def name(self):
            if not self._station_name:
                return 'St.{}'.format(self._station_id)
            return '{}({})'.format(self._station_name, self._station_id)
        def icon(self):
            if self._api._isError:
                return ICON_SIGN_CAUTION

            if not self._isUpdate:
                return ICON_EYE_OFF

            if not self._api._isUpdate:
                return ICON_EYE_OFF

            return self._icon
        def state(self):
            if self._api._isError:
                return 'Error'

            if not self._isUpdate:
                return '-'

            if not self._isUpdate:
                return '-'

        def update(self):
            if self._api is None:
                return

            if self._isUpdate is None:
                self._api.update()

            dt = datetime.now()
            syncDate = dt.strftime("%Y-%m-%d %H:%M:%S")

            self._sync_date = syncDate
            self._isUpdate = True

            if self._isUpdate:
                self._api.update()

            buses_dict = self._api.result
            self.buses = buses_dict
            
        def device_state_attributes(self):
        """Attributes."""
            attr = {}

        # API Error Contents Attributes Add
            if self._api._isError :
                attr['API Error Code'] = self._api._errorCd
                attr['API Error Msg'] = self._api._errorMsg

            for key in sorted(self.buses):
                attr['{} [{}]'.format(self.buses[key].get('rtNm', key), self.buses[key].get('present', '-'))] 

            attr['Sync Date'] = self._sync_date
            attr['is Update'] = self._isUpdate

            return attr

class BusSensor(Entity):
    def __init__(self, station_id, station_name, bus_id, bus_name, values, api):
        self._station_id   = station_id
        self._station_name = station_name
        self._bus_id   = bus_id
        self._bus_name = bus_name

        self._isUpdate = None
        self._stt_time = None
        self._end_time = None

        self._api = api
        self._state = None
        self._data  = {}

        self._rtNm = values['rtNm']



    @property
    def entity_id(self):
        """Return the entity ID."""
        return 'sensor.ulsan_bus_{}_{}'.format(self._station_id, self._bus_id)

    @property
    def name(self):
        """Return the name of the sensor, if any."""
        station_name = self._station_name

        if not self._station_name:
            station_name = 'St.{}'.format(self._station_id)

        if not self._bus_name:
            return '{} {}'.format(station_name, self._rtNm)

        return self._bus_name

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        if not self._isUpdate:
            return ICON_BUS_READY

        return ICON_BUS

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        if not self._isUpdate:
            return ''
        else:
            return '초'

    @property
    def state(self):
        """Return the state of the sensor."""
        if not self._isUpdate:
            return '-'
        else second2min(self._data['traTime1'])

        

    @Throttle(MIN_TIME_BETWEEN_BUS_SENSOR_UPDATES)
    def update(self):
        """Get the latest state of the sensor."""
        if self._api is None:
            return

        dt = datetime.now()
        syncDate = dt.strftime("%Y-%m-%d %H:%M:%S")

        self._sync_date = syncDate


        if len(self._station_update_time) > 0:
            stt_tm = None
            end_tm = None

            for item in self._station_update_time:
                stt_tm = item['start_time']
                end_tm = item['end_time']

                self._stt_time = stt_tm
                self._end_time = end_tm

            self._isUpdate = isBetweenNowTime(stt_tm, end_tm)

        buses_dict = self._api.result
        self._data = buses_dict.get(self._bus_id,{})



    @property
    def device_state_attributes(self):
        """Attributes."""
        attr = {}

        for key in self._data:
           attr[_BUS_PROPERTIES[key]] = self._data[key]

        attr[_BUS_PROPERTIES['syncDate']] = self._sync_date

        attr[_BUS_PROPERTIES['isUpdate']]   = self._isUpdate


        return attr              
  