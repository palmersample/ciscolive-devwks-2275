"""
Helper functions for WLC configuration from NetBox data
"""
from jinja2 import Environment, FileSystemLoader, select_autoescape
from .request_helpers import http_exceptions
from .rf_channel_map import parse_netbox_rf_channel


# Initialize Jinja2 environment and load the XML template
template_env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(),
    lstrip_blocks=True,
    trim_blocks=True
)


def get_ap_wlc_associations(netbox_api, netbox_ap_object):
    """
    Get the list of WLCs to associate an access point with. Return a list of
    dicts containing the WLC name and DNS hostname

    :param netbox_api: pynetbox API object reference
    :param netbox_ap_object: Access point object reference from NetBox
    :return: List of dicts containing WLCs and DNS hostnames for association
    """
    associated_wlc_list = []
    for association_type in ["wlc_primary_association",
                             "wlc_secondary_association",
                             "wlc_tertiary_association"]:

        netbox_wlc_id = netbox_ap_object.custom_fields.get(association_type)
        if netbox_wlc_id:
            wlc_object = netbox_api.dcim.devices.get(id=netbox_wlc_id["id"])
            wlc_mgmt_ip = netbox_api.ipam.ip_addresses.get(address=str(wlc_object.primary_ip4))
            wlc_dns_name = wlc_mgmt_ip.dns_name

            ap_association = {"wlc_name": wlc_object.name,
                              "wlc_dns": wlc_dns_name}

            associated_wlc_list.append(ap_association)

    return associated_wlc_list


@http_exceptions
def provision_ap_on_wlc(request_session, ap_name, ap_mac):
    wlc_tag_template = template_env.get_template("ap_tags.j2")
    wlc_host_template = template_env.get_template("provision_ap_hostname.j2")

    ap_template = wlc_host_template.render(ap_name=ap_name, ap_mac=ap_mac)
    radio_cfg_url = "data/Cisco-IOS-XE-wireless-radio-cfg:radio-cfg-data"
    restconf_result = request_session.patch(url=radio_cfg_url,
                                            data=ap_template)
    if restconf_result.ok:
        print("OK")
    else:
        print("FAILED")


    # Assign default tags
    ap_tag_template = wlc_tag_template.render(ap_mac=ap_mac)
    radio_cfg_url = "data/Cisco-IOS-XE-wireless-ap-cfg:ap-cfg-data"
    restconf_result = request_session.patch(url=radio_cfg_url,
                                            data=ap_tag_template)
    print("\tAssigning default tags to AP... ", end="")
    if restconf_result.ok:
        print("OK")
    else:
        print("FAILED")


@http_exceptions
def provision_ap_radios(request_session, ap_name, ap_mac, ap_interfaces):
    wlc_interface_template = template_env.get_template("provision_ap_radios.j2")
    for interface in ap_interfaces:
        if str(interface.name).lower().startswith('radio'):
            print(f"\tConfiguring interface: {interface}... ", end="")
            interface_rf_details = parse_netbox_rf_channel(interface.rf_channel.value)

            # pylint: disable=line-too-long
            interface_template = wlc_interface_template.render(ap_name=ap_name,
                                                               ap_mac=ap_mac,
                                                               interface=interface,
                                                               interface_rf_details=interface_rf_details)
            # print(interface_template)
            radio_cfg_url = "data/Cisco-IOS-XE-wireless-radio-cfg:radio-cfg-data"
            restconf_result = request_session.patch(url=radio_cfg_url,
                                                    data=interface_template)
            if restconf_result.ok:
                print("OK")
            else:
                print("FAILED")

