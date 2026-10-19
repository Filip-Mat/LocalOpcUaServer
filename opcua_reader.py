"""Read all devices from one OPC UA server."""

from datetime import datetime, timezone

from asyncua import ua
from asyncua.sync import Client


NODE_NAMES = {
    "deviceId": "DeviceId",
    "value": "Value",
    "unit": "Unit",
    "measuredAtUtc": "MeasuredAtUtc",
    "status": "Status"
}


def format_datetime(value):
    """Convert OPC UA datetime to an ISO UTC string."""

    if not isinstance(value, datetime):
        return value

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    return (
        value.astimezone(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def read_device_from_client(
    client,
    namespace_index,
    device_id
):
    """Read one known device from an open connection."""

    values = {}

    for field, node_name in NODE_NAMES.items():
        node_id = (
            f"device/{device_id}/{node_name}"
        )

        node = client.get_node(
            ua.NodeId(
                node_id,
                namespace_index
            )
        )

        values[field] = node.read_value()

    values["measuredAtUtc"] = format_datetime(
        values["measuredAtUtc"]
    )

    return values


def read_all_devices(config):
    """Discover and read every OPC UA device."""

    endpoint = config["opcua_endpoint"]

    with Client(endpoint, timeout=5) as client:
        namespace_index = (
            client.get_namespace_index(
                config["namespace_uri"]
            )
        )

        devices_node = client.get_node(
            ua.NodeId(
                "Devices",
                namespace_index
            )
        )

        devices = []

        for device_object in devices_node.get_children():
            identifier = str(
                device_object.nodeid.Identifier
            )

            prefix = "device/"

            if not identifier.startswith(prefix):
                continue

            device_id = identifier[len(prefix):]

            try:
                device = read_device_from_client(
                    client,
                    namespace_index,
                    device_id
                )

                devices.append(device)

            except Exception as error:
                print(
                    f"Kunde inte läsa "
                    f"{device_id}: {error}"
                )

        return sorted(
            devices,
            key=lambda device: device["deviceId"]
        )


def read_device(config, device_id):
    """Read one device by its deviceId."""

    endpoint = config["opcua_endpoint"]

    with Client(endpoint, timeout=5) as client:
        namespace_index = (
            client.get_namespace_index(
                config["namespace_uri"]
            )
        )

        try:
            return read_device_from_client(
                client,
                namespace_index,
                device_id
            )

        except Exception:
            return None
