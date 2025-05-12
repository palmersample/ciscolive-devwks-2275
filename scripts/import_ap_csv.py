"""
Import a CSV file into NetBox for Wireless Devices.
"""
import csv
import argparse
import os
import pathlib
from dotenv import dotenv_values
import pynetbox
from helpers import (generate_device_details,
                     update_interfaces,
                     create_or_update_device)

# Read the environment variables created by the "prepare_lab.sh" script
SCRIPT_PATH = pathlib.PurePath(os.path.dirname(os.path.abspath(__file__)))
WORKSHOP_ENV = dotenv_values(os.path.join(SCRIPT_PATH.parent, "workshop-env"))

# Store the pod number to set NetBox custom field values
POD_NUMBER = WORKSHOP_ENV["POD_NUMBER"]

# Set the NetBox URL to the environment variable created during setup.
NETBOX_URL = WORKSHOP_ENV["NETBOX_URL"]

# Set the NetBox token to the environment variable created during setup.
NETBOX_TOKEN = WORKSHOP_ENV["NETBOX_TOKEN"]

# Initialize the pynetbox API object
netbox = pynetbox.api(url=NETBOX_URL, token=NETBOX_TOKEN)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c",
        "--csv-file",
        dest="csv_file",
        default="netbox-import.csv",
        action="store",
        help="CSV file to import.  Default: netbox-import.csv",
    )

    script_args = parser.parse_known_args()[0]

    # Set the CSV file to open based on the --csv-file parameter or its default
    csv_file = script_args.csv_file

