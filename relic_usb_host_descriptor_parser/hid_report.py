# SPDX-FileCopyrightText: Copyright (c) 2025 Cooper Dalrymple
#
# SPDX-License-Identifier: MIT

"""
Resources:
- https://github.com/usb-tools/python-hid-parser/blob/main/hid_parser/__init__.py#L823
- https://usb.org/sites/default/files/hut1_6.pdf
- https://docs.kernel.org/hid/hidintro.html
- https://www.usb.org/sites/default/files/hid1_11.pdf
"""

# imports

from micropython import const
import struct

try:
    from typing import Generator
except ImportError:
    pass

# HID constants

_HID_TYPE_MAIN = const(0)
_HID_TYPE_GLOBAL = const(1)
_HID_TYPE_LOCAL = const(2)

_HID_TAG_MAIN_INPUT = const(0b1000)
_HID_TAG_MAIN_OUTPUT = const(0b1001)
_HID_TAG_MAIN_FEATURE = const(0b1011)
_HID_TAG_MAIN_COLLECTION = const(0b1010)
_HID_TAG_MAIN_END_COLLECTION = const(0b1100)

_HID_TAG_GLOBAL_USAGE_PAGE = 0b0000
_HID_TAG_GLOBAL_LOGICAL_MINIMUM = 0b0001
_HID_TAG_GLOBAL_LOGICAL_MAXIMUM = 0b0010
_HID_TAG_GLOBAL_PHYSICAL_MINIMUM = 0b0011
_HID_TAG_GLOBAL_PHYSICAL_MAXIMUM = 0b0100
_HID_TAG_GLOBAL_UNIT_EXPONENT = 0b0101
_HID_TAG_GLOBAL_UNIT = 0b0110
_HID_TAG_GLOBAL_REPORT_SIZE = 0b0111
_HID_TAG_GLOBAL_REPORT_ID = 0b1000
_HID_TAG_GLOBAL_REPORT_COUNT = 0b1001
_HID_TAG_GLOBAL_PUSH = 0b1010
_HID_TAG_GLOBAL_POP = 0b1011

_HID_TAG_GLOBAL_SIGNED_TAGS = (
    _HID_TAG_GLOBAL_LOGICAL_MINIMUM,
    _HID_TAG_GLOBAL_LOGICAL_MAXIMUM,
    _HID_TAG_GLOBAL_PHYSICAL_MINIMUM,
    _HID_TAG_GLOBAL_PHYSICAL_MAXIMUM,
    _HID_TAG_GLOBAL_UNIT_EXPONENT,
)

_HID_TAG_LOCAL_USAGE = 0b0000
_HID_TAG_LOCAL_USAGE_MINIMUM = 0b0001
_HID_TAG_LOCAL_USAGE_MAXIMUM = 0b0010
_HID_TAG_LOCAL_DESIGNATOR_INDEX = 0b0011
_HID_TAG_LOCAL_DESIGNATOR_MINIMUM = 0b0100
_HID_TAG_LOCAL_DESIGNATOR_MAXIMUM = 0b0101
_HID_TAG_LOCAL_STRING_INDEX = 0b0111
_HID_TAG_LOCAL_STRING_MINIMUM = 0b1000
_HID_TAG_LOCAL_STRING_MAXIMUM = 0b1001
_HID_TAG_LOCAL_DELIMITER = 0b1010


class Item:

    def __init__(self, offset: int, size: int):
        self._offset = offset  # in bits
        self._size = size  # in bits

    @property
    def offset(self) -> int:
        return self._offset

    @property
    def size(self) -> int:
        return self._size
    

class PaddingItem(Item):
    pass


class ArrayItem(Item):

    def __init__(self, offset: int, size: int, usages: list, report_count: int, flags: int):
        pass


class VariableItem(Item):

    def __init__(self, offset: int, size: int, usage: int, flags: int):
        pass


class Usage:
    def __init__(self, usage_page: int, data: int):
        pass


class Descriptor:

    def __init__(self, descriptor: bytearray):
        self._offset = {
            _HID_TAG_MAIN_INPUT: {},
            _HID_TAG_MAIN_OUTPUT: {},
            _HID_TAG_MAIN_FEATURE: {},
        }
        self._pool = {
            _HID_TAG_MAIN_INPUT: {},
            _HID_TAG_MAIN_OUTPUT: {},
            _HID_TAG_MAIN_FEATURE: {},
        }

        report_id = None
        report_count = None
        report_size = None

        usage_page = None
        usages = []
        usage_min = None
        glob = {}
        local = {}

        for typ, tag, data in self._iterate():
            if typ == _HID_TYPE_MAIN:
                if tag in (_HID_TAG_MAIN_COLLECTION, _HID_TAG_MAIN_END_COLLECTION):
                    usages = []
                
                if tag not in (_HID_TAG_MAIN_INPUT, _HID_TAG_MAIN_OUTPUT, _HID_TAG_MAIN_FEATURE):
                    continue

                if self._report_count is None or self._report_size is None or data is None:
                    raise ValueError("Invalid report")
                
                self._append_items(
                    tag,
                    report_id,
                    report_count,
                    report_size,
                    usages,
                    data
                )

                # reset
                usages = []
                usage_min = None
                local = {}

            elif typ == _HID_TYPE_GLOBAL:
                if tag == _HID_TAG_GLOBAL_USAGE_PAGE:
                    usage_page = data

                elif tag in (_HID_TAG_GLOBAL_LOGICAL_MINIMUM, _HID_TAG_GLOBAL_LOGICAL_MAXIMUM, _HID_TAG_GLOBAL_PHYSICAL_MINIMUM, _HID_TAG_GLOBAL_PHYSICAL_MAXIMUM):
                    glob[tag] = data

                elif tag == _HID_TAG_GLOBAL_REPORT_SIZE:
                    report_size = data

                elif tag == _HID_TAG_GLOBAL_REPORT_ID:
                    if not report_id and any(self._pool[x] for x in self._pool):
                        raise ValueError("Report ID defined on invalid report")
                    report_id = data
                    # initialize item offsets
                    for x in self._offset:
                        self._offset[x][report_id] = 0

                elif tag in (_HID_TAG_GLOBAL_UNIT, _HID_TAG_GLOBAL_UNIT_EXPONENT):
                    pass  # not supported

                elif tag == _HID_TAG_GLOBAL_REPORT_COUNT:
                    report_count = data

                else:
                    raise NotImplementedError(f"Unsupported global tag: {bin(tag)}")

            elif typ == _HID_TYPE_LOCAL:
                if tag == _HID_TAG_LOCAL_USAGE:
                    if usage_page is None:
                        raise ValueError("Usage defined before page")
                    usages.append(Usage(usage_page, data))

                elif tag == _HID_TAG_LOCAL_USAGE_MINIMUM:
                    usage_min = data

                elif tag == _HID_TAG_LOCAL_USAGE_MAXIMUM:
                    if usage_min is None:
                        raise ValueError("Usage maximum defined before minimum")
                    if data is None:
                        raise ValueError("Invalid usage maximum")
                    for i in range(usage_min, data + 1):
                        usages.append(Usage(usage_page, i))
                    usage_min = None

                elif tag in (_HID_TAG_LOCAL_STRING_INDEX, _HID_TAG_LOCAL_STRING_MINIMUM, _HID_TAG_LOCAL_STRING_MAXIMUM):
                    pass

                else:
                    raise NotImplementedError(f"Unsupported local tag: {bin(tag)}")

    def _append_item(self, tag: int, report_id: int, item: Item):
        self._offset[report_id] += item.size
        if report_id not in self._pool[tag]:
            self._pool[tag][report_id] = []
        self._pool[tag][report_id].append(item)

    def _append_items(self, tag: int, report_id: int, report_count: int, report_size: int, usages: list, flags: int):
        if len(usages) == 0 or not usages:
            for i in range(report_count):
                self._append_item(tag, report_id, PaddingItem(self._offset[tag][report_id], report_size))

        elif not (flags & 0b10):
            self._append_item(tag, report_id, ArrayItem(self._offset[tag][report_id], report_size, usages, report_count, flags))
        
        else:
            if len(usages) > report_count:
                report_count = len(usages)
            elif len(usages) != report_count:
                usages += [] * (report_count - len(usages))
            for usage in usages:
                self._append_item(tag, report_id, VariableItem(self._offset[tag][report_id], report_size, usage, flags))

    @staticmethod
    def _iterate(descriptor: bytearray) -> Generator[int, int, int]:
        i = 0
        while i < len(descriptor):
            prefix = descriptor[i]
            i += 1
            tag = (prefix & 0b11110000) >> 4
            typ = (prefix & 0b00001100) >> 2
            size = prefix & 0b00000011

            if size == 0:
                if typ == _HID_TYPE_MAIN:
                    data = 0
                else:
                    data = None
            elif size > 3:
                raise ValueError("Invalid item size")
            else:
                pack_type = '0BHL'[size]
                if typ == _HID_TYPE_GLOBAL and tag in _HID_TAG_GLOBAL_SIGNED_TAGS:
                    pack_type = pack_type.lower()
                fmt = f"<{pack_type}"
                size = struct.calcsize(fmt)
                if i + size > len(descriptor):
                    raise ValueError("Invalid item size")
                
                (data,) = struct.unpack(fmt, descriptor[i:i+size])
            
            yield typ, tag, data

            i += size
