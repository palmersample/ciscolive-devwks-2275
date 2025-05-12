"""
Cisco Live, DEVWKS-2275: "Supercharge Your Wireless Network with Programmability!"

Create an AP import .csv file with random AP data to be imported in
workshop code.
"""
import csv
import string
import random
import os
import pathlib
import argparse
from dotenv import dotenv_values
from helpers.rf_channel_map import allowed_channel_numbers_24ghz, channel_range_5ghz_20mhz

SCRIPT_PATH = pathlib.PurePath(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(SCRIPT_PATH.parent, "scripts")

WORKSHOP_ENV = dotenv_values(os.path.join(SCRIPT_PATH.parent, "workshop-env"))

DEFAULT_AP_COUNT = 2
DEFAULT_OUTPUT_FILE = os.path.join(CSV_PATH, "netbox-import.csv")

POD_NUMBER = WORKSHOP_ENV["POD_NUMBER"]

FLOOR_AP_LOCATIONS = ("N", "S", "E", "W", "C")

DEVICE_TYPES = (
    "air-ap-2802e-b-k9",
    "air-ap-1815w-b-k9",
    "c9136i-b",
    "c9124axe-a"
)

NETBOX_LOCATIONS = (
    "learning-and-certifications",
    "devnet-zone",
    "the-hub"
)

def generate_random_string(length, int_only=False, char_only=False):
    """
    Generate a random string of uppercase letters, numbers, or both.

    :param length: Length of string to generate
    :param int_only: Only include integers
    :param char_only: Only include characters (uppercase)
    :return: Generated random string
    """
    if int_only:
        selector = string.digits
    elif char_only:
        selector = string.ascii_uppercase
    else:
        selector = string.ascii_uppercase + string.digits
    return ''.join(random.choices(selector, k=length))

def generate_random_mac_address():
    """
    Generate a random MAC address formatted for NetBox Import

    :return: Generated random MAC address string
    """
    # Generate 6 random hexadecimal bytes
    mac_bytes = [random.randint(0x00, 0xff) for _ in range(6)]

    # Format the bytes as a MAC address string
    mac_address = ''.join([f"{byte:02x}" for byte in mac_bytes])

    return mac_address


print("*" * 78)
def create_access_point():
    """
    Generator to build a unique access point definition with random data.
    """
    # pylint: disable=line-too-long
    yield "device_name", f"AP{random.randint(1, 20)}{random.choice(FLOOR_AP_LOCATIONS)}{random.randint(100, 1000)}"
    yield "device_role", "ap"
    yield "device_type", random.choice(DEVICE_TYPES)
    yield "serial_number", f"Y{''.join(generate_random_string(2, char_only=True))}{generate_random_string(10)}"
    yield "asset_tag", generate_random_string(12)
    yield "site", "san-sdcc"
    yield "location", random.choice(NETBOX_LOCATIONS)
    yield "platform", "iosxe"
    yield "primary_wlc", f"pod{POD_NUMBER}-wlc"
    yield "secondary_wlc", ""
    yield "tertiary_wlc", ""
    yield "wired_mac", generate_random_mac_address()
    yield "radio0_mac", generate_random_mac_address()
    yield "radio0_band", "2.4"
    yield "radio0_rf_role", "ap"
    yield "radio0_enabled", bool(random.getrandbits(1))
    yield "radio0_channel_number", random.choice(allowed_channel_numbers_24ghz)
    yield "radio0_channel_width", ""
    yield "radio0_tx_power", random.randint(9, 18)
    yield "radio1_mac", generate_random_mac_address()
    yield "radio1_band", "5"
    yield "radio1_rf_role", "ap"
    yield "radio1_enabled", bool(random.getrandbits(1))
    yield "radio1_channel_number", random.choice(channel_range_5ghz_20mhz)
    yield "radio1_channel_width", 20
    yield "radio1_tx_power", random.randint(9, 18)

def generate_csv_file(ap_count=DEFAULT_AP_COUNT, output_file=DEFAULT_OUTPUT_FILE):
    """
    Build a specified number of access points and write them to a CSV file.

    :param ap_count: Number of access points to create
    :param output_file: CSV output file
    :return: None
    """

    ap_list = [dict(create_access_point()) for _ in range(0, ap_count)]

    with open(output_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=dict(create_access_point()).keys())
        writer.writeheader()
        for row in ap_list:
            writer.writerow(row)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create an AP import .csv file with random AP data",
    )
    parser.add_argument("-o", "--output-file",
                        default=DEFAULT_OUTPUT_FILE,
                        dest="output_file",
                        help="Output file name",
                        type=str)
    parser.add_argument("-c", "--count",
                        default=DEFAULT_AP_COUNT,
                        dest="device_count",
                        help="Number of devices to create",
                        type=int)
    args, _ = parser.parse_known_args()
    generate_csv_file(ap_count=args.device_count, output_file=args.output_file)
