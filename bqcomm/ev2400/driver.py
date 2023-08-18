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

# Python 2 compatibility
from __future__ import print_function

from __future__ import absolute_import
import atexit

import bqcomm

from pywinusb import hid

from .packet import EV2400Packet, PacketStream
import six

try:
    import queue
except ImportError:
    import six.moves.queue as queue

Tags = EV2400Packet.Tags

class EV2400(bqcomm.CommDevice):

    USB_VID_PID = (0x0451, 0x0037)
    USB_BSL_VID_PID = (0x2047, 0x0200)

    I2C_CLK_BASE_KHZ = 4000

    @classmethod
    def list_hid_devices(cls, bsl=False):
        if bsl:
            vid, pid = cls.USB_BSL_VID_PID
        else:
            vid, pid = cls.USB_VID_PID

        fil = hid.HidDeviceFilter(vendor_id=vid, product_id=pid)
        return fil.get_devices()

    @classmethod
    def enumerate(cls):
        for dev in cls.list_hid_devices():
            yield cls(dev, no_open=True)

    def __init__(self, device=None, no_open=False):

        if device is None:
            device = 0

        if isinstance(device, six.integer_types):
            try:
                device = EV2400.list_hid_devices()[device]
            except IndexError:
                raise bqcomm.Error("No EV2400 at index {0}".format(device))

        self.device = device
        self.is_open = False
        atexit.register(self.close)

        self.resp_queue = queue.Queue()
        self.timeout = 2.0

        self._last_packet_id = 0
        self._bitrate = None

        if not no_open:
            self.open()

    def _next_packet_id(self):
        self._last_packet_id = (self._last_packet_id + 1) & 0xFFFF
        return self._last_packet_id

    @property
    def bitrate(self):
        return self._bitrate

    @bitrate.setter
    def bitrate(self, bitrate):
        if bitrate > bqcomm.CommDevice.I2C_400KHZ:
            raise bqcomm.Error("Unsupported bitrate- should be < 400")

        divider = int(round(float(EV2400.I2C_CLK_BASE_KHZ) / bitrate))
        self.set_i2c_divider(divider)
        self._bitrate = int(round(EV2400.I2C_CLK_BASE_KHZ / divider))

    def open(self):
        if self.is_open:
            return

        self.device.open(shared=False)
        self.is_open = True

        out_report = self.device.find_output_reports()[0]
        self.packetstream = PacketStream(out_report.send, self.packet_received)
        self.device.set_raw_data_handler(self.packetstream)

        if self._bitrate is None:
            self.bitrate = bqcomm.CommDevice.I2C_100KHZ

    def close(self):
        if self.is_open:
            self.device.close()
            self.is_open = False

    def packet_received(self, packet):
        self.resp_queue.put_nowait(packet)

    def do_transaction(self, packet, get_resp=True):
        # Future Improvement: Use packet IDs and be smarter about the queue
        # Should at least check response tag
        packet.packet_id = self._next_packet_id()
        packet.pack()
        packet.validate()
        self.packetstream.send_packet(packet)
        try:
            resp = self.resp_queue.get(
                True, self.timeout if get_resp else 0.025)
            resp.payload = list(resp.payload)  # Don't use ReadOnlyList type
        except queue.Empty:
            if get_resp:
                raise bqcomm.Error("Timeout waiting for EV2400 response")
            else:
                return None

        assert resp.packet_id == packet.packet_id
        resp.validate()

        if resp.error:
            try:
                code = resp.payload[0]
            except IndexError:
                code = -1
            raise bqcomm.Error(resp.error, code)

        return resp

    def get_version(self):
        resp = self.do_transaction(EV2400Packet(Tags.GET_VERSION))
        if len(resp.payload) < 2:
            raise bqcomm.Error("Malformed version response packet")

        return "v{0}.{1:02d}".format(*resp.payload[:2])

    def get_board_id(self):
        resp = self.do_transaction(EV2400Packet(Tags.GET_BOARD_ID))
        if len(resp.payload) < 1:
            raise bqcomm.Error("Malformed board ID response packet")

        return resp.payload[0]

    def set_vout_with_timeout(self, settings):
        assert len(settings) == 4
        packet = EV2400Packet(Tags.SET_VOUT_WITH_TIMEOUT, settings)
        self.do_transaction(packet, get_resp=False)

    def get_serial_number(self):
        return self.device.serial_number

    def get_board_name(self):
        resp = self.do_transaction(EV2400Packet(Tags.BOARD_NAME))
        return resp.payload

    def set_board_name(self, name, auto=True):
        if auto:
            name = [len(name)] + list(map(ord, name))
        assert len(name) <= 32
        packet = EV2400Packet(Tags.BOARD_NAME, name)
        self.do_transaction(packet, get_resp=False)

    def enter_fw_update_mode(self):
        resp = self.do_transaction(EV2400Packet(Tags.RETURN_TO_ROM_RQ))
        code = resp.payload[:2]
        assert len(code) == 2
        self.do_transaction(EV2400Packet(Tags.RETURN_TO_ROM, code))

    def enable_fast_mode(self, fast_mode):
        data = [0x02 if fast_mode else 0x00, 0x02] + [0] * 4
        self.do_transaction(
            EV2400Packet(Tags.SET_CHARACTERISTICS, data),
            get_resp=False
        )

    def set_i2c_divider(self, div):
        data = [div & 0xff, (div >> 8) & 0xff]
        self.do_transaction(
            EV2400Packet(Tags.SET_I2C_SPEED, data),
            get_resp=False
        )

    def set_smb_divider(self, div):
        data = [div & 0xff, (div >> 8) & 0xff]
        self.do_transaction(
            EV2400Packet(Tags.SET_SMB_SPEED, data),
            get_resp=False
        )

    def smb_read(self, tag, address, cmd):
        # Untested
        r = self.do_transaction(EV2400Packet(tag, [address, cmd]))
        if len(r.payload) < 3:
            raise bqcomm.Error("Malformed response packet")
        if r.payload[-1] == 0:
            return r.payload[1:-1]
        else:
            raise bqcomm.Error("SMB Error Status " + str(r.payload[2]))

    def smb_read_byte(self, address, cmd):
        # Untested
        return self.smb_read(Tags.SMB_RD_BYTE, address, cmd)[0]

    def smb_read_word(self, address, cmd):
        # Untested
        data = self.smb_read(Tags.SMB_RD_WORD, address, cmd)
        return data[0] + data[1] * 0x100

    def smb_read_block(self, address, cmd):
        return self.smb_read(Tags.SMB_RD_BLOCK, address, cmd)[1:]

    def smb_cmd(self, address, cmd, data):
        # Untested
        self.do_transaction(EV2400Packet(
            Tags.SMB_CMD,
            [address, cmd]
        ), False)
        return True

    def smb_write_byte(self, address, cmd, data):
        # Untested
        self.do_transaction(EV2400Packet(
            Tags.SMB_WR_BYTE,
            [address, cmd, data]
        ), False)
        return True

    def smb_write_word(self, address, cmd, data):
        # Untested
        self.do_transaction(EV2400Packet(
            Tags.SMB_WR_WORD,
            [address, cmd, data & 0xFF, (data >> 8) & 0xFF]
        ), False)
        return True

    def smb_write_block(self, address, cmd, data):
        # Untested
        self.do_transaction(EV2400Packet(
            Tags.SMB_WR_BLOCK,
            [address, cmd, len(data)] + data
        ), False)
        return True

    def i2c_read_block(self, target_addr, reg_addr, length):
        # Untested
        r = self.do_transaction(EV2400Packet(
            Tags.I2C_RD_DATA,
            [target_addr, reg_addr, length]
        ))
        if len(r.payload) < 3 + length:
            raise bqcomm.Error("Malformed response packet")

        if r.payload[-1] == 0:
            return r.payload[2:-1]
        else:
            raise bqcomm.Error("I2C Error Status " + str(r.payload[-1]))

    def i2c_transaction(self, target_addr, wr, read_len):
        flags = 0
        if read_len is None:
            read_len = 0
            flags |= 0x01
        r = self.do_transaction(EV2400Packet(
            Tags.I2C_TRANSACTION,
            [target_addr, flags, read_len, len(wr)] + wr
        ))
        return r.payload

    def i2c_write_block(self, target_addr, reg_addr, data):
        # Untested
        self.do_transaction(EV2400Packet(
            Tags.I2C_WR_DATA,
            [target_addr, reg_addr, len(data)] + data
        ), False)
        return True

    def hdq_read_block(self, reg_addr, length):
        # Untested
        r = self.do_transaction(EV2400Packet(
            Tags.HDQ8_RD_BLOCK,
            [reg_addr, length],
            retry=2
        ))
        if len(r.payload) < length:
            raise bqcomm.Error("Malformed response packet")

        if len(r.payload):
            return r.payload[1:r.payload[0]+1]
        else:
            raise bqcomm.Error("HDQ Read returned no bytes")

    def hdq_write_block(self, reg_addr, data):
        # Untested
        self.do_transaction(EV2400Packet(
            Tags.HDQ8_WR_BLOCK,
            [reg_addr, len(data)] + data
        ), False)
        return True

    def dq_read_byte(self, reg_addr):
        r = self.do_transaction(EV2400Packet(
            Tags.DQ_RD,
            [reg_addr],
            retry=2
        ))
        if len(r.payload) < 2:
            raise bqcomm.Error("Malformed response packet")

        if len(r.payload):
            return r.payload[1]
        else:
            raise bqcomm.Error("DQ Read returned no bytes")

    def dq_write_byte(self, reg_addr, data):
        self.do_transaction(EV2400Packet(
            Tags.DQ_WR,
            [reg_addr, data]
        ), False)
        return True

    def enable_tracing(self, enable=True):
        self.packetstream.enable_tracing = enable

    def set_pwm(self, duty, period=None):
        settings = []

        if not duty:
            duty = 0

        if period is not None:
            assert period > 0
            assert period <= 65535
            assert period > duty

        if duty or period:
            settings = [duty & 0xff, (duty >> 8) & 0xff]
            if period:
                settings += [period & 0xff, (period >> 8) & 0xff]

        packet = EV2400Packet(Tags.PWM_CONFIG, settings)
        self.do_transaction(packet, get_resp=False)

    def get_board_type(self):
        resp = self.do_transaction(EV2400Packet(Tags.BOARD_TYPE))
        return resp.payload
