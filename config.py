"""Read settings from config.json."""

import json
from pathlib import Path


CONFIG_FILE = Path(__file__).with_name(
    "config.json"
)


def load_config():
    with CONFIG_FILE.open(
        encoding="utf-8"
    ) as file:
        config = json.load(file)

    required_settings = [
        "api_host",
        "api_port",
        "namespace_uri",
        "opcua_endpoint"
    ]

    for setting in required_settings:
        if setting not in config:
            raise ValueError(
                f"config.json saknar '{setting}'"
            )

    return config