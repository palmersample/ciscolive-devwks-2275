"""
Example script to read wireless access points from NetBox, generate a NETCONF
XML RPC payload, and push to a WLC.
"""
# pylint: disable=loop-global-usage
import os
import sys
import pynetbox
from helpers import (create_request_session,
                     get_ap_wlc_associations,
                     provision_ap_on_wlc,
                     provision_ap_radios)

# Set the NetBox URL to the environment variable created during setup.
NETBOX_URL = os.environ.get("NETBOX_URL")

# Set the NetBox token to the environment variable created during setup.
NETBOX_TOKEN = os.environ.get("NETBOX_TOKEN")

# Initialize the pynetbox API object
netbox = pynetbox.api(url=NETBOX_URL, token=NETBOX_TOKEN)

# IPAM and DNS not setup in NetBox at this time.  Manually set remove device
# parameters for NETCONF
WLC_HOST = os.environ.get("WLC_HOST")
WLC_USERNAME = os.environ.get("WLC_USERNAME")
WLC_PASSWORD = os.environ.get("WLC_PASSWORD")

# Initialize the pynetbox API object
try:
    netbox = pynetbox.api(url=NETBOX_URL, token=NETBOX_TOKEN)
except pynetbox.RequestError:
    sys.exit("Unable to connect to NetBox.  Terminating.")

if __name__ == "__main__":
    try:
        access_points = netbox.dcim.devices.filter(role="ap")
    except pynetbox.RequestError:
        print("NetBox error happened when trying to query APs. Terminating.")

    print("*" * 78)

