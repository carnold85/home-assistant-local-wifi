# Local-WiFi: A Custom Home Assistant Component

`local-wifi` is a custom integration for Home Assistant that adds sensors to monitor WiFi clients connected to a host system running **hostapd**. It utilizes the `iw` command to retrieve detailed information about connected peers and their status.

## Features

The `local-wifi` component creates entities for each WiFi client, providing detailed attributes such as:

- **State**: Indicates if the client is online or offline.
- **Signal**: Signal strength of the client.
- **Authorized**: Whether the client is authorized.
- **Authenticated**: Whether the client is authenticated.
- **Associated**: Whether the client is associated with the access point.

Additionally, MAC addresses can be replaced with friendly names for better readability.

## Prerequisites

1. **hostapd** must be installed and running on the host system.
2. The `iw` command must be accessible to Home Assistant. Ensure appropriate permissions are set to allow Home Assistant to execute `iw`.

## Installation

1. Copy the `local-wifi` integration to your Home Assistant custom components directory:
   ```
   custom_components/local_wifi/
   ```

2. Verify that the `iw` command is installed and functioning on your system.

## Configuration

Enable the `local-wifi` component by adding the configuration under `sensor` in your `configuration.yaml` file. 

### Example Configuration

```yaml
sensor:
  # My own WiFi Entities
  - platform: local_wifi
    interface: "wifi0"  # Optional, default is "wlan0"
    clients:
      # Assign friendly names to clients
      - mac: "AA:BB:CC:DD:EE:FF"
        name: "Smartphone"
      - mac: "11:22:33:44:55:66"
        name: "Laptop"
```

### Default Values

- **IW Path**: `/usr/bin/iw`
- **Interface**: `wlan0`

If you use different paths or interfaces, specify them in the configuration.

## Example Sensor Attributes

Each WiFi client entity provides the following attributes:

- `Signal`: The signal strength of the client.
- `Authorized`: Indicates whether the client is authorized.
- `Authenticated`: Indicates whether the client is authenticated.
- `Associated`: Indicates whether the client is associated.
- `MAC Address`: The unique identifier of the client (unless overridden by a friendly name).

## Troubleshooting

- Ensure Home Assistant has permission to execute the `iw` command.
- Check the Home Assistant logs for error messages related to the `local-wifi` integration.