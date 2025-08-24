# SPDX-FileCopyrightText: Copyright (c) 2025 Cooper Dalrymple
#
# SPDX-License-Identifier: Unlicense
import usb.core

from relic_usb_host_descriptor_parser import DeviceDescriptor

for device in usb.core.find(find_all=True):
    device_descriptor = DeviceDescriptor(device)
    print("# Device")
    print(device_descriptor)
    print("## Configurations")
    for configuration in device_descriptor.configurations:
        print(configuration)
        print("### Interfaces")
        for interface in configuration.interfaces:
            print(interface)
            print("#### Endpoints")
            for endpoint in interface.endpoints:
                print(endpoint)
