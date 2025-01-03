import logging
import subprocess
from datetime import timedelta

import apparse
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity_registry import async_get
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)
UPDATE_INTERVAL = timedelta(seconds=5)

existing_entities = {}
mac_to_name_map = {}

DEFAULT_IW_PATH = "/usr/bin/iw"
DEFAULT_INTERFACE = "wlan0"


class WifiClientSensor(SensorEntity):
    def __init__(self, coordinator, mac_address, initial_data, friendly_name=None):
        # Initial set
        self.coordinator = coordinator
        self._mac_address = mac_address
        self._attributes = initial_data
        self._friendly_name = friendly_name

    @property
    def unique_id(self):
        return self._mac_address

    @property
    def name(self):
        return f"WiFi Client {self._friendly_name if self._friendly_name else self._mac_address}"

    @property
    def state(self):
        # State Online or Offline
        return "Online" if self._attributes.get("associated", False) else "Offline"

    @property
    def extra_state_attributes(self):
        # Only return spexific values
        return {
            # 'Device': self._attributes.get('device'),
            # 'Inactive Time': self._attributes.get('inactive_time'),
            # 'Received Bytes': self._attributes.get('rx_bytes'),
            # 'Received Packets': self._attributes.get('rx_packets'),
            # 'Transmitted Bytes': self._attributes.get('tx_bytes'),
            # 'Transmitted Packets': self._attributes.get('tx_packets'),
            # 'TX Retries': self._attributes.get('tx_retries'),
            # 'TX Failed': self._attributes.get('tx_failed'),
            # 'RX Drop Misc': self._attributes.get('rx_drop_misc'),
            "Signal": self._attributes.get("signal"),
            # 'Signal Avg': self._attributes.get('signal_avg'),
            # 'TX Bitrate': self._attributes.get('tx_bitrate'),
            # 'RX Bitrate': self._attributes.get('rx_bitrate'),
            # 'RX Duration': self._attributes.get('rx_duration'),
            # 'Last ACK Signal': self._attributes.get('last_ack_signal'),
            "Authorized": self._attributes.get("authorized"),
            "Authenticated": self._attributes.get("authenticated"),
            "Associated": self._attributes.get("associated"),
            # 'Preamble': self._attributes.get('preamble'),
            # 'WMM/WME': self._attributes.get('wmm_wme'),
            # 'MFP': self._attributes.get('mfp'),
            # 'TDLS Peer': self._attributes.get('tdls_peer'),
            # 'DTIM Period': self._attributes.get('dtim_period'),
            # 'Beacon Interval': self._attributes.get('beacon_interval'),
            # 'Short Preamble': self._attributes.get('short_preamble'),
            # 'Short Slot Time': self._attributes.get('short_slot_time'),
            # 'Connected Time': self._attributes.get('connected_time')
        }

    @property
    def should_poll(self):
        # Should not be polled, we have a coordinator instead
        return False

    async def async_added_to_hass(self):
        # Add an listener for the coordinator for the update
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_on_coordinator_update)
        )

    def async_on_coordinator_update(self):
        # Update was triggered so update data and also wirte update to HA
        self.update_data()
        self.async_write_ha_state()

    def update_data(self):
        (
            _LOGGER.info(f"WiFi Client {self._mac_address} offline")
            if self._attributes.get("associated", False)
            and not self.coordinator.data.get(self._mac_address, {}).get(
                "associated", False
            )
            else (
                _LOGGER.info(f"WiFi Client {self._mac_address} online")
                if not self._attributes.get("associated", False)
                and self.coordinator.data.get(self._mac_address, {}).get(
                    "associated", False
                )
                else None
            )
        )
        self._attributes = self.coordinator.data.get(self._mac_address, {})
        self._friendly_name = mac_to_name_map.get(
            self._mac_address.upper(), self._mac_address
        )


def fetch_wifi_clients(iw_path, interface):
    command = f"{iw_path} dev {interface} station dump"
    return subprocess.run(command, shell=True, stdout=subprocess.PIPE).stdout.decode(
        "utf-8"
    )


def parse_wifi_clients(raw_data):
    return apparse.parse_iw_station(raw_data)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    # I dont know why this function is called twice if i use sesor - platform configuuration. But with this hack it works just calling once
    if "platform" not in config:
        return

    global mac_to_name_map
    # Get the Alias configuration from configuration.yaml
    wifi_clients_config = config.get("clients", [])
    # Create a dictionary to map MAC addresses to friendly names
    mac_to_name_map = (
        {client["mac"].upper(): client.get("name") for client in wifi_clients_config}
        if wifi_clients_config
        else {}
    )

    # Get iw_path and interface from configuration, or use defaults
    iw_path = config.get("iw_path", DEFAULT_IW_PATH)
    interface = config.get("interface", DEFAULT_INTERFACE)

    # Fetcher Function
    async def fetch_from_iw():
        raw_data = fetch_wifi_clients(iw_path, interface)
        parsed_data = parse_wifi_clients(raw_data)
        return parsed_data

    # The coordinator for all entities. So only on data fetch used to update all entities
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="wifi_clients",
        update_method=fetch_from_iw,
        update_interval=UPDATE_INTERVAL,
    )

    # Manual trigger
    await coordinator.async_refresh()

    # First inital add - later the update will do the rest
    global existing_entities
    entities = []
    for mac_address, client_data in coordinator.data.items():
        # Get the friendly name if provided else None
        friendly_name = mac_to_name_map.get(mac_address.upper())
        new_entity = WifiClientSensor(
            coordinator, mac_address, client_data, friendly_name
        )
        existing_entities[mac_address] = new_entity
        entities.append(new_entity)
    async_add_entities(entities, True)

    # Delete old entries
    provided_sensors = set()
    for sensor in entities:
        provided_sensors.add(sensor.entity_id)
    # Get the entity registry
    entity_registry = async_get(hass)
    # Identify the sensors not used any more
    sensors_to_remove = [
        entity.entity_id
        for entity in entity_registry.entities.values()
        if entity.platform == DOMAIN and entity.entity_id not in provided_sensors
    ]
    # Remove sensors that are no longer provided
    for sensor_id in sensors_to_remove:
        _LOGGER.info(f"Removing sensor: {sensor_id}")
        entity_registry.async_remove(sensor_id)

    # Now we need a function for delete or new entities.
    def coordinator_update():
        global existing_entities
        global mac_to_name_map

        new_entities = []
        for mac_address, client_data in coordinator.data.items():
            if mac_address not in existing_entities:
                # New Client forund, create a new entity
                friendly_name = mac_to_name_map.get(mac_address.upper())
                new_entity = WifiClientSensor(
                    coordinator, mac_address, client_data, friendly_name
                )
                existing_entities[mac_address] = new_entity
                new_entities.append(new_entity)
                _LOGGER.info(f"WiFi Client {mac_address} added")

        # Add new entities to Home Assistant
        if new_entities:
            async_add_entities(new_entities, True)

        # The next lines makes the Entity unavaible. I think thats not so nice like offline so I comment it
        # for mac_address in list(existing_entities.keys()):
        #     if mac_address not in coordinator.data:
        #         entity = existing_entities.pop(mac_address)
        #         hass.add_job(entity.async_remove())
        #         _LOGGER.info(f"WiFi Client {mac_address} deleted")

    # Link the coordinator update method
    coordinator.async_add_listener(coordinator_update)
