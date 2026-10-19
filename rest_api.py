"""Flask web page and REST API."""

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

from config import load_config
from opcua_reader import read_all_devices, read_device


config = load_config()

app = Flask(
    __name__,
    static_folder="web",
    static_url_path=""
)

CORS(app)


@app.route("/")
def home():
    return send_from_directory(
        "web",
        "index.html"
    )


@app.route("/api/devices")
def get_devices():
    try:
        devices = read_all_devices(config)
        return jsonify(devices)

    except Exception as error:
        return jsonify({
            "error": "Could not read OPC UA server",
            "details": str(error)
        }), 503


@app.route("/api/devices/<device_id>")
def get_device(device_id):
    try:
        device = read_device(
            config,
            device_id
        )

    except Exception as error:
        return jsonify({
            "error": "Could not read OPC UA server",
            "details": str(error)
        }), 503

    if device is None:
        return jsonify({
            "error": "Device not found",
            "deviceId": device_id
        }), 404

    return jsonify(device)


if __name__ == "__main__":
    print(
        f"REST API: "
        f"http://{config['api_host']}:"
        f"{config['api_port']}"
    )

    app.run(
        host=config["api_host"],
        port=config["api_port"]
    )