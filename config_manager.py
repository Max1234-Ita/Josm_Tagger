import json
import os

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "hotkey": "ctrl+num 0",
    "font_family": "Segoe UI",
    "font_size": 10,
    "ui_scale": 1.0
}


def load_config():

    if not os.path.exists(CONFIG_FILE):

        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    # aggiunge automaticamente i parametri mancanti
    updated = False

    for k, v in DEFAULT_CONFIG.items():
        if k not in cfg:
            cfg[k] = v
            updated = True

    if updated:
        save_config(cfg)

    return cfg


def save_config(cfg):

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)