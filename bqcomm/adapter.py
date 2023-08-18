"""
Copyright (c) 2018-2021, Texas Instruments Incorporated
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

1. Redistributions of source code must retain the above copyright
notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright
notice, this list of conditions and the following disclaimer in the
documentation and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its
contributors may be used to endorse or promote products derived from
this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

from __future__ import absolute_import
import time


class Error(Exception):
    pass


class UnsupportedOperation(Error):
    def __init__(self, op):
        msg = "Comm device does not support {operation}".format(operation=op)
        super(UnsupportedOperation, self).__init__(msg)


def _unsupported_property(read=None, write=None):
    def un(self, *args):
        msg = "Comm device does not support this property"
        raise UnsupportedOperation(msg)

    if read is None:
        read = un

    if write is None:
        write = un

    return property(read, write)


class CommDevice(object):

    KNOWN_TYPES = []

    I2C_100KHZ = 100
    I2C_400KHZ = 400

    @classmethod
    def enumerate(cls):
        """Return a list of IDs that can be used to open the adapter"""
        devices = []
        for t in cls.KNOWN_TYPES:
            devices.extend(t.enumerate())

        return devices

    @classmethod
    def register(cls, device_type):
        if device_type not in cls.KNOWN_TYPES:
            cls.KNOWN_TYPES.append(device_type)

    def close(self):
        raise NotImplementedError("CommDevice did not implement a close()")

    def open(self):
        raise NotImplementedError("CommDevice did not implement an open()")

    def i2c_transaction(self, target, wr, read_len):
        """

        Perform an I2C transaction and return the result

        `target` is the I2C target address.
        `wr` is the a list of bytes to write. To do a register read, pass in
            a list `[reg_addr]`.
        `read_len` is the number of bytes to read afterwards. Can be 0 for a
            write-only transaction, or None for an SMBus block read where the
            first byte returned by the device specifies the block length.
        """
        raise UnsupportedOperation("I2C")

    def enable_pullups(self, enabled):
        raise UnsupportedOperation("pullup control")

    def delay_ms(self, milliseconds):
        time.sleep(milliseconds / 1000.0)

    def hdq_read_block(self, addr, length):
        raise UnsupportedOperation("HDQ")

    def hdq_write_block(self, addr, data):
        raise UnsupportedOperation("HDQ")

    def hdq_break(self):
        raise UnsupportedOperation("HDQ")

    def dq_read_byte(self, reg_addr):
        raise UnsupportedOperation("DQ")

    def dq_write_byte(self, reg_addr, data):
        raise UnsupportedOperation("DQ")

    bitrate = _unsupported_property()

    # Need to add HDQ later

    def __repr__(self):
        return type(self).__name__


class Adapter(object):

    @classmethod
    def enumerate(cls):
        for dev in CommDevice.enumerate():
            yield Adapter(dev, no_open=True)

    def __init__(self, device=None, no_open=False):

        if device is None:
            devices = CommDevice.enumerate()
            if not len(devices):
                raise Error("No communication devices available")

            device = devices[0]
            if not no_open:
                device.open()

        self.device = device

        self.i2c_transaction = self.device.i2c_transaction

    def __repr__(self):
        return "{0}<{1}>".format(type(self).__name__, repr(self.device))

    def open(self):
        self.device.open()

    def close(self):
        self.device.close()

    def delay_ms(self, milliseconds):
        self.device.delay_ms(milliseconds)

    def smb_cmd(self, target_addr, cmd):
        self.i2c_transaction(target_addr, [cmd], 0)

    def smb_read_byte(self, target_addr, cmd):
        return self.i2c_transaction(target_addr, [cmd], 1)

    def smb_read_word(self, target_addr, cmd):
        res = self.i2c_transaction(target_addr, [cmd], 2)
        return res[0] + (res[1] << 8)

    def smb_read_block(self, target_addr, cmd):
        return self.i2c_transaction(target_addr, [cmd], None)

    def smb_write_byte(self, target_addr, cmd, data):
        self.i2c_transaction(target_addr, [cmd, data], 0)

    def smb_write_word(self, target_addr, cmd, data):
        data = [cmd, data & 0xFF, (data >> 8) & 0xFF]
        self.i2c_transaction(target_addr, data, 0)

    def smb_write_block(self, target_addr, cmd, data):
        data = [cmd, len(data)] + list(data)
        self.i2c_transaction(target_addr, data, 0)

    def hdq_read_block(self, addr, length):
        return self.device.hdq_read_block(addr, length)

    def hdq_write_block(self, addr, data):
        return self.device.hdq_write_block(addr, data)

    def hdq_break(self):
        self.device_hdq_break()

    def dq_read_byte(self, reg_addr):
         return self.device.dq_read_byte(reg_addr)

    def dq_write_byte(self, reg_addr, data):
         return self.device.dq_write_byte(reg_addr, data)

    def i2c_read_block(self, target_addr, reg_addr, length):
        return self.i2c_transaction(target_addr, [reg_addr], length)

    def i2c_write_block(self, target_addr, reg_addr, data):
        self.i2c_transaction(target_addr, [reg_addr] + list(data), 0)
