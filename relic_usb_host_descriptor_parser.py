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
    """The base class of a descriptor parser. Validates descriptor data length and type. The
    constructor will throw a `ValueError` exception if the data is invalid.

    :param descriptor: The descriptor data to validate.
    :type descriptor: `bytearray`
    :param length: The length of the descriptor data.
    :type length: `int`, optional
    :param descriptor_type: The type of the descriptor data.
    :type descriptor_type: `int`, optional
    """

    def __init__(self, descriptor: bytearray, length: int = None, descriptor_type: int = None):
        if (
            (length is not None and len(descriptor) < length)
            or descriptor[0] != len(descriptor)
            or (descriptor_type is not None and descriptor[1] != descriptor_type)
        ):
            raise ValueError("Invalid descriptor format")


class EndpointDescriptor(Descriptor):
    """Parse the provided endpoint descriptor. This class should only be instantiated by
    :class:`ConfigurationDescriptor`.

    :param descriptor: The endpoint descriptor data to parse.
    :type descriptor: `bytearray`
    """

    def __init__(self, descriptor: bytearray):
        super().__init__(descriptor, 7, adafruit_usb_host_descriptors.DESC_ENDPOINT)
        self._address = descriptor[2]
        self._attributes = descriptor[3]
        self._max_packet_size = (descriptor[5] << 8) | descriptor[4]
        self._interval = descriptor[6]

    @property
    def address(self) -> int:
        """The endpoint address."""
        return self._address

    @property
    def attributes(self) -> int:
        """The attributes of the endpoint."""
        return self._attributes

    @property
    def max_packet_size(self) -> int:
        """The maximum expected packet size of a report from the endpoint in bytes."""
        return self._max_packet_size

    @property
    def interval(self) -> int:
        """The expected polling interval of an endpoint. If the device is low-speed or full-speed,
        the interval is in increments of 1ms. If the device is high-speed, the interval can be
        calculated using the formula: "2^(interval-1) * 125 µs".
        """
        return self._interval

    @property
    def input(self) -> bool:
        """Whether or not this endpoint is used for input data."""
        return bool(self._address & 0x80)

    @property
    def output(self) -> bool:
        """Whether or not this endpoint is used for output data."""
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


class HIDDescriptor(Descriptor):
    """Parse the provided HID descriptor. This class should only be instantiated by
    :class:`ConfigurationDescriptor`.

    :param descriptor: The HID descriptor data to parse.
    :type descriptor: `bytearray`
    """

    def __init__(self, descriptor: bytearray, device: usb.core.Device, interface: int = 0):
        super().__init__(descriptor, 9, adafruit_usb_host_descriptors.DESC_HID)
        self._country = descriptor[4]
        self._count = descriptor[5]
        self._report_type = descriptor[6]
        self._report_length = (descriptor[8] << 8) | descriptor[7]

        # read usage id from report descriptor
        report_descriptor = adafruit_usb_host_descriptors.get_report_descriptor(
            device, interface, self._report_length
        )
        self._usage_page_id = None
        self._usage_id = None
        i = 0
        while i < len(report_descriptor):
            tag, value = report_descriptor[i : i + 2]
            i += 2
            if (
                tag == adafruit_usb_host_descriptors.HID_TAG_USAGE_PAGE
                and self._usage_page_id is None
            ):
                self._usage_page_id = value
            elif tag == adafruit_usb_host_descriptors.HID_TAG_USAGE and self._usage_id is None:
                self._usage_id = value
                break

    @property
    def country(self) -> int:
        """The country of the HID descriptor."""
        return self._country

    @property
    def count(self) -> int:
        """The count of the HID descriptor."""
        return self._count

    @property
    def report_type(self) -> int:
        """The type of the HID report descriptor."""
        return self._report_type

    @property
    def report_length(self) -> int:
        """The length of the HID report derscriptor."""
        return self._report_length

    @property
    def usage_page_id(self) -> int:
        """The ID of the first HID usage page."""
        return self._usage_page_id

    @property
    def usage_id(self) -> int:
        """The ID of the first HID usage."""
        return self._usage_id

    def __str__(self):
        return str(
            {
                "country": hex(self._country),
                "count": hex(self._count),
                "report_type": hex(self._report_type),
                "report_length": self._report_length,
                "usage_page_id": self._usage_page_id,
                "usage_id": self._usage_id,
            }
        )


class InterfaceDescriptor(Descriptor):
    """Parse the provided interface descriptor. This class should only be instantiated by
    :class:`ConfigurationDescriptor`.

    :param descriptor: The interface descriptor data to parse.
    :type descriptor: `bytearray`
    """

    def __init__(self, descriptor: bytearray):
        super().__init__(descriptor, 9, adafruit_usb_host_descriptors.DESC_INTERFACE)
        self._index = descriptor[2]
        self._num_endpoints = descriptor[4]
        self._interface_class = descriptor[5]
        self._interface_subclass = descriptor[6]
        self._protocol = descriptor[7]
        self._endpoints = []
        self._hid_descriptor = None

    def _append_endpoint(self, descriptor: bytearray) -> None:
        self._endpoints.append(EndpointDescriptor(descriptor))

    @property
    def index(self) -> int:
        """The number of the interface in the usb device configuration."""
        return self._index

    @property
    def interface_class(self) -> int:
        """The class specification of the interface."""
        return self._interface_class

    @property
    def interface_subclass(self) -> int:
        """The subclass specification of the interface."""
        return self._interface_subclass

    @property
    def protocol(self) -> int:
        """The interface protocol."""
        return self._protocol

    @property
    def endpoints(self) -> tuple:
        """A `tuple` of the descriptors for the endpoints utilized by this interface."""
        return tuple(self._endpoints)

    @property
    def in_endpoint(self) -> EndpointDescriptor:
        """The first endpoint designated as an input within the interface."""
        try:
            return next(x for x in self._endpoints if x.input)
        except StopIteration:
            return None

    @property
    def out_endpoint(self) -> EndpointDescriptor:
        """The first endpoint designated as an output within the interface."""
        try:
            return next(x for x in self._endpoints if x.output)
        except StopIteration:
            return None

    @property
    def hid_descriptor(self) -> HIDDescriptor:
        """The HID descriptor of the interface if it is an HID-compliant interface. Otherwise,
        this property will be `None`."""
        return self._hid_descriptor

    def get_class_identifier(self) -> tuple:
        """A `tuple` containing the class and subclass of the interface."""
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
    """Fetch and parse the specified configuration descriptor and its interface and endpoint
    descriptors from a device.

    :param device: The USB device to fetch descriptors from.
    :type device: :class:`usb.core.Device`
    :param configuration: The zero-based index of the device configuration to fetch. Defaults to 0.
    :type configuration: `int`, optional
    """

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
                descriptor_type == adafruit_usb_host_descriptors.DESC_HID
                and self._interfaces[interface_index].interface_class
                == adafruit_usb_host_descriptors.INTERFACE_HID
            ):
                self._interfaces[interface_index]._hid_descriptor = HIDDescriptor(
                    descriptor, device, interface_index
                )

            elif (
                descriptor_type == adafruit_usb_host_descriptors.DESC_ENDPOINT
                and interface_index is not None
            ):
                self._interfaces[interface_index]._append_endpoint(descriptor)

            i += descriptor_len

        self._interfaces = tuple(self._interfaces)

    @property
    def value(self) -> int:
        """The configuration value which indicates the number for the configuration defined in the
        firmware of the device.
        """
        return self._value

    @property
    def max_power(self) -> int:
        """The maximimum power in milliamps that the device can draw from the host."""
        return self._max_power * 2  # units are 2 mA

    @property
    def interfaces(self) -> tuple:
        """A `tuple` of the descriptors for the interfaces utilized by this configuration."""
        return self._interfaces

    def get_class_identifier(self, interface: int = 0):
        """A `tuple` containing the class and subclass of an interface within this configuration.

        :param interface: The index of the desired interface. Defaults to 0.
        :type interface: `int`, optional
        """
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
    """Fetch and parse all device, configuration, interface, and endpoint descriptors.

    :param device: The USB device to fetch descriptors from.
    :type device: :class:`usb.core.Device`
    """

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
        """The class specification of the device."""
        return self._device_class

    @property
    def device_subclass(self) -> int:
        """The subclass specification of the device."""
        return self._device_subclass

    @property
    def protocol(self) -> int:
        """The device protocol."""
        return self._protocol

    @property
    def max_packet_size(self) -> int:
        """The maximum expected packet size of a report from the default endpoint in bytes."""
        return self._max_packet_size

    @property
    def configurations(self) -> tuple:
        """A `tuple` of the descriptors for the configurations as :class:`ConfigurationDescriptor`
        objects offered by this device."""
        return self._configurations

    def get_class_identifier(self, configuration: int = 0, interface: int = 0) -> tuple:
        """A `tuple` of 4 `int` elements containing the class and subclass of this device as well as
        the class and subclass of the designated configuration and interface.

        :param configuration: The index of the desired device configuration. Defaults to 0.
        :type configuration: `int`, optional
        :param interface: The index of the desired interface within the configuration.
            Defaults to 0.
        :type interface: `int`, optional
        """
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
