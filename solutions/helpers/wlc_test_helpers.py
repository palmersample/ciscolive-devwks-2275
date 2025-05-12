"""
Helper functions for WLC configuration tests from NetBox data
"""
from requests.exceptions import RequestException
from .request_helpers import http_exceptions
from .rf_channel_map import parse_netbox_rf_channel


WIRELESS_DEFAULTS = {
    "5": {
        "tx_power": 1,
        "channel": 36,
        "channel_width": 20,
        "admin_state": True,
    },
    "24": {
        "tx_power": 1,
        "channel": 1,
        "channel_width": 22,  # Actual SHOULD be 20; this is for NetBox map
        "admin_state": True,
    }
}

BASE_NODE = "data/Cisco-IOS-XE-wireless-radio-cfg:radio-cfg-data"

# String formats for varying levels of tests
LEVEL_1_TEST = "        {test_name:<30}... "
LEVEL_2_TEST = "            {test_name:<26}... "
LEVEL_3_TEST = "                {test_name:<22}... "
LEVEL_4_TEST = "                    {test_name:<18}... "


@http_exceptions
def validate_ap_name(request_session, ap_name, ap_mac):
    """
    Test that the supplied AP name and MAC are configured on the WLC.

    :param request_session: Request session reference to RESTCONF endpoint
    :param ap_name: AP name to be assigned
    :param ap_mac: AP Ethernet MAC address
    :return: None
    """
    print(LEVEL_1_TEST.format(test_name="AP name present in config DB"), end="")
    validation_url = f"{BASE_NODE}/ap-spec-configs/ap-spec-config={ap_mac}"
    try:
        restconf_result = request_session.get(url=validation_url)
        if restconf_result.ok:
            # The YANG node is a list, but the AP was specified so the first element
            # _should_ be the only returned item.
            model_result = restconf_result.json()\
                ["Cisco-IOS-XE-wireless-radio-cfg:ap-spec-config"][0]

    except RequestException:
        print("FAILED - AP not present")

    else:
        # Make sure the name and MAC match for a successful result
        if ((model_result["ap-eth-mac-addr"].upper() == ap_mac.upper()) and
                (model_result["ap-host-name"].upper() == ap_name.upper())):
            print("OK")
        else:
            print("FAILED - AP MAC mismatch!")

@http_exceptions
def validate_ap_radios(request_session, ap_mac, ap_interfaces):
    """
    Iterate over each radio interface and verify the channel, width,
    transmit power, and DCA/DTP parameters match the desired state.

    :param request_session: Request session reference to RESTCONF endpoint
    :param ap_mac: AP Ethernet MAC address
    :param ap_interfaces: NetBox object list reference to radio interfaces
    :return: None
    """
    # pylint: disable=too-many-locals, too-many-branches
    validation_url = f"{BASE_NODE}/ap-specific-configs/ap-specific-config={ap_mac}"
    radio_interfaces = [r for r in ap_interfaces if r.name.startswith("radio")]
    print(LEVEL_1_TEST.format(test_name="Testing radio configuration"), end="")
    try:
        restconf_result = request_session.get(url=validation_url)

        # The URL specifies the MAC address, so we know the first
        # element is the desired AP.
        wlc_radio_config = restconf_result.json()\
            ["Cisco-IOS-XE-wireless-radio-cfg:ap-specific-config"][0]\
            ["ap-specific-slot-configs"]["ap-specific-slot-config"]

    except RequestException:
        print("FAILED - no radio config present")

    else:
        print()
        for interface in radio_interfaces:
            radio_slot_id = None
            print(LEVEL_2_TEST.format(test_name=interface.name))

            # Get the NetBox radio info
            nb_radio_details = parse_netbox_rf_channel(interface.rf_channel.value)
            nb_radio_details.update({"enabled": interface.enabled})
            radio_slot_id = interface.name.replace("radio", "")

            for wlc_radio in wlc_radio_config:
                ap_slot_freq = nb_radio_details['radio_band']
                if wlc_radio.get("slot-id", False) == int(radio_slot_id):
                    radio_leaf_name = f"radio-params-{ap_slot_freq}ghz"
                    wlc_radio_params = wlc_radio[radio_leaf_name]

                    wlc_radio_channel = wlc_radio_params.get(
                        "channel", WIRELESS_DEFAULTS[ap_slot_freq]["channel"]
                    )
                    wlc_channel_width = wlc_radio_params.get(
                        "channel-width", WIRELESS_DEFAULTS[ap_slot_freq]["channel_width"]
                    )
                    wlc_tx_power = wlc_radio_params.get(
                        "transmit-power", WIRELESS_DEFAULTS[ap_slot_freq]["tx_power"]
                    )
                    wlc_admin_state = wlc_radio_params.get(
                        "admin-state", WIRELESS_DEFAULTS[ap_slot_freq]["admin_state"]
                    )

                    # DCA and DTP enabled by default...
                    wlc_dtp_enabled = wlc_radio_params.get("dtp", True)
                    wlc_dca_enabled = wlc_radio_params.get("dca", True)

                    print(LEVEL_3_TEST.format(
                        test_name=f"Channel {nb_radio_details['channel']}"), end=""
                    )
                    if int(nb_radio_details.get("channel", 999)) == int(wlc_radio_channel):
                        print("OK")
                    else:
                        print(f"Configured: {wlc_radio_channel}. FAILED")

                    print(LEVEL_3_TEST.format(
                        test_name=f"Channel width {nb_radio_details['channel_width']}"), end=""
                    )
                    if int(nb_radio_details.get("channel_width", 20)) == int(wlc_channel_width):
                        print("OK")
                    else:
                        print(f"Configured: {wlc_channel_width}. FAILED")

                    print(LEVEL_3_TEST.format(
                        test_name=f"TX Power {interface.tx_power}"), end=""
                    )
                    if int(interface.tx_power) == int(wlc_tx_power):
                        print("OK")
                    else:
                        print(f"Configured: {wlc_tx_power}. FAILED")

                    print(LEVEL_3_TEST.format(
                        test_name="DCA Disabled"), end=""
                    )
                    if not wlc_dca_enabled:
                        print("OK")
                    else:
                        print("FAILED")

                    print(LEVEL_3_TEST.format(
                        test_name="DTP Disabled"), end=""
                    )
                    if not wlc_dtp_enabled:
                        print("OK")
                    else:
                        print("FAILED")

                    print(LEVEL_3_TEST.format(
                        test_name="Admin state"), end=""
                    )
                    if nb_radio_details.get("enabled", True) is wlc_admin_state:
                        print("OK")
                    else:
                        print("FAILED")
                    break
