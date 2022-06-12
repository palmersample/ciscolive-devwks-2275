"""
Example script to read wireless access points from NetBox, generate a NETCONF
XML RPC payload, and optionally push to a WLC.

If the --update parameter is passed, configure WLC using nccclient.  Otherwise
the XML RPC will be printed for review.
"""
import os
import sys
import argparse
import pynetbox
from ncclient import manager
from ncclient.transport.errors import SSHError
from jinja2 import Environment, FileSystemLoader, select_autoescape

parser = argparse.ArgumentParser()

parser.add_argument(
    "--update",
    dest="update_mode",
    default=False,
    action="store_true",
    help="Enable update mode - push NETCONF payload to device",
)

parser.add_argument(
    "--netbox-url",
    dest="netbox_url",
    default="http://127.0.0.1:8000",
    action="store",
    help="URL of the NetBox API endpoint.  Include scheme, host, and port.  "
    "Default: http://localhost:8000",
)


script_args = parser.parse_known_args()[0]

# Set the update mode based on the presence of --update
UPDATE_DEVICE = script_args.update_mode

# Set the default NetBox URL based on --netbox-url parameter or its default
NETBOX_URL = script_args.netbox_url

# Set the NetBox token to the environment variable NETBOX_TOKEN if present.
# Otherwise use a default development token
NETBOX_TOKEN = os.environ.get("NETBOX_TOKEN", "0123456789abcdef0123456789abcdef01234567")

# IPAM and DNS not setup in NetBox at this time.  Manually set remove device
# parameters for NETCONF
WLC_HOST = "192.168.123.128"
WLC_USERNAME = os.environ.get("WLC_USERNAME", "developer")
WLC_PASSWORD = os.environ.get("WLC_PASSWORD", "1234QWer")
TLS_VERIFY = False

# Initialize the pynetbox API object
try:
    nb = pynetbox.api(NETBOX_URL, token=NETBOX_TOKEN)
except pynetbox.RequestError:
    sys.exit("Unable to connect to NetBox.  Terminating")

try:
    access_points = nb.dcim.devices.filter(role="ap")
except pynetbox.RequestError:
    print("NetBox error happens when trying to query - might as well terminate here...")

template_env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(),
    lstrip_blocks=True,
    trim_blocks=True
)


wlc_netconf_template = template_env.get_template("provision_ap.j2")


template_data = {}

for ap in access_points:
    template_data.update({"device_name": ap.name})
    print(f"Processing AP {ap}... ")

    ap_interfaces = nb.dcim.interfaces.filter(device=ap.name)

    ap_mgmt_mac = nb.dcim.interfaces.get(mgmt_only=True, device=ap.name)
    ap_wired_mac = ap_mgmt_mac.mac_address

    for interface in ap_interfaces:
        try:
            netconf_payload = wlc_netconf_template.render(ap_name=ap.name,
                                                          ap_mac=ap_wired_mac,
                                                          ap_interfaces=ap_interfaces)

            if UPDATE_DEVICE:
                print("Update mode enabled.  Pushing NETCONF RPC to device...")
                try:
                    nc = manager.connect(host=WLC_HOST,
                                         port=830,
                                         timeout=30,
                                         username=WLC_USERNAME,
                                         password=WLC_PASSWORD,
                                         hostkey_verify=TLS_VERIFY)

                    with nc.locked("running"):
                        with nc.locked("candidate"):
                            nc.edit_config(target="candidate", config=netconf_payload)
                            commit_result = nc.commit()
                            print(f"Commit result: {commit_result}")
                except SSHError:
                    print("Unable to start NETCONF session, not updating WLC.")

            else:
                print(f"Update mode disabled.  NETCONF RPC:\n{netconf_payload}")

        except NameError as err:
            print(f"Missing required field: {err}")
