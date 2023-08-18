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
from __future__ import print_function
import atexit
import logging

import bqcomm

try:
    import aardvark_py
except ImportError:
    aardvark_py = None

_LOGGER = logging.getLogger("bqcomm")


class Aardvark(bqcomm.CommDevice):

    _aa_errors = None

    @classmethod
    def enumerate(cls):
        # This eventually could query features (SPI, I2C, GPIO, I2C_MONITOR)

        # Input argument is max number of devices. Obviously this won't work
        # if over 1024 Aardvarks are connected, but will that actually happen?
        retcode, devices = aardvark_py.aa_find_devices(1024)

        # Seems to return number of devices
        if retcode < aardvark_py.AA_OK:
            # For some reason you get this if you haven't plugged in an
            # Aardvark yet. Sometimes.
            if retcode != aardvark_py.AA_UNABLE_TO_LOAD_DRIVER:
                raise bqcomm.Error(cls.get_aa_error(retcode))

        for dev in devices:
            yield cls(dev, no_open=True)

    def __init__(
        self,
        port=0,
        bitrate=bqcomm.CommDevice.I2C_100KHZ,
        no_open=False
    ):

        self.port = port
        self.handle = None
        self._bitrate = bitrate
        self._aa_mode = aardvark_py.AA_CONFIG_GPIO_I2C

        if not no_open:
            self.open()

        atexit.register(self.close)

    def __repr__(self):
        return "Aardvark(port={0})".format(self.port)

    def open(self):
        if self.handle is None:

            self.handle = aardvark_py.aa_open(self.port)

            if self.handle <= 0:
                msg = "Unable to open Aardvark on port {0}".format(self.port)
                raise bqcomm.Error(msg)

            # Make sure it gets written to the device
            self.bitrate = self._bitrate
            aardvark_py.aa_configure(self.handle, self._aa_mode)
            self.enable_pullups(True)

    def close(self):
        if self.handle is not None:
            aardvark_py.aa_close(self.handle)
            self.handle = None

    def i2c_transaction(self, target, wr, read_len):
        # Make sure Aardvark is in I2C mode
        i2c_mode = self._aa_mode & aardvark_py.AA_CONFIG_I2C_MASK
        if not i2c_mode:
            self._aa_mode |= aardvark_py.AA_CONFIG_I2C_MASK
            aardvark_py.aa_configure(self.handle, self._aa_mode)

        # Shift target address for aardvark API
        target >>= 1

        # Allow either list or single byte data for wr
        try:
            iter(wr)
        except TypeError:
            if wr is None:
                wr = []
            else:
                wr = list(wr)

        if len(wr):
            wr = aardvark_py.array('B', wr)

        # Set up flags
        flags = aardvark_py.AA_I2C_NO_FLAGS
        smb_block = read_len is None
        if smb_block:
            flags |= aardvark_py.AA_I2C_SIZED_READ
            read_len = 255

        if read_len and len(wr):  # Write/Read
            aa = aardvark_py.aa_i2c_write_read
            (result, wr_count, data_in, rd_count) = aa(
                self.handle,
                target,
                flags,
                wr,
                read_len
            )

            Aardvark.check_error(result)

            if wr_count != len(wr):
                raise bqcomm.Error(
                    "Number of bytes actually written does not match "
                    "requested number"
                )

            if not smb_block and len(data_in) != read_len:
                raise bqcomm.Error(
                    "Number of bytes actually read does not match requested "
                    "number"
                )

            data = list(data_in)
            if smb_block:
                data = data[1:]

            return data

        elif len(wr):  # Write-only
            wr_count = aardvark_py.aa_i2c_write(
                self.handle,
                target,
                flags,
                wr
            )

            if wr_count != len(wr):
                raise bqcomm.Error(
                    "Number of bytes actually written does not match "
                    "requested number"
                )
            return []
        else:  # Read only
            result, data_in = aardvark_py.aa_i2c_read(
                self.handle, target, flags, read_len
            )

            Aardvark.check_error(result)

            if not smb_block and len(data_in) != read_len:
                raise bqcomm.Error(
                    "Number of bytes actually read does not "
                    "match requested number"
                )

            data = list(data_in)
            print("RD: " + ' '.join(map('{0:02X}'.format, data)))
            if smb_block:
                data = data[1:]

            return data

    @property
    def bitrate(self):
        return self._bitrate

    @bitrate.setter
    def bitrate(self, bitrate):
        self._bitrate = aardvark_py.aa_i2c_bitrate(self.handle, bitrate)

    def enable_pullups(self, enabled):
        if enabled:
            enabled = aardvark_py.AA_I2C_PULLUP_BOTH
        else:
            enabled = aardvark_py.AA_I2C_PULLUP_NONE

        aardvark_py.aa_i2c_pullup(self.handle, enabled)

    def delay_ms(self, milliseconds):
        aardvark_py.aa_sleep_ms(milliseconds)

    @classmethod
    def get_aa_error(cls, code):
        if cls._aa_errors is None:
            cls._aa_errors = {
                aardvark_py.AA_UNABLE_TO_LOAD_LIBRARY:
                    "Unable to load Aardvark library",
                aardvark_py.AA_UNABLE_TO_LOAD_DRIVER:
                    "Unable to load Aardvark Driver",
                aardvark_py.AA_UNABLE_TO_LOAD_FUNCTION:
                    "Unable to load Aardvark Function",
                aardvark_py.AA_INCOMPATIBLE_LIBRARY:
                    "Incompatible Aardvark Library",
                aardvark_py.AA_INCOMPATIBLE_DEVICE:
                    "Incompatible Aardvark Device",
                aardvark_py.AA_COMMUNICATION_ERROR:
                    "Error communicating with Aardvark",
                aardvark_py.AA_UNABLE_TO_OPEN:
                    "Unable to open Aardvark",
                aardvark_py.AA_UNABLE_TO_CLOSE:
                    "Unable to close Aardvark",
                aardvark_py.AA_INVALID_HANDLE:
                    "Invalid Aardvark Handle",
                aardvark_py.AA_CONFIG_ERROR:
                    "Aardvark Configuration Error",

                # I2C codes (-100 to -199)
                aardvark_py.AA_I2C_NOT_AVAILABLE:
                    "I2C not available on Aardvark",
                aardvark_py.AA_I2C_NOT_ENABLED:
                    "I2C not enabled on Aardvark",
                aardvark_py.AA_I2C_READ_ERROR:
                    "I2C Read Error",
                aardvark_py.AA_I2C_WRITE_ERROR:
                    "I2C Write Error",
                aardvark_py.AA_I2C_SLAVE_BAD_CONFIG:
                    "Bad I2C Slave Configuration",
                aardvark_py.AA_I2C_SLAVE_READ_ERROR:
                    "I2C Slave Read Error",
                aardvark_py.AA_I2C_SLAVE_TIMEOUT:
                    "I2C Slave Timeout",
                aardvark_py.AA_I2C_DROPPED_EXCESS_BYTES:
                    "Aardvark dropped excess bytes with I2C",
                aardvark_py.AA_I2C_BUS_ALREADY_FREE:
                    "I2C bus already free",

                # enum AardvarkI2cStatus
                aardvark_py.AA_I2C_STATUS_BUS_ERROR:
                    "I2C Bus Error",
                aardvark_py.AA_I2C_STATUS_SLA_ACK:
                    "I2C Slave Ack",
                aardvark_py.AA_I2C_STATUS_SLA_NACK:
                    "I2C Slave Nack",
                aardvark_py.AA_I2C_STATUS_DATA_NACK:
                    "I2C Data Nack",
                aardvark_py.AA_I2C_STATUS_ARB_LOST:
                    "I2C Bus Arbitration Lost",
                aardvark_py.AA_I2C_STATUS_BUS_LOCKED:
                    "I2C Bus Locked",
                aardvark_py.AA_I2C_STATUS_LAST_DATA_ACK:
                    "I2C Last Data Ack",

                # SPI codes (-200 to -299)
                aardvark_py.AA_SPI_NOT_AVAILABLE:
                    "SPI not available on Aardvark",
                aardvark_py.AA_SPI_NOT_ENABLED:
                    "SPI Not enbabled on Aardvark",
                aardvark_py.AA_SPI_WRITE_ERROR:
                    "SPI Write Error",
                aardvark_py.AA_SPI_SLAVE_READ_ERROR:
                    "SPI Slave Read Error",
                aardvark_py.AA_SPI_SLAVE_TIMEOUT:
                    "SPI Slave Timeout",
                aardvark_py.AA_SPI_DROPPED_EXCESS_BYTES:
                    "Aardvark dropped excess bytes with SPI",

                # GPIO codes (-400 to -499)
                aardvark_py.AA_GPIO_NOT_AVAILABLE:
                    "GPIO not available",

                # I2C bus monitor codes (-500 to -599)
                aardvark_py.AA_I2C_MONITOR_NOT_AVAILABLE:
                    "I2C Monitor not available",
                aardvark_py.AA_I2C_MONITOR_NOT_ENABLED:
                    "I2C Monitor not enabled",
            }
        return cls._aa_errors.get(code, "Unknown Error {0}".format(code))

    @classmethod
    def check_error(cls, retcode):
        if retcode == aardvark_py.AA_OK:
            return
        raise bqcomm.Error(cls.get_aa_error(retcode))


class AardvarkNotInstalled(bqcomm.CommDevice):
    @classmethod
    def enumerate(cls):
        _LOGGER.warn(
            "aardvark_py not installed- run `pip install aardvark_py` to "
            "enable TotalPhase Aardvark adapter support."
        )
        return []


# Keep a copy of the original class just in case
_Aardvark = Aardvark

# If not installed, use the dummy implementation
if aardvark_py is None:
    Aardvark = AardvarkNotInstalled
