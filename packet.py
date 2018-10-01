def checkSum(data, mask=0xFF):
    cs = 0x00
    for i in range(0,len(data)):
        cs += data[i]
    cs = (cs & mask) ^ mask
    return chr(cs)

class Packet:
    command  = 0x02
    ota      = 0x04

    otaStart = 0x0b
    otaStop  = 0x0c
    otaReady = 0x0d

    smartDrive = 0x00

    minPacketLength = 6
    otaReadyLength = minPacketLength

    def __init__(self, Type=None, SubType=None, data=None):
        if Type is not None and SubType is not None:
            length = len(data) if data is not None else 0
            self.data = bytearray(length + self.minPacketLength)
            self.data[0] = 0xFE
            self.data[1] = self.Type
            self.data[2] = self.SubType

            for i in range(0, length):
                self.data[3 + i] = data[i]

            self.data[-3] = length
            self.data[-2] = checkSum(data)
            self.data[-1] = 0xEF

        elif data is not None:
            self.data = data
            self.Type = self.data[0]
            self.SubType = self.data[1]
        else:
            raise ValueError("must provide either data or Type AND SubType")

    def __str__(self):
        return ' '.join('{:02x}'.format(x) for x in self.data)

    def isValid(self):
        if self.data is None:
            return False
        payloadLen = (len(self.data) - self.minPacketLength)
        crc = checkSum(self.data[3:(3+payloadLen)])
        if (payloadLen < 0 or
            self.data[0] != 0xFE or
            self.data[1] != Type or
            self.data[2] != SubType or
            self.data[-3] != payloadLen or
            self.data[-2] != crc or
            self.data[-1] != 0xEF):
            return False
        return True

class Header(Packet):
    def __init__(self, version, checksum):
        payload = bytearray(8)
        payload[0] = version
        payload[4] = checksum & 0xFF
        payload[5] = (checksum >> 8) & 0xFF
        payload[6] = (checksum >> 16) & 0xFF
        payload[7] = (checksum >> 24) & 0xFF
        super(self.ota, self.smartDrive, payload, 8)

