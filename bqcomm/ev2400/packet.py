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

from __future__ import print_function

from __future__ import absolute_import
import datetime
import struct
import sys


def struct_pack_list(*args, **kwargs):
    ret = struct.pack(*args, **kwargs)
    # Python 3
    if sys.hexversion > 0x3000000:
        return list(ret)
    # Python 2
    return list(ord(x) for x in ret)


class InvalidPacketException(Exception):
    pass


class EV2400Packet(object):

    HEADER = 0xAA
    TRAILER = 0x55
    HDR = 0
    TAG = 1
    PID_L = 2
    PID_H = 3
    RETRY = 4
    PLEN = 5
    PAYLD = 6
    CRC = -2
    TLR = -1
    PREAMBLE_SIZE = PLEN + 1
    POSTAMBLE_SIZE = 2
    METADATA_SIZE = PREAMBLE_SIZE + POSTAMBLE_SIZE

    class Tags:

        CMD = 0
        RSP = 1

        # (tag, response_tag)
        # Target packets
        SMB_RD_BYTE = (0x00, 0x40)
        SMB_RD_WORD = (0x01, 0x41)
        SMB_RD_BLOCK = (0x02, 0x42)
        SMB_WR_BYTE = (0x03, None)
        SMB_WR_WORD = (0x04, None)
        SMB_WR_BLOCK = (0x05, None)
        SMB_CMD = (0x06, None)
        I2C_RD_DATA = (0x0D, 0x52)  # 0x4E is in the spec but 0x52 is used
        I2C_WR_DATA = (0x0E, None)
        EE_RD_BLOCK = (0x1D, 0x52)  # Legacy I2C Command
        EE_WR_BLOCK = (0x1E, None)  # Legacy I2C Command
        HDQ8_RD = (0x12, 0x4A)
        HDQ8_WR = (0x13, None)
        HDQ16_RD = (0x14, 0x4B)
        HDQ16_WR = (0x15, None)
        DQ_RD = (0x16, 0x4C)
        DQ_WR = (0x17, None)
        HDQ8_BREAK = (0x1B, None)
        SDQ_WR = (0x21, None)
        SDQ_RD = (0x23, 0x53)
        SDQ_RD_BLOCK = (0x25, 0x54)
        SDQ_WR_BLOCK = (0x27, None)
        SDQ_PULSE = (0x28, None)
        SDQ_WR_FLXBLK = (0x29, None)
        UART_TX = (0x2A, None)
        UART_RX = (0x2B, 0x59)
        SPI_TX_RX = (0x2C, 0x5A)
        HDQ8_WR_BLOCK = (0x2D, None)
        HDQ8_WR_NC_BLOCK = (0x2E, None)
        HDQ8_RD_BLOCK = (0x2F, 0x5B)
        I2C_LIGHT_RD_DATA = (0x30, None)
        I2C_LIGHT_WR_DATA = (0x31, None)
        I2C_LIGHT_STOP = (0x32, None)
        I2C_TRANSACTION = (0x33, 0x52)

        # Controller packets
        GET_VERSION = (0x80, 0xC0)
        RETURN_TO_ROM_RQ = (0x86, 0xC6)
        RETURN_TO_ROM = (0x87, None)
        WAIT = (0x88, None)
        BOARD_NAME = (0x90, 0xC8)
        RESET = (0x91, None)
        BOARD_TYPE = (0x96, 0xCF)
        PWM_CONFIG = (0x9A, None)
        UART_PARAM = (0xB1, None)
        SPI_SETUP = (0xB2, None)
        VVOD_SET_VOLTAGE = (0xB3, None)
        VVOD_STATE = (0xB4, 0xCD)
        VPUV_SET_VOLTAGE = (0xB5, None)
        GPIO_RW = (0xB7, 0xCC)
        SPI_SET_BITRATE = (0xB8, None)
        SPI_SET = (0xB9, None)
        SPI_SET_CS = (0xBA, None)
        SET_I2C_LIGHT_TIMING = (0xBB, None)
        SET_VOUT_WITH_TIMEOUT = (0xBC, None)
        SET_CHARACTERISTICS = (0xBD, 0xCE)
        SET_I2C_SPEED = (0xEE, None)
        SET_SMB_SPEED = (0xEF, None)

        # Response Tags
        ERROR = (None, 0xC3)
        SMB_ERROR = (None, 0x46)
        # RESET_NOTIFICATION = 0xC7 # Not implemented in EV2400 FW

        # Error codes from error packet
        class Err(object):
            UNKNOWN_TAG = 0x80
            QUEUE_FULL = 0x81  # Not actually implemented in EV2400 FW
            BAD_CRC = 0x83
            BAD_PEC = 0x91
            TIMEOUT = 0x92
            NACK = 0x93
            UNSPECIFIED = 0x96

            message = {
                UNKNOWN_TAG: "Unknown packet tag sent to EV2400",
                QUEUE_FULL: "EV2400 packet Queue full",
                BAD_CRC: "Bad CRC sent to EV2400",
                BAD_PEC: "Bad PEC",
                TIMEOUT: "The transaction timed out",
                NACK: "Nack received",
                UNSPECIFIED: "Unspecified error occurred",
            }

            @classmethod
            def get_name(cls, tag, payload):
                if tag == EV2400Packet.Tags.SMB_ERROR[EV2400Packet.Tags.RSP]:
                    idx = 1
                else:
                    idx = 0
                if idx < len(payload):
                    code = payload[idx]
                    for name, err_code in cls.__dict__.items():
                        if name == name.upper() and err_code == code:
                            return name
                return "UNKNOWN"

        @classmethod
        def get_tag(cls, int_tag):
            for name, item in cls.__dict__.items():
                if (
                    isinstance(item, tuple)
                    and len(item) == 2
                    and name == name.upper()
                ):
                    match = None
                    for x in item:
                        if x == int_tag and match is None:
                            match = True
                        elif (
                            not isinstance(x, int)
                            and not isinstance(x, type(None))
                        ):
                            match = False

                    if match:
                        return item

        @classmethod
        def get_name(cls, tag):
            if not isinstance(tag, tuple):
                tag = cls.get_tag(tag)
            if tag is not None:
                for name, item in cls.__dict__.items():
                    if name == name.upper() and tag == item:
                        return name
            return "UNKNOWN"

    class Handler(object):
        def __init__(self, cmd_or_resp):
            self.handlers = {}
            self.cmd_or_resp = cmd_or_resp

        def __call__(self, *tags):
            alltags = []
            for tag in tags:
                if isinstance(tag, tuple):
                    alltags.append(tag[self.cmd_or_resp])

            def reg(fn):
                for tag in alltags:
                    self.handlers[tag] = fn
                return fn
            return reg

        def __getitem__(self, int_tag):
            return self.handlers[int_tag]

        def __contains__(self, int_tag):
            return int_tag in self.handlers

        def ignore_packets(self, *tags):
            for tag in tags:
                self.handlers[tag] = lambda x, y: None

    def __init__(self, tag=None, payload=None, packet_id=None, retry=None):
        self.raw_bytes = []
        self.total_length = None
        self.complete = False
        if (
            tag is None
            and payload is None
            and packet_id is None
            and retry is None
        ):
            self.header = None
            self.tag = None
            self.packet_id = None
            self.retry_count = None
            self.payload_length = None
            self.payload = None
            self.crc = None
            self.trailer = None
        else:
            if payload is None:
                payload = []
            if packet_id is None:
                packet_id = 0
            if retry is None:
                retry = 0
            self.set(tag, payload, packet_id, retry)

    def set(self, tag, payload=[], packet_id=0, retry=0):
        self.header = EV2400Packet.HEADER
        if isinstance(tag, tuple):
            tag = tag[EV2400Packet.Tags.CMD]
        self.tag = tag
        self.packet_id = packet_id
        self.retry_count = retry
        self.payload_length = len(payload)
        self.payload = payload[:]
        self.crc = 0
        self.trailer = EV2400Packet.TRAILER
        self.pack()
        self.validate()
        return self

    def pack(self, no_crc_recalc=False):
        self.raw_bytes = struct_pack_list(
            "<BBHBB",
            self.header,
            self.tag,
            self.packet_id,
            self.retry_count,
            self.payload_length
        )

        self.raw_bytes += self.payload + [self.crc, self.trailer]
        if not no_crc_recalc:
            self.crc = self.calc_crc()
            self.raw_bytes[EV2400Packet.CRC] = self.crc
        self.total_length = len(self.raw_bytes)

    def add_bytes(self, data):
        pre_bytes = max(0, EV2400Packet.PREAMBLE_SIZE - len(self.raw_bytes))
        self.raw_bytes.extend(data[:pre_bytes])
        if len(self.raw_bytes) >= EV2400Packet.PREAMBLE_SIZE:
            self.total_length = EV2400Packet.METADATA_SIZE + \
                self.raw_bytes[EV2400Packet.PLEN]
        self.raw_bytes = (
            self.raw_bytes + data[pre_bytes:])[:self.total_length]
        if len(self.raw_bytes) == self.total_length:
            self.complete = True
            self.header = self.raw_bytes[EV2400Packet.HDR]
            self.tag = self.raw_bytes[EV2400Packet.TAG]
            self.packet_id = self.raw_bytes[EV2400Packet.PID_L]
            self.packet_id += self.raw_bytes[EV2400Packet.PID_H] << 8
            self.retry_count = self.raw_bytes[EV2400Packet.RETRY]
            self.payload_length = self.raw_bytes[EV2400Packet.PLEN]
            self.payload = self.raw_bytes[EV2400Packet.PAYLD:EV2400Packet.CRC]
            self.crc = self.raw_bytes[EV2400Packet.CRC]
            self.trailer = self.raw_bytes[EV2400Packet.TLR]

            # TODO: This does not fail gracefully
            # self.validate()

    def validate(self):
        if self.header != EV2400Packet.HEADER:
            raise InvalidPacketException(
                "Header was not " + hex(EV2400Packet.HEADER))

        if self.trailer != EV2400Packet.TRAILER:
            raise InvalidPacketException(
                "Trailer was not " + hex(EV2400Packet.TRAILER))

        if (
            self.retry_count is None
            or self.retry_count < 0
            or self.retry_count > 0xFF
        ):
            raise InvalidPacketException("Retry Count must be in range 0-255")

        if self.payload is None:
            raise InvalidPacketException("Payload was None")

        if len(self.payload):
            if max(self.payload) > 0xFF or min(self.payload) < 0:
                raise InvalidPacketException(
                    "Payload values must be in range 0-255")

        if len(self.payload) > 0xFF:
            raise InvalidPacketException("Max payload size is 255 bytes")

        if self.payload_length != len(self.payload or []):
            raise InvalidPacketException(
                "Payload length ({0}) did not match actual ({1})".format(
                    self.payload_length, len(self.payload or [])
                )
            )

        if self.tag is None or self.tag < 0 or self.tag > 0xFF:
            raise InvalidPacketException(
                "Tag {0} must be in the range 0-255".format(self.tag))

        if (
            self.packet_id is None
            or self.packet_id < 0
            or self.packet_id > 0xFFFF
        ):
            msg = "Packet ID {0} must be in the range 0-65535"
            raise InvalidPacketException(msg.format(self.packet_id))

        if self.crc != self.calc_crc():
            msg = "CRC ({0}) is incorrect (shoule be {1})"
            raise InvalidPacketException(
                msg.format(self.crc, self.calc_crc())
            )

    def calc_crc(self):
        data = self.raw_bytes[EV2400Packet.TAG:EV2400Packet.CRC]
        crc = data[0]
        for c in data[1:]:
            for j in range(8):
                carry = crc & 0x80
                crc = (crc << 1) | (c >> 7)
                crc &= 0xFF
                if carry:
                    crc ^= 0x07  # Poly for EV2400
                c <<= 1
                c &= 0xFF

        for j in range(8):
            carry = crc & 0x80
            crc <<= 1
            crc &= 0xFF
            if carry:
                crc ^= 0x07

        return crc

    def __str__(self):
        tag_len = 21
        tag_name = EV2400Packet.Tags.get_name(self.tag)
        tag_name += ' ' * (tag_len - len(tag_name))

        if self.packet_id != 0:
            tag_name += ' <{0}>'.format(self.packet_id)

        data = '[' + ', '.join("%02X" % x for x in self.payload) + ']'

        if not self.ok:
            try:
                err = EV2400Packet.Tags.Err.get_name(self.tag, self.payload)
                data += " ({0})".format(err)
            except IndexError:
                pass

        return "{0} ({1:02X}): {2}".format(tag_name, self.tag, data)

    def __repr__(self):
        return "EV2400Packet<{0}>".format(str(self))

    @property
    def ok(self):
        error_tags = [
            EV2400Packet.Tags.ERROR[EV2400Packet.Tags.RSP],
            EV2400Packet.Tags.SMB_ERROR[EV2400Packet.Tags.RSP]
        ]
        return self.tag is not None and self.tag not in error_tags

    @property
    def error(self):
        if self.ok:
            return None
        if not len(self.payload):
            raise InvalidPacketException("Error packet had no error code")
        error_code = self.payload[-1]
        try:
            return EV2400Packet.Tags.Err.message[error_code]
        except KeyError:
            return "Unknown error code {0:02X}".format(error_code)

    def response(self, payload):
        tags = EV2400Packet.Tags
        resp_tag = tags.get_tag(self.tag)[tags.RSP]
        return EV2400Packet(resp_tag, payload, self.packet_id)


class PacketStream(object):

    def __init__(self, send_raw_data, on_packet_received):
        self.on_packet_received = on_packet_received
        self.partial_packet = None
        self.send_raw_data = send_raw_data
        self.enable_tracing = False

    def on_data_received(self, data):
        if not len(data):
            return

        if self.partial_packet is None:
            self.partial_packet = EV2400Packet()

        assert data[0] == 0x3F
        assert data[1] <= len(data) - 2

        if data[1] == 0:
            if self.enable_tracing:
                print("GOT EMPTY USB PACKET")
            return

        if len(self.partial_packet.raw_bytes) == 0:
            if data[2] != EV2400Packet.HEADER:
                if self.enable_tracing:
                    print("GOT GARBAGE DATA (don't see header)")
                return

        self.partial_packet.add_bytes(data[2:data[1] + 2])
        if self.partial_packet.complete:

            packet = self.partial_packet
            self.log_packet(packet, False)
            self.partial_packet = None
            if self.on_packet_received:
                self.on_packet_received(packet)

    def send_packet(self, packet):

        psz = 62
        data = packet.raw_bytes
        if not data:
            return

        self.log_packet(packet, True)

        while len(data):
            buf = data[:psz]
            data = data[psz:]
            buf = [0x3f, len(buf)] + buf + [0] * (psz - len(buf))
            if self.enable_tracing:
                print("sending data: ", ' '.join('%02X' % x for x in buf))
            self.send_raw_data(buf)

    def log_packet(self, packet, outgoing):
        if not self.enable_tracing:
            return

        log = datetime.datetime.now().strftime("%m/%d/%y %H:%M:%S.%f ")
        log += "--> " if outgoing else "<-- "
        log += str(packet)
        print(log)

    # Map call of this to data handler
    __call__ = on_data_received
