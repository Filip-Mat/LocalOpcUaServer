# Local OPC UA Server

Programmet läser sensordata från Azure IoT Hub, gör datan tillgänglig via OPC UA och visar den genom ett REST-API.

## Första gången

Öppna PowerShell i mappen `LocalOpcUaServer`.

Skapa Pythonmiljön:

```powershell
py -m venv .venv
```

Installera paketen:

```powershell
.\.venv\Scripts\python.exe -m pip install asyncua azure-eventhub azure-iot-device Flask Flask-Cors
```

## Starta OPC UA-servern

Öppna PowerShell i `LocalOpcUaServer` och ange Azure-inställningarna:

```powershell
$env:EVENT_HUB_CONNECTION_STRING='EVENT-HUB-COMPATIBLE-ENDPOINT-STRING'
```

```powershell
$env:EVENT_HUB_NAME='EVENT-HUB-COMPATIBLE-NAME'
```

```powershell
$env:EVENT_HUB_CONSUMER_GROUP='$Default'
```

Starta servern:

```powershell
.\.venv\Scripts\python.exe .\azure_opcua_server.py
```

Låt terminalfönstret vara öppet.

## Starta REST-API:t

Öppna ett nytt PowerShell-fönster i samma mapp.

Starta API:t:

```powershell
.\.venv\Scripts\python.exe .\rest_api.py
```

## Skicka ett testmeddelande

Hämta enhetens Primary connection string från:

```text
Azure IoT Hub → Devices → välj en device → Primary connection string
```

Öppna ett tredje PowerShell-fönster i `LocalOpcUaServer`.

Spara connection stringen som en miljövariabel:

```powershell
$env:IOTHUB_DEVICE_CONNECTION_STRING='DEVICE-PRIMARY-CONNECTION-STRING'
```

Kontrollera meddelandet i `send_test_message.py`. Det ska exempelvis se ut så här:

```python
payload = {
    "deviceId": "example-device",
    "value": 56.3,
    "unit": "%"
}
```

Skicka testmeddelandet:

```powershell
.\.venv\Scripts\python.exe .\send_test_message.py
```

OPC UA-servern ska redan vara startad när testmeddelandet skickas.

Varje test är ett riktigt IoT Hub-meddelande och räknas mot hubbens dagliga meddelandekvot.

## Använd API:t

Visa alla upptäckta enheter:

```text
http://127.0.0.1:8000/api/devices
```

Visa en specifik enhet:

```text
http://127.0.0.1:8000/api/devices/example-device
```

Ersätt `example-device` med enhetens riktiga `deviceId`.

En enhet visas först efter att ett nytt telemetrimeddelande har kommit från IoT Hub.

JSON-formatet som skickas till IoT Hub:

```json
{
  "deviceId": "example-device",
  "value": 56.3,
  "unit": "%"
}
```

OPC UA-servern lägger själv till `measuredAtUtc` och `status`.

REST-API:t ger därför exempelvis:

```json
{
  "deviceId": "example-device",
  "value": 56.3,
  "unit": "%",
  "measuredAtUtc": "2026-10-19T14:30:00Z",
  "status": "online"
}
```

## Stoppa programmen

Stoppa OPC UA-servern och REST-API:t med:

```text
Ctrl+C
```

Azure connection strings är hemliga och ska inte sparas i GitHub.
