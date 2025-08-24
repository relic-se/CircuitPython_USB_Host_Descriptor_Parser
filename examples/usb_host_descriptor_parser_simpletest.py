# SPDX-FileCopyrightText: Copyright (c) 2025 Cooper Dalrymple
#
# SPDX-License-Identifier: Unlicense
import usb.core

from relic_usb_host_descriptor_parser import DeviceDescriptor

for i, device in enumerate(usb.core.find(find_all=True)):
    device_descriptor = DeviceDescriptor(device)
    print(f"Device {i+1}: {device_descriptor}")
    for j, configuration in enumerate(device_descriptor.configurations):
        print(f"- Configuration {j+1}: {configuration}")
        for k, interface in enumerate(configuration.interfaces):
            print(f"  - Interface {k+1}: {interface}")
            for l, endpoint in enumerate(interface.endpoints):
                print(f"    - Endpoints {l+1}: {endpoint}")
    print()
