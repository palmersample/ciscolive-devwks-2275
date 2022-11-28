"""
Package init for helper functions
"""
# pylint: disable=use-tuple-over-list

from .request_helpers import create_request_session

from .import_helpers import (generate_device_details,
                             update_interfaces,
                             create_or_update_device)

from .wlc_helpers import (provision_ap_on_wlc,
                          provision_ap_radios,
                          get_ap_wlc_associations)

# from .rf_channel_map import (get_rf_channel_value,
#                              parse_netbox_rf_channel)

__all__ = [
    "generate_device_details",
    "update_interfaces",
    "create_or_update_device",
    "provision_ap_on_wlc",
    "provision_ap_radios",
    "get_ap_wlc_associations",
    "create_request_session",
]
