# SPDX-FileCopyrightText: Copyright (c) 2025 Cooper Dalrymple
#
# SPDX-License-Identifier: MIT
"""
`relic_usb_host_descriptor_parser`
================================================================================

Helper to parse USB descriptors


* Author(s): Cooper Dalrymple

Implementation Notes
--------------------

**Hardware:**

* `Adafruit Fruit Jam - Mini RP2350 Computer <https://www.adafruit.com/product/6200>`_

* `Adafruit Feather RP2040 with USB Type A Host <https://www.adafruit.com/product/5723>`_

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

* Adafruit's USB Host Descriptors library:
  https://github.com/adafruit/Adafruit_CircuitPython_USB_Host_Descriptors

"""

# imports

__version__ = "0.0.0+auto.0"
__repo__ = "https://github.com/relic-se/CircuitPython_USB_Host_Descriptor_Parser.git"

import adafruit_usb_host_descriptors
import usb.core


class Descriptor:
    def __init__(self, descriptor: bytearray, length: int = None, descriptor_type: int = None):
        if (
            (length is not None and len(descriptor) != length)
            or descriptor[0] != len(descriptor)
            or (descriptor_type is not None and descriptor[1] != descriptor_type)
        ):
            raise ValueError("Invalid descriptor format")


class EndpointDescriptor(Descriptor):
    def __init__(self, descriptor: bytearray):
        super().__init__(descriptor, 7, adafruit_usb_host_descriptors.DESC_ENDPOINT)
        self._address = descriptor[2]
        self._attributes = descriptor[3]
        self._max_packet_size = (descriptor[5] << 8) | descriptor[4]
        self._interval = descriptor[6]

    @property
    def address(self) -> int:
        return self._address

    @property
    def attributes(self) -> int:
        return self._attributes

    @property
    def max_packet_size(self) -> int:
        return self._max_packet_size

    @property
    def interval(self) -> int:
        return self._interval

    @property
    def input(self) -> bool:
        return bool(self._address & 0x80)

    @property
    def output(self) -> bool:
        return not self.input

    def __str__(self):
        return str(
            {
                "address": hex(self._address),
                "attributes": hex(self._attributes),
                "max_packet_size": self._max_packet_size,
                "interval": self._interval,
                "input": self.input,
                "output": self.output,
            }
        )


class InterfaceDescriptor(Descriptor):
    def __init__(self, descriptor: bytearray):
        super().__init__(descriptor, 9, adafruit_usb_host_descriptors.DESC_INTERFACE)
        self._index = descriptor[2]
        self._num_endpoints = descriptor[4]
        self._interface_class = descriptor[5]
        self._interface_subclass = descriptor[6]
        self._protocol = descriptor[7]
        self._endpoints = []

    def append_endpoint(self, descriptor: bytearray) -> None:
        self._endpoints.append(EndpointDescriptor(descriptor))

    @property
    def index(self) -> int:
        return self._index

    @property
    def interface_class(self) -> int:
        return self._interface_class

    @property
    def interface_subclass(self) -> int:
        return self._interface_subclass

    @property
    def protocol(self) -> int:
        return self._protocol

    @property
    def endpoints(self) -> tuple:
        return tuple(self._endpoints)

    @property
    def in_endpoint(self) -> EndpointDescriptor:
        try:
            return next(x for x in self._endpoints if x.input)
        except StopIteration:
            return None

    @property
    def out_endpoint(self) -> EndpointDescriptor:
        try:
            return next(x for x in self._endpoints if x.output)
        except StopIteration:
            return None

    def get_class_identifier(self) -> tuple:
        return (self._interface_class, self._interface_subclass)

    def __str__(self):
        return str(
            {
                "class": hex(self._interface_class),
                "subclass": hex(self._interface_subclass),
                "protocol": hex(self._protocol),
                "endpoints": self._num_endpoints,
            }
        )


class ConfigurationDescriptor(Descriptor):
    def __init__(self, device: usb.core.Device, configuration: int = 0):
        config_descriptor = adafruit_usb_host_descriptors.get_configuration_descriptor(
            device, configuration
        )

        self._interfaces = []

        interface_index = None
        i = 0
        while i < len(config_descriptor):
            descriptor_len, descriptor_type = config_descriptor[i : i + 2]
            descriptor = config_descriptor[i : i + descriptor_len]

            if descriptor_type == adafruit_usb_host_descriptors.DESC_CONFIGURATION:
                super().__init__(descriptor, 9, adafruit_usb_host_descriptors.DESC_CONFIGURATION)
                self._num_interfaces = descriptor[4]
                self._value = descriptor[5]  # for set_configuration()
                self._max_power = descriptor[8]

            elif descriptor_type == adafruit_usb_host_descriptors.DESC_INTERFACE:
                interface_index = len(self._interfaces)
                self._interfaces.append(InterfaceDescriptor(descriptor))

            elif (
                descriptor_type == adafruit_usb_host_descriptors.DESC_ENDPOINT
                and interface_index is not None
            ):
                self._interfaces[interface_index].append_endpoint(descriptor)

            i += descriptor_len

        self._interfaces = tuple(self._interfaces)

    @property
    def value(self) -> int:
        return self._value

    @property
    def max_power(self) -> int:
        return self._max_power * 2  # units are 2 mA

    @property
    def interfaces(self) -> tuple:
        return self._interfaces

    def get_class_identifier(self, interface: int = 0):
        return self._interfaces[interface].get_class_identifier()

    def __str__(self):
        return str(
            {
                "value": hex(self._value),
                "max_power": f"{self.max_power} mA",
                "interfaces": self._num_interfaces,
            }
        )


class DeviceDescriptor:
    def __init__(self, device: usb.core.Device):
        descriptor = adafruit_usb_host_descriptors.get_device_descriptor(device)
        self._device_class = descriptor[4]
        self._device_subclass = descriptor[5]
        self._protocol = descriptor[6]
        self._max_packet_size = descriptor[7]
        self._num_configurations = descriptor[17]
        self._configurations = tuple(
            [ConfigurationDescriptor(device, i) for i in range(self._num_configurations)]
        )

    @property
    def device_class(self) -> int:
        return self._device_class

    @property
    def device_subclass(self) -> int:
        return self._device_subclass

    @property
    def protocol(self) -> int:
        return self._protocol

    @property
    def max_packet_size(self) -> int:
        return self._max_packet_size

    @property
    def configurations(self) -> tuple:
        return self._configurations

    def get_class_identifier(self, configuration: int = 0, interface: int = 0) -> tuple:
        return (self.device_class, self.device_subclass) + self._configurations[
            configuration
        ].get_class_identifier(interface)

    def __str__(self):
        return str(
            {
                "class": hex(self._device_class),
                "subclass": hex(self._device_subclass),
                "protocol": hex(self._protocol),
                "max_packet_size": self._max_packet_size,
                "configurations": self._num_configurations,
            }
        )
