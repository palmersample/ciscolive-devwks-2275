"""
Example script to read wireless access points from NetBox, generate a RESTCONF
message-body, and push to a WLC.
"""
import os
import pathlib
import sys
from dotenv import dotenv_values
import pynetbox
from helpers import (create_request_session,
                     get_ap_wlc_associations,
                     provision_ap_on_wlc,
                     provision_ap_radios)

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

# Collect WLC username and password from environment
WLC_USERNAME = WORKSHOP_ENV["WLC_USERNAME"]
WLC_PASSWORD = WORKSHOP_ENV["WLC_PASSWORD"]

# Initialize the pynetbox API object
try:
    netbox = pynetbox.api(url=NETBOX_URL, token=NETBOX_TOKEN)
except pynetbox.RequestError:
    sys.exit("Unable to connect to NetBox.  Terminating.")

if __name__ == "__main__":
    try:
        access_points = netbox.dcim.devices.filter(role="ap",
                                                   cf_workshop_pod_number=POD_NUMBER)
    except pynetbox.RequestError:
        print("NetBox error happened when trying to query APs. Terminating.")

    print("*" * 78)

