"""
Import a CSV file into NetBox for Wireless Devices.
"""
import csv
import argparse
import os
import pynetbox
from pynetbox.core.query import RequestError

MORE_OUTPUT = True

parser = argparse.ArgumentParser()
parser.add_argument(
    "--no-update",
    dest="update_mode",
    default=True,
    action="store_false",
    help="Disable update mode (changes in CSV will not result in object updates)",
)

parser.add_argument(
    "-c",
    "--csv-file",
    dest="csv_file",
    default="netbox-import.csv",
    action="store",
    help="CSV file to import.  Default: netbox-import.csv",
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

# If UPDATE_MODE is True, changes in an existing CSV file will bg applied to
# existing devices.  Otherwise, existing objects will be skipped with no update
UPDATE_MODE = script_args.update_mode

# Set the CSV file to open based on the --csv-file parameter or its default
CSV_FILE = script_args.csv_file

# Set the default NetBox URL based on --netbox-url parameter or its default
NETBOX_URL = script_args.netbox_url

# Set the NetBox token to the environment variable NETBOX_TOKEN if present.
# Otherwise use a default development token
NETBOX_TOKEN = os.environ.get("NETBOX_TOKEN", "0123456789abcdef0123456789abcdef01234567")

# Initialize the pynetbox API object
nb = pynetbox.api(NETBOX_URL, token=NETBOX_TOKEN)


def generate_device_details(csv_row):
    """
    Given a row from the CSV file, create a dictionary suitable for import into
    NetBox to create a device.

    :param csv_row: The current row of the CSV file to process
    :return: Dict containing NetBox attributes required for device creation.
    """
    # Map CSV columns to DCIM attributes
    csv_to_dcim_map = {
        "device_name": "name",
        "serial": "serial",
        "asset_tag": "asset_tag",
        "device_type": "device_type",
        "device_role": "device_role",
        "platform": "platform",
        "site": "site",
        "location": "location",
    }

    # Map CSV columns to DCIM custom fields
    csv_to_dcim_custom_field_map = {
        "primary_wlc": "wlc_primary_association",
        "secondary_wlc": "wlc_secondary_association",
        "tertiaty_wlc": "wlc_tertiary_association",
    }

    # DCIM key fields will NOT use a NetBox object reference via "slug" value
    dcim_key_fields = ["name", "serial", "asset_tag"]

    print(f"Processing device '{csv_row['device_name']}'...")

    # For each expected / valid CSV field and associated DCIM field, check if
    # there is a CSV value and update the device_details dictionary.
    # If the associated DCIM field is a key field, use the raw value and don't
    # set the value to the NetBox 'slug'
    device_details = {}
    for csv_field, dcim_object_attr in csv_to_dcim_map.items():
        if csv_attr := csv_row.get(csv_field):
            if dcim_object_attr in dcim_key_fields:
                device_details.update({dcim_object_attr: csv_attr})
            else:
                device_details.update({dcim_object_attr: {"slug": csv_attr}})

    # Perform the same iteration as above, but for each custom field.  This is
    # specifically designed ONLY for WLC association objects for our use case,
    # so get the associated NetBox object ID for the WLC name.
    #
    # NOTE: WLC association is case-sensitive; must match the name of the WLC
    # as defined in NetBox.
    custom_fields = {}
    for csv_field, dcim_custom_object_attr in csv_to_dcim_custom_field_map.items():
        if csv_attr := csv_row.get(csv_field):
            wlc_device = nb.dcim.devices.get(name=csv_attr)
            try:
                custom_fields.update({dcim_custom_object_attr: wlc_device.id})
            except AttributeError:
                print(
                    f"ERROR: During import of field '{csv_field}'\n"
                    f"\tDesired WLC association '{csv_attr}' is not a valid NetBox device name."
                )

    # Add the custom fields to the device_details dictionary
    device_details.update({"custom_fields": custom_fields})

    # Input validation: remove keys that don't have values so no unexpected
    # values are imported
    device_details = {k: v for k, v in device_details.items() if v}

    return device_details


def generate_interface_details(device_name, csv_row):
    """
    Given a device name and a row from a CSV file, generate a dictionary
    with attributes required to create (or update) an interface associated
    with the NetBox device name

    :param device_name: Name of the device to associate interfaces
    :param csv_row: The current row of the CSV to process
    :return: Dict containing NetBox attributes required for interface creation.
    """

    # Anything in this list will be checked against the CSV row values by
    # appending the expected field name to an interface prefix.
    valid_interface_prefixes = [
        "wired",
        "wired1",
        "wired2",
        "radio0",
        "radio1",
        "radio2",
        "radio3",
    ]

    # Map CSV columns to DCIM attributes
    csv_to_dcim_map = {
        "mac": "mac_address",
        "radio_type": "type",
        "role": "rf_role",
        "tx_power": "tx_power",
        "channel_width": "rf_channel_width",
    }

    # Map CSV fields to NetBox custom fields
    csv_to_dcim_custom_field_map = {
        "band": "wifi_radio_band",
        "channel_number": "wifi_radio_channel"
    }

    # Initialize the return which will be a list of interfaces to update
    interfaces = []
    print("\tCreating interface definitions...")
    for interface_type in valid_interface_prefixes:
        # Identify the current interface ID based on the name and associated
        # device name
        dcim_interface = nb.dcim.interfaces.get(name=interface_type, device=device_name)

        if dcim_interface:
            print(f"\t\tInterface '{dcim_interface.name}'... ", end="")

            # Key field: initialize the interface ID
            interface_details = {"id": dcim_interface.id}

            # Initialize the custom fields
            custom_fields = {}

            # For each expected / valid CSV field and associated DCIM field, check if
            # there is a CSV value and update the interface_details dictionary.
            # NOTE: No slugs needed for interface values; use raw data.
            for csv_field, dcim_object_attr in csv_to_dcim_map.items():
                if csv_attr := csv_row.get(f"{interface_type}_{csv_field}"):
                    interface_details.update({dcim_object_attr: csv_attr})

            # Again, process custom fields based on CSV headers
            for csv_field, dcim_custom_field in csv_to_dcim_custom_field_map.items():
                if csv_attr := csv_row.get(f"{interface_type}_{csv_field}"):
                    custom_fields.update({dcim_custom_field: csv_attr})

            # Update the custom fields for this device
            interface_details.update({"custom_fields": custom_fields})

            # Input validation: remove keys that don't have values so no unexpected
            # values are imported
            interface_details = {k: v for k, v in interface_details.items() if v}

            # Append to the list of interfaces
            interfaces.append(interface_details)

            print("OK")

    return interfaces


def create_or_update_device(device_detail_dict):
    """
    Create a new device in NetBox.  If the device already exists and the
    --no-update option has NOT been specified, this will update an existing
    device if already present.

    :param device_detail_dict: Dict containing device attributes for import
    :return: API result of creating or updating a device if successful.  None
        if the device exists and the --no-update parameter was passed OR if
        an error occurred during device creation/update.
    """
    nb_result = None

    try:
        print("\tChecking if device exists... ", end="")
        device_id = nb.dcim.devices.get(name=device_detail_dict["name"])

        # Device exists and update is enabled (default):
        if device_id and UPDATE_MODE:
            print("YES\n\t\tUpdating device... ", end="")
            device_detail_dict.update({"id": device_id.id})
            nb_result = nb.dcim.devices.update([device_detail_dict])
            print("OK")

        # Device exists but update is disabled via --no-update
        elif device_id and not UPDATE_MODE:
            print("SKIPPING - update mode disabled")
            nb_result = None

        # No device exists, create
        else:
            print("NO\n\t\tCreating device... ", end="")
            nb_result = nb.dcim.devices.create([device_detail_dict])
            print("OK")

    except RequestError as err_msg:  # Catch pynetbox API errors
        print(f"FAILED\n\t\tNetBox API error: {err_msg}")
    except KeyError as err_msg:  # Device name doesn't exist
        print(f"FAILED: Missing Key {err_msg} in device detail dictionary")

    return nb_result


if __name__ == "__main__":
    try:
        with open(CSV_FILE, "r", encoding="utf-8-sig") as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:

                if MORE_OUTPUT:
                    print("Reading CSV row:")
                    for column_heading, column_value in row.items():
                        print(f"{column_heading} = {column_value}")
                    print()

                # Generate the expected payload dictionary based on the CSV row
                device_detail = generate_device_details(row)

                # Create or update with the generated device details
                current_device = create_or_update_device(
                    device_detail_dict=device_detail
                )

                try:
                    # If a device is updated, a list must be passed as the API
                    # parameter, and a list is returned.  Since a row only
                    # has a single device to process, use the first index [0]
                    # to process interfaces on the current device.
                    device_interfaces = generate_interface_details(
                        device_name=current_device[0].name, csv_row=row
                    )
                    print("\tEditing interfaces...", end="")
                    iface_result = nb.dcim.interfaces.update(device_interfaces)
                except TypeError:  # nb_result is None - ignore and continue
                    pass
                else:
                    print("OK")

    except FileNotFoundError as err:
        print(f"Unable to open CSV file for import: {err}")
