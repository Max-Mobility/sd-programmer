from packet import Packet, Header

class SmartDrive:
    def __init__(self):
        try:
            f = open(filename, 'rb')
        except Exception as error:
            print("ERROR: Couldn't open file {}".format(filename))
        else:
            with f:
                fileData = bytearray(f.read())

            self.fileSize = os.path.getsize(filename)
            self.fwCheckSum = checkSum(fileData, fileSize, 0xFFFFFFFF)

    def programBootloader(self):
        pass

    def programFirmware(self, port):
        haveRecvReady = False
        while not haveRecvReady:
            # send start
            p = Packet(command, otaStart, [smartDrive])
            port.flushInput();
            port.write(p.data)

            # receive ota ready
            resp = bytearray(port.read(otaReadyLength))
            if not checkOTAReady(resp):
                pass
            else:
                haveRecvReady = True

        # send header
        p = Header(version, self.fwCheckSum)
        port.write(p.data)

        # send firmware data
        for i in range(0, self.fileSize, 16):
            length = min(self.fileSize - i, 16)
            fwData = fileData[i:(i+length)]
            p = Packet(ota, smartDrive, fwData)
            port.write(p.data)
            time.sleep(transmitDelay)

        # send stop
        p = Packet(command, otaStop, [smartDrive])
        port.write(p.data)
