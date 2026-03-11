import json

CODES_FILE = "codes.json"


def load_codes():

    with open(CODES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_codes(data):

    with open(CODES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)