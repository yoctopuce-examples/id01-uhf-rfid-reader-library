# -*- coding: utf-8 -*-
# ********************************************************************
#
#  Sample python library to interface DFRobot ID01 UDF RFID reader
#  using Yoctopuce Yocto-RS485-V2 interface
#
#  You can find more information on our web site:
#   Yocto-RS485-V2:
#      https://www.yoctopuce.com/EN/products/yocto-rs485-v2
#   Python API Reference:
#      https://www.yoctopuce.com/EN/doc/reference/yoctolib-python-EN.html
#
# *********************************************************************

from yoctopuce.yocto_api import *
from yoctopuce.yocto_serialport import *

class ID01:
    """
    The ID01 class is designed to access DFRobot ID01 UFH RFID reader
    using a Yocto-RS485-V2 interface
    """

    def __init__(self, connection):
        """
        Prepare to use an ID01 UHF RFID reader on specified port or IP address
        :param connection: either "usb", or IP address of a YoctoHub hosting the RS485 interface
        """
        self._connection = connection
        self._serialPort = None
        self._lastError = "No error"

    def connect(self):
        """
        Establish the connection to the RS485 interface
        :return: "OK" if the function succeeds, or an error message otherwise
        """
        errmsg = YRefParam()
        if YAPI.RegisterHub(self._connection, errmsg) != YAPI.SUCCESS:
            return "Cannot connect to " + self._connection + ": " + errmsg.value
        self._serialPort = YSerialPort.FindSerialPort('ID01_RFID')
        if not self._serialPort.isOnline():
            return "No Yocto-RS485-V2 found with logical name set to 'ID01_RFID'"
        self._serialPort.set_serialMode("9600,8N1")
        self._serialPort.set_protocol("Frame:3ms")
        return "OK"

    def disconnect(self):
        """
        Disconnects from the RS485 interface and free ressources
        """
        YAPI.UnregisterHub(self._connection)

    def getLastError(self):
        return self._lastError

    def encodeMessage(self, byteList):
        """
        Encode an outgoing message to be sent to the RFID reader
        :param byteList: the command bytes (without prefix, length and checksum)
        :return: a complete message that can be sent to the RFID reader, as hex string
        """
        msglen = len(byteList)
        # prepend prefix, length and add checksum
        chksum = 0xa0 + (msglen+1)
        hexstr = "A0%02X" % (msglen+1)
        for i in range(len(byteList)):
            chksum += byteList[i]
            hexstr += "%02X" % byteList[i]
        chksum = (-chksum) & 0xff
        hexstr += "%02X" % chksum
        return hexstr

    def decodeMessage(self, hexstr, result):
        """
        Decode an incoming message coming from the RFID reader.
        The decoded message is stored in the result list passed as argument
        :param hexstr: the message, including prefix, length and checksum, as hex string
        :return: "OK" if the message is well formed, or an error message otherwise
        """
        replybin = bytes.fromhex(hexstr)
        replylen = replybin[1]
        if len(replybin) != replylen+2:
            return "Invalid RFID reply length (communication error)"
        # verify checksum, save result in list
        chksum = replybin[0] + replybin[1]
        for i in range(2, len(replybin)-1):
            chksum += replybin[i]
            result.append(replybin[i])
        chksum += replybin[len(replybin)-1]
        if (chksum & 0xff) != 0:
            return "Invalid RFID reply checksum (communication error)"
        return "OK"

    def sendCommand(self, byteList):
        """
        Send a command to the RFID reader, adding the checksum on the fly, and wait for the reply
        :param byteArray: the command bytes (without prefix, length and checksum)
        :return: the reply payload received from reader if success
                 [] if no valid reply is received from reader, use getLastError() for more info
        """
        hexstr = self.encodeMessage(byteList)
        # send message, wait for reply for 1000 [ms]
        replystr = self._serialPort.queryHex(hexstr, 1000)
        if replystr == "":
            self._lastError = "No reply received from RFID reader, check wiring"
            return []
        # parse reply
        res = []
        msgcheck = self.decodeMessage(replystr, res)
        if msgcheck != "OK":
            self._lastError = msgcheck
            return []
        if res[0] != byteList[0] or res[1] != byteList[1]:
            self._lastError = "Reply does not match query (protocol error)"
            return []
        return res[2:]

    def getReaderSoftwareVersion(self):
        """
        Get the software release of the RFID reader
        :return: the version number string in form XX.XX, or an error message
        """
        res = self.sendCommand([0x6a, 0x00])
        if len(res) == 0:
            return self._lastError
        return "%02X.%02X" % (res[0], res[1])

    def stopContinuousReading(self):
        """
        Disable continuous tag detection, read only when requested to do so
        :return: "OK" if the function suceeds, or an error message otherwise
        """
        res = self.sendCommand([0xa8, 0x00])
        if len(res) == 0:
            return self._lastError
        if res[0] == 0:
            return "OK"
        self._lastError = "stopContinuousReading command rejected"
        return self._lastError

    def startContinuousReading(self):
        """
        Enable continuous tag detection (for diagnosis purposes with buzzer function)
        :return: "OK" if the function suceeds, or an error message otherwise
        """
        res = self.sendCommand([0x65, 0x00])
        if len(res) == 0:
            return self._lastError
        if res[0] == 0:
            return "OK"
        self._lastError = "restartContinuousReading command rejected"
        return self._lastError

    def setReaderBuzzer(self, buzzerMode):
        """
        Configure the buzzer mode to signal tag detection
        :param buzzerMode: 0=no beep, >=1: beeps when detecting tag
        :return: "OK" if the function suceeds, or an error message otherwise
        """
        res = self.sendCommand([0xb0, 0x00, buzzerMode])
        if len(res) == 0:
            return self._lastError
        if res[0] == 0:
            return "OK"
        self._lastError = "setReaderBuzzer command rejected"
        return self._lastError

    def requestTagIdentification(self):
        """
        Send "Read EPC tag identification" command, and get result
        :return: the antenna code ID as a list of bytes, or an empty array if none is found
        """
        reply = self.sendCommand([0x82, 0x00])
        if len(reply) == 0:
            return []
        if reply[0] == 1:
            # valid antenna found, convert EPC ID to words
            res = []
            for i in range(1, len(reply), 2):
                res.append(reply[i]*256+reply[i+1])
            return res
        self._lastError = "No EPC tag detected"
        return []

    def readWordsFromTag(self, bank, addr, nWords):
        """
        Send "Read data from EPC tag" command, and get result
        :param bank: the bank to read from (0=Reserved, 1=EPC, 2=TID, 3=User)
        :param addr: the word start address (0-4 for Reserved area, 2-7 for EPC, varies for User)
        :param nWords: the number of words to read
        :return: the list of words read from tag, or an empty array if none is found
        """
        reply = self.sendCommand([0x80, 0x00, bank, addr, nWords])
        if len(reply) == 0:
            return []
        if reply[0] == bank:
            # valid antenna found
            res = []
            for i in range(3, len(reply), 2):
                res.append(reply[i]*256+reply[i+1])
            return res
        self._lastError = "No EPC tag detected"
        return []

    def writeWordsToTag(self, bank, addr, data):
        """
        Send "Write data to EPC tag" command, and get result
        :param bank: the bank to read from (0=Reserved, 1=EPC, 3=User)
        :param addr: the word start address (0-4 for Reserved area, 2-7 for EPC, varies for User)
        :param data: the list of words to write (max 8 words)
        :return: "OK" if the message is well formed, or an error message otherwise
        """
        writeMode = 0 if len(data)==0 else 1
        cmd = [0x81, 0x00, writeMode, bank, addr, len(data)]
        for i in range(len(data)):
            cmd.append((data[i] >> 8) & 0xff)
            cmd.append(data[i] & 0xff)
        print(cmd)
        res = self.sendCommand(cmd)
        print(res)
        if len(res) == 0:
            return []
        if res[0] == 0:
            # valid antenna found
            return "OK"
        self._lastError = "No EPC tag detected"
        return self._lastError

    # The functions below correspond to DFRobot documentation,
    # but have no clear purpose as multi-tag mode is undocumented
    def restartTagIdentification(self):
        res = self.sendCommand([0xfc, 0x00])
        print(res)

    def restartAccessData(self):
        res = self.sendCommand([0xff, 0x00])
        print(res)

    def accessData(self):
        res = self.sendCommand([0xa6, 0x00])
        print(res)
