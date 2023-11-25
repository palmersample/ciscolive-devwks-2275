"""
CSV import helper functions - decouple tasks from the main entrypoint.
"""
# pylint: disable=loop-invariant-statement
from pynetbox.core.query import RequestError
from .rf_channel_map import get_rf_channel_value


def generate_device_details(netbox_api, csv_row):
    """
    Given a row from the CSV file, create a dictionary suitable for import into
    NetBox to create a device.

    :param netbox_api: pynetbox API object reference
    :param csv_row: The current row of the CSV file to process
    :return: Dict containing NetBox attributes required for device creation.
    """
    # Map CSV columns to DCIM attributes
    device_key_field_map = {
        "device_name": "name",
        "serial": "serial",
        "asset_tag": "asset_tag",
        "device_type": "device_type",
        "device_role": "role",
        "platform": "platform",
        "site": "site",
        "location": "location",
    }

    # Map CSV columns to DCIM custom fields
    device_custom_field_map = {
        "primary_wlc": "wlc_primary_association",
        "secondary_wlc": "wlc_secondary_association",
        "tertiary_wlc": "wlc_tertiary_association",
    }

    # DCIM key fields will NOT use a NetBox object reference via "slug" value
    dcim_native_fields = ("name", "serial", "asset_tag")

    print(f"Processing device '{csv_row['device_name']}'...")

    # For each expected / valid CSV field and associated DCIM field, check if
    # there is a CSV value and update the device_details dictionary.
    # If the associated DCIM field is a key field, use the raw value and don't
    # set the value to the NetBox 'slug'
    device_details = {}
    for csv_field, dcim_object_attr in device_key_field_map.items():
        if csv_attr := csv_row.get(csv_field):
            if dcim_object_attr in dcim_native_fields:
                device_details.update({dcim_object_attr: csv_attr})
            else:
                device_details.update({dcim_object_attr: {"slug": csv_attr}})
            csv_row.pop(csv_field)

    # Perform the same iteration as above, but for each custom field.  This is
    # specifically designed ONLY for WLC association objects for our use case,
    # so get the associated NetBox object ID for the WLC name.
    #
    # NOTE: WLC association is case-sensitive; must match the name of the WLC
    # as defined in NetBox.
    custom_fields = {}
    for csv_field, dcim_custom_object_attr in device_custom_field_map.items():
        if csv_attr := csv_row.get(csv_field):
            associated_wlc = netbox_api.dcim.devices.get(name=csv_attr)
            try:  # pylint: disable=loop-try-except-usage
                custom_fields.update({dcim_custom_object_attr: associated_wlc.id})
            except AttributeError:
                print(
                    f"ERROR: During import of field '{csv_field}'\n"
                    f"\tDesired WLC association '{csv_attr}' is not a valid NetBox device name."
                )
            csv_row.pop(csv_field)

    # Add the custom fields to the device_details dictionary
    device_details.update({"custom_fields": custom_fields})

    # Input validation: remove keys that don't have values so no unexpected
    # values are imported
    device_details = {k: v for k, v in device_details.items() if v}

    return device_details


def update_interfaces(netbox_api, device_object, csv_row):
    """
    Given a device name and a row from a CSV file, generate a dictionary
    with attributes required to create (or update) an interface associated
    with the NetBox device name and then update via pynetbox API.

    :param netbox_api: pynetbox API object reference
    :param device_object: pynetbox object reference for the current device
    :param csv_row: The current row of the CSV to process
    :return: Dict containing NetBox attributes required for interface creation.
    """

    # Anything in this list will be checked against the CSV row values by
    # appending the expected field name to an interface prefix.
    valid_interface_names = (
        "wired",
        "wired1",
        "wired2",
        "radio0",
        "radio1",
        "radio2",
        "radio3",
    )

    interface_key_field_map = {
        "mac": "mac_address",
        "band": "band",
        "channel_number": "channel",
        "rf_role": "rf_role",
        "tx_power": "tx_power",
        "channel_width": "rf_channel_width",
        "enabled": "enabled"
    }

    # Get the device interfaces
    device_interfaces = netbox_api.dcim.interfaces.filter(device=device_object)

    # Initialize an empty list to store all interface details
    interfaces = []

    # Process each interface
    for current_interface in device_interfaces:

        # Valid interface name? Proceed!
        if current_interface.name in valid_interface_names:
            interface_details = {"id": current_interface.id}

            # Convert the CSV fields to NetBox attributes.
            for csv_field, dcim_object_attr in interface_key_field_map.items():

                # If there is a CSV column matching the field, process it:
                if csv_attr := csv_row.get(f"{current_interface}_{csv_field}"):
                    interface_details.update({dcim_object_attr: csv_attr})
                    csv_row.pop(f"{current_interface}_{csv_field}")

            # Is this a radio interface? If so, convert the RF params
            # to a value that NetBox expects.
            if current_interface.name.lower().startswith("radio"):
                get_rf_channel_value(interface_details)

            interfaces.append(interface_details)
    iface_result = netbox_api.dcim.interfaces.update(interfaces)
    print(f"\t\tInterfaces updated: {iface_result}")
    return interfaces


def create_or_update_device(netbox_api, device_detail_dict):
    """
    Create a new device in NetBox.  If the device already exists and the
    --no-update option has NOT been specified, this will update an existing
    device if already present.

    :param netbox_api: pynetbox API object reference
    :param device_detail_dict: Dict containing device attributes for import
    :return: API result of creating or updating a device if successful.  None
        if the device exists and the --no-update parameter was passed OR if
        an error occurred during device creation/update.
    """
    device_object = None

    try:
        print("\tChecking if device exists... ", end="")
        device_id = netbox_api.dcim.devices.get(name=device_detail_dict["name"])

        # Device exists and update is enabled (default):
        if device_id:
            print("YES\n\t\tUpdating device... ", end="")
            device_detail_dict.update({"id": device_id.id})
            nb_result = netbox_api.dcim.devices.update([device_detail_dict])
            print("OK")

        # No device exists, create
        else:
            print("NO\n\t\tCreating device... ", end="")
            nb_result = netbox_api.dcim.devices.create([device_detail_dict])
            print("OK")

    except RequestError as err_msg:  # Catch pynetbox API errors
        print(f"FAILED\n\t\tNetBox API error: {err_msg}")
    except KeyError as err_msg:  # Device name doesn't exist
        print(f"FAILED: Missing Key {err_msg} in device detail dictionary")
    else:
        device_object = nb_result[0]

    return device_object
