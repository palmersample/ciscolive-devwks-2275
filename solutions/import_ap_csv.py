"""
Import a CSV file into NetBox for Wireless Devices.
"""
# pylint: disable=loop-global-usage
import csv
import argparse
import os
import pynetbox
from helpers import (generate_device_details,
                     update_interfaces,
                     create_or_update_device)


# Set the NetBox URL to the environment variable created during setup.
NETBOX_URL = os.environ.get("NETBOX_URL")

# Set the NetBox token to the environment variable created during setup.
NETBOX_TOKEN = os.environ.get("NETBOX_TOKEN")

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

    try:
        with open(csv_file, "r", encoding="utf-8-sig") as csvfile:
            reader = csv.DictReader(csvfile)

            print("*" * 78)
            for row in reader:
                # Uncomment the following lines if more detail is desired:
                # print("Reading CSV row:")
                # for column_heading, column_value in row.items():
                #     print(f"{column_heading} = {column_value}")
                # print()

                # Generate the expected payload dictionary based on the CSV row
                device_detail = generate_device_details(netbox_api=netbox, csv_row=row)

                # Create or update with the generated device details
                current_device = create_or_update_device(netbox_api=netbox,
                                                         device_detail_dict=device_detail)
                if current_device is not None:
                    # The device was created or updated, now update the
                    # interface details.
                    print("\t\tUpdating interfaces for this device...")
                    update_interfaces(netbox_api=netbox,
                                      device_object=current_device,
                                      csv_row=row)

                print("*" * 78)

    except FileNotFoundError as err:
        print(f"Unable to open CSV file for import: {err}")
