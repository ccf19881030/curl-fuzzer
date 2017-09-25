#!/usr/bin/env python
#
# Common corpus functions
import logging
import struct
log = logging.getLogger(__name__)


class BaseType(object):
    TYPE_URL = 1
    TYPE_RSP1 = 2
    TYPE_USERNAME = 3
    TYPE_PASSWORD = 4
    TYPE_POSTFIELDS = 5
    TYPE_HEADER = 6
    TYPE_COOKIE = 7
    TYPE_UPLOAD1 = 8
    TYPE_RANGE = 9
    TYPE_CUSTOMREQUEST = 10
    TYPE_MAIL_RECIPIENT = 11
    TYPE_MAIL_FROM = 12
    TYPE_MIME_PART = 13
    TYPE_MIME_PART_NAME = 14
    TYPE_MIME_PART_DATA = 15

    TYPEMAP = {
        TYPE_URL: "CURLOPT_URL",
        TYPE_RSP1: "First server response",
        TYPE_USERNAME: "CURLOPT_USERNAME",
        TYPE_PASSWORD: "CURLOPT_PASSWORD",
        TYPE_POSTFIELDS: "CURLOPT_POSTFIELDS",
        TYPE_HEADER: "CURLOPT_HEADER",
        TYPE_COOKIE: "CURLOPT_COOKIE",
        TYPE_UPLOAD1: "CURLOPT_UPLOAD / CURLOPT_INFILESIZE_LARGE",
        TYPE_RANGE: "CURLOPT_RANGE",
        TYPE_CUSTOMREQUEST: "CURLOPT_CUSTOMREQUEST",
        TYPE_MAIL_RECIPIENT: "curl_slist_append(mail recipient)",
        TYPE_MAIL_FROM: "CURLOPT_MAIL_FROM",
        TYPE_MIME_PART: "curl_mime_addpart",
        TYPE_MIME_PART_NAME: "curl_mime_name",
        TYPE_MIME_PART_DATA: "curl_mime_data",
    }



class TLVEncoder(BaseType):
    def __init__(self, output):
        self.output = output

    def write_string(self, tlv_type, wstring):
        data = wstring.encode("utf-8")
        self.write_tlv(tlv_type, len(data), data)

    def write_bytes(self, tlv_type, bytedata):
        self.write_tlv(tlv_type, len(bytedata), bytedata)

    def maybe_write_string(self, tlv_type, wstring):
        if wstring is not None:
            self.write_string(tlv_type, wstring)

    def write_mimepart(self, namevalue):
        (name, value) = namevalue.split(":", 1)

        # Create some mimepart TLVs for the name and value
        name_tlv = self.encode_tlv(self.TYPE_MIME_PART_NAME, len(name), name)
        value_tlv = self.encode_tlv(self.TYPE_MIME_PART_DATA, len(value), value)

        # Combine the two TLVs into a single TLV.
        part_tlv = name_tlv + value_tlv
        self.write_tlv(self.TYPE_MIME_PART, len(part_tlv), part_tlv)

    def encode_tlv(self, tlv_type, tlv_length, tlv_data=None):
        log.debug("Encoding TLV %r, length %d, data %r",
                  self.TYPEMAP.get(tlv_type, "<unknown>"),
                  tlv_length,
                  tlv_data)

        data = struct.pack("!H", tlv_type)
        data = data + struct.pack("!L", tlv_length)
        if tlv_data:
            data = data + tlv_data

        return data

    def write_tlv(self, tlv_type, tlv_length, tlv_data=None):
        log.debug("Writing TLV %r, length %d, data %r",
                  self.TYPEMAP.get(tlv_type, "<unknown>"),
                  tlv_length,
                  tlv_data)

        data = self.encode_tlv(tlv_type, tlv_length, tlv_data)
        self.output.write(data)


class TLVDecoder(BaseType):
    def __init__(self, inputdata):
        self.inputdata = inputdata
        self.pos = 0
        self.tlv = None

    def __iter__(self):
        self.pos = 0
        self.tlv = None
        return self

    def __next__(self):
        if self.tlv:
            self.pos += self.tlv.total_length()

        if (self.pos + TLVHeader.TLV_DECODE_FMT_LEN) > len(self.inputdata):
            raise StopIteration

        # Get the next TLV
        self.tlv = TLVHeader(self.inputdata[self.pos:])
        return self.tlv

    next = __next__


class TLVHeader(BaseType):
    TLV_DECODE_FMT = "!HL"
    TLV_DECODE_FMT_LEN = struct.calcsize(TLV_DECODE_FMT)

    def __init__(self, data):
        # Parse the data to populate the TLV fields
        (self.type, self.length) = struct.unpack(self.TLV_DECODE_FMT, data[0:self.TLV_DECODE_FMT_LEN])

        # Get the remaining data and store it.
        self.data = data[self.TLV_DECODE_FMT_LEN:self.TLV_DECODE_FMT_LEN + self.length]

    def __repr__(self):
        return ("{self.__class__.__name__}(type={stype!r} ({self.type!r}), length={self.length!r}, data={self.data!r})"
                .format(self=self,
                        stype=self.TYPEMAP.get(self.type, "<unknown>")))

    def total_length(self):
        return self.TLV_DECODE_FMT_LEN + self.length