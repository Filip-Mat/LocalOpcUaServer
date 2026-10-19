import json
import os

from azure.iot.device import IoTHubDeviceClient, Message


connection_string = os.environ[
    "IOTHUB_DEVICE_CONNECTION_STRING"
]

payload = {
    "deviceId": "filip-humidity-sensor",
    "value": 56.3,
    "unit": "%"
}

message = Message(
    json.dumps(payload)
)

message.content_type = "application/json"
message.content_encoding = "utf-8"

client = IoTHubDeviceClient.create_from_connection_string(
    connection_string,
    websockets=True
)

try:
    print("Ansluter till IoT Hub...")

    client.connect()

    print(
        "Skickar:",
        json.dumps(payload, indent=2)
    )

    client.send_message(message)

    print("Testmeddelandet skickades.")

finally:
    client.shutdown()
