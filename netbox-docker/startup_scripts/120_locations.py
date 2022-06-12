import sys

from dcim.models import Location, Site
from startup_script_utils import load_yaml

rack_groups = load_yaml("/opt/netbox/initializers/locations.yml")

if rack_groups is None:
    sys.exit()

optional_assocs = {"site": (Site, "name"), "parent": (Location, "name")}

for params in rack_groups:

    for assoc, details in optional_assocs.items():
        if assoc in params:
            model, field = details
            query = {field: params.pop(assoc)}

            params[assoc] = model.objects.get(**query)

    region, created = Location.objects.get_or_create(**params)

    if created:
        print("🌐 Created region", region.name)

#
# if rack_groups is None:
#     sys.exit()
#
# required_assocs = {"site": (Site, "name")}
#
# for params in rack_groups:
#
#     for assoc, details in required_assocs.items():
#         model, field = details
#         query = {field: params.pop(assoc)}
#         params[assoc] = model.objects.get(**query)
#
#     location, created = Location.objects.get_or_create(**params)
#
#     if created:
#         print("🎨 Created location", location.name)
