
import json

CODES_FILE = "codes.json"


def load_codes():

    try:
        with open(CODES_FILE, "r", encoding="utf8") as f:
            return json.load(f)
    except:
        return {}


def save_codes(codes):

    with open(CODES_FILE, "w", encoding="utf8") as f:
        json.dump(codes, f, indent=4)