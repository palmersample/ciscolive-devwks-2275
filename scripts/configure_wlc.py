"""
Example script to read wireless access points from NetBox, generate a NETCONF
XML RPC payload, and push to a WLC.
"""
import os
import sys
import requests
from requests.auth import HTTPBasicAuth
import pynetbox
from ncclient import manager
from ncclient.transport.errors import SSHError
from jinja2 import Environment, FileSystemLoader, select_autoescape
from rf_channel_map import parse_netbox_rf_channel

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

try:
    access_points = netbox.dcim.devices.filter(role="ap")
except pynetbox.RequestError:
    print("NetBox error happened when trying to query APs. Terminating.")

# Initialize Jinja2 environment and load the XML template
template_env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(),
    lstrip_blocks=True,
    trim_blocks=True
)

wlc_tag_template = template_env.get_template("ap_tags.j2")
wlc_host_template = template_env.get_template("provision_ap_hostname.j2")
wlc_interface_template = template_env.get_template("restconf_provision.j2")
wlc_netconf_template = template_env.get_template("provision_ap.j2")

request_baseurl = f"https://{WLC_HOST}/restconf"

request_headers = {
    "Content-Type": "application/yang-data+json",
    "Accept": "application/yang-data+json"
}

template_data = {}

for ap in access_points:
    template_data.update({"device_name": ap.name})
    print(f"Processing AP {ap.name}... ")
    ap_interfaces = netbox.dcim.interfaces.filter(device=ap)
    ap_mgmt_interface = netbox.dcim.interfaces.get(device=ap, mgmt_only=True)
    ap_mgmt_mac = ap_mgmt_interface.mac_address

    try:
        # Set AP hostname with RESTCONF
        ap_template = wlc_host_template.render(ap_name=ap.name, ap_mac=ap_mgmt_mac)
        print(ap_template)
        radio_cfg_url = f"{request_baseurl}/data/Cisco-IOS-XE-wireless-radio-cfg:radio-cfg-data"
        restconf_result = requests.patch(url=radio_cfg_url,
                                         headers=request_headers,
                                         auth=(WLC_USERNAME, WLC_PASSWORD),
                                         # auth=HTTPBasicAuth(WLC_USERNAME, WLC_PASSWORD),
                                         data=ap_template)
        print(restconf_result.status_code)

        # Assign default tags
        ap_tag_template = wlc_tag_template.render(ap_mac=ap_mgmt_mac)
        radio_cfg_url = f"{request_baseurl}/data/Cisco-IOS-XE-wireless-ap-cfg:ap-cfg-data"
        restconf_result = requests.patch(url=radio_cfg_url,
                                         headers=request_headers,
                                         auth=(WLC_USERNAME, WLC_PASSWORD),
                                         data=ap_tag_template)
        print(restconf_result.status_code)
    except Exception as err:
        print(err)


    try:
        # netconf = manager.connect(host=WLC_HOST,
        #                           port=830,
        #                           username=WLC_USERNAME,
        #                           password=WLC_PASSWORD,
        #                           ssh_config="../ssh/netconf_ssh_config")
        #
        # with netconf.locked("running"):
        #     with netconf.locked("candidate"):
        for interface in ap_interfaces:
            print(f"\tConfiguring interface: {interface}")
            if str(interface.name).lower().startswith('radio'):
                interface_rf_details = parse_netbox_rf_channel(interface.rf_channel.value)
            # else:
            #     interface_rf_details = None

                interface_template = wlc_interface_template.render(ap_name=ap.name,
                                                                   ap_mac=ap_mgmt_mac,
                                                                   interface=interface,
                                                                   interface_rf_details=interface_rf_details)
                print(interface_template)
                radio_cfg_url = f"{request_baseurl}/data/Cisco-IOS-XE-wireless-radio-cfg:radio-cfg-data"
                restconf_result = requests.patch(url=radio_cfg_url,
                                                 headers=request_headers,
                                                 auth=(WLC_USERNAME, WLC_PASSWORD),
                                                 # auth=HTTPBasicAuth(WLC_USERNAME, WLC_PASSWORD),
                                                 data=interface_template)
                print(restconf_result.status_code)

            # netconf_payload = wlc_netconf_template.render(ap_name=ap.name,
            #                                               ap_mac=ap_mgmt_mac,
            #                                               interface=interface,
            #                                               interface_rf_details=interface_rf_details)

            # netconf.edit_config(target="candidate", config=netconf_payload)
        # commit_result = netconf.commit()
        # print(f"Commit result: {commit_result.ok}\n")

    except SSHError:
        print("Unable to start NETCONF session, not updating WLC.")
    except NameError as err:
        print(f"Missing required field: {err}")
