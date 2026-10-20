import json
import os
import queue
import threading
import time
from datetime import datetime, timezone

from asyncua import ua
from asyncua.sync import Server
from azure.eventhub import EventHubConsumerClient


# Azure-inställningar

EVENT_HUB_CONNECTION_STRING = os.environ[
    "EVENT_HUB_CONNECTION_STRING"
]

EVENT_HUB_NAME = os.environ[
    "EVENT_HUB_NAME"
]

EVENT_HUB_CONSUMER_GROUP = os.getenv(
    "EVENT_HUB_CONSUMER_GROUP",
    "$Default"
)


# OPC UA-inställningar

OPC_ENDPOINT = os.getenv(
    "OPC_ENDPOINT",
    "opc.tcp://127.0.0.1:4840"
)

NAMESPACE_URI = "urn:nackademin:telemetry"

TELEMETRY_TIMEOUT_SECONDS = 180


# Azure-tråden lägger meddelanden i denna kö.
# OPC UA-serverns huvudtråd hämtar dem sedan.

updates = queue.Queue()


def on_azure_event(partition_context, event):
    """Körs varje gång ett Azure-meddelande tas emot."""

    try:
        text = event.body_as_str(encoding="UTF-8")
        payload = json.loads(text)

        if not isinstance(payload, dict):
            return

        # Endast det platta OPC UA-formatet används.
        required_fields = {
            "deviceId",
            "value",
            "unit"
        }

        if not required_fields.issubset(payload):
            # Exempelvis dashboardens measurements-format
            # ignoreras utan att servern kraschar.
            return

        device_id = str(payload["deviceId"]).strip()
        sensor_value = float(payload["value"])
        sensor_unit = str(payload["unit"]).strip()

        if not device_id:
            raise ValueError(
                "deviceId får inte vara tomt."
            )

        measured_at = datetime.now(timezone.utc)

        updates.put({
            "deviceId": device_id,
            "value": sensor_value,
            "unit": sensor_unit,
            "measuredAtUtc": measured_at
        })

        print(
            f"Azure: {device_id}, "
            f"{sensor_value} {sensor_unit}",
            flush=True
        )

    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError
    ) as error:
        print(
            f"Ogiltigt Azure-meddelande: {error}",
            flush=True
        )


def listen_to_azure():
    """Lyssnar kontinuerligt på IoT Hub."""

    while True:
        try:
            consumer = (
                EventHubConsumerClient
                .from_connection_string(
                    conn_str=EVENT_HUB_CONNECTION_STRING,
                    consumer_group=EVENT_HUB_CONSUMER_GROUP,
                    eventhub_name=EVENT_HUB_NAME
                )
            )

            print(
                "Ansluter till Azure IoT Hub...",
                flush=True
            )

            print(
                f"Consumer group: "
                f"{EVENT_HUB_CONSUMER_GROUP}",
                flush=True
            )

            with consumer:
                consumer.receive(
                    on_event=on_azure_event,
                    starting_position="@latest"
                )

        except Exception as error:
            print(
                f"Azure-anslutningen misslyckades: "
                f"{error}",
                flush=True
            )

            print(
                "Försöker ansluta igen om fem sekunder.",
                flush=True
            )

            time.sleep(5)


# Skapa OPC UA-servern

server = Server()

server.set_endpoint(OPC_ENDPOINT)

server.set_server_name(
    "Local Azure OPC UA Server"
)

server.set_security_policy([
    ua.SecurityPolicyType.NoSecurity
])

namespace_index = server.register_namespace(
    NAMESPACE_URI
)


# Alla dynamiska enheter läggs under Objects/Devices.

devices_object = server.nodes.objects.add_object(
    ua.NodeId("Devices", namespace_index),
    "Devices"
)


# Innehåller OPC UA-noderna för varje deviceId.

device_nodes = {}


def create_device_nodes(
    device_id,
    sensor_value,
    sensor_unit,
    measured_at
):
    """Skapar OPC UA-noder för ett nytt deviceId."""

    device_object = devices_object.add_object(
        ua.NodeId(
            f"device/{device_id}",
            namespace_index
        ),
        device_id
    )

    nodes = {
        "deviceId": device_object.add_variable(
            ua.NodeId(
                f"device/{device_id}/DeviceId",
                namespace_index
            ),
            "DeviceId",
            device_id
        ),

        "value": device_object.add_variable(
            ua.NodeId(
                f"device/{device_id}/Value",
                namespace_index
            ),
            "Value",
            sensor_value
        ),

        "unit": device_object.add_variable(
            ua.NodeId(
                f"device/{device_id}/Unit",
                namespace_index
            ),
            "Unit",
            sensor_unit
        ),

        "measuredAtUtc": device_object.add_variable(
            ua.NodeId(
                f"device/{device_id}/MeasuredAtUtc",
                namespace_index
            ),
            "MeasuredAtUtc",
            measured_at
        ),

        "status": device_object.add_variable(
            ua.NodeId(
                f"device/{device_id}/Status",
                namespace_index
            ),
            "Status",
            "online"
        ),

        "lastReceived": time.monotonic()
    }

    device_nodes[device_id] = nodes

    print(
        f"Ny OPC UA-enhet skapad: {device_id}",
        flush=True
    )

    return nodes


def update_device(message):
    """Skapar eller uppdaterar rätt OPC UA-enhet."""

    device_id = message["deviceId"]
    sensor_value = message["value"]
    sensor_unit = message["unit"]
    measured_at = message["measuredAtUtc"]

    if device_id not in device_nodes:
        nodes = create_device_nodes(
            device_id,
            sensor_value,
            sensor_unit,
            measured_at
        )
    else:
        nodes = device_nodes[device_id]

        nodes["value"].write_value(sensor_value)
        nodes["unit"].write_value(sensor_unit)
        nodes["measuredAtUtc"].write_value(measured_at)
        nodes["status"].write_value("online")
        nodes["lastReceived"] = time.monotonic()

    print(
        f"OPC UA uppdaterad: "
        f"{device_id} = "
        f"{sensor_value} {sensor_unit}",
        flush=True
    )


def update_offline_statuses():
    """Markerar enheter offline efter 20 sekunder."""

    current_time = time.monotonic()

    for device_id, nodes in device_nodes.items():
        elapsed = (
            current_time - nodes["lastReceived"]
        )

        if elapsed > TELEMETRY_TIMEOUT_SECONDS:
            current_status = (
                nodes["status"].read_value()
            )

            if current_status != "offline":
                nodes["status"].write_value(
                    "offline"
                )

                print(
                    f"{device_id} markerades offline.",
                    flush=True
                )


# Starta servern

try:
    server.start()

    print(
        f"OPC UA-server startad: {OPC_ENDPOINT}",
        flush=True
    )

    print(
        f"Namespace: {NAMESPACE_URI}",
        flush=True
    )

    azure_thread = threading.Thread(
        target=listen_to_azure,
        daemon=True
    )

    azure_thread.start()

    while True:
        try:
            message = updates.get(timeout=1)
            update_device(message)

        except queue.Empty:
            pass

        update_offline_statuses()

except KeyboardInterrupt:
    print(
        "Stoppar OPC UA-servern.",
        flush=True
    )

finally:
    server.stop()
