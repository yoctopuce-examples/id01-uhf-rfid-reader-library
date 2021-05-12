# -*- coding: utf-8 -*-
# ********************************************************************
#
#  Python example code for using ID01.py library for accessing
#  DFRobot ID01 UDF RFID reader using Yoctopuce Yocto-RS485-V2 interface
#
#  You can find more information on our web site:
#   Yocto-RS485-V2:
#      https://www.yoctopuce.com/EN/products/yocto-rs485-v2
#   Python API Reference:
#      https://www.yoctopuce.com/EN/doc/reference/yoctolib-python-EN.html
#
# *********************************************************************

import os, sys

from ID01 import *

# Use the ID01 library with on a RS485 interface connected via USB.
# You can use an IP address instead of "usb" when using a YoctoHub
# or a device connected to a remote machine running VirtualHub service
rfidReader = ID01("usb")

status = rfidReader.connect()
if status != "OK":
    sys.exit(status)

print("RFID reader version: "+ rfidReader.getReaderSoftwareVersion())
print("Scanning for RFID tags, press Ctrl-Break to exit")
res = rfidReader.setReaderBuzzer(0)
while res == "OK":
    tag = rfidReader.requestTagIdentification()
    if len(tag) != 0:
        print("Tag detected: ", tag)
        data = rfidReader.readWordsFromTag(3, 0, 8)
        if len(data) == 0: data = rfidReader.getLastError()
        print("   User data: ", data)
        print("Type (E) rewrite tag EPC ID, (U) to write user data or (Return) to rescan")
        cmd = input("Action: ")  # use raw_input in python 2.x
        if cmd.upper() == 'E':
            values = input("Enter 1 to 6 comma-separated EPC ID words: ")
            strArr = values.split(",")
            words = []
            for i in range(len(strArr)):
                words.append(int(strArr[i].strip()))
            result = rfidReader.writeWordsToTag(1, 2, words)
            print("Result: "+result)
        elif cmd.upper() == 'U':
            values = input("Enter 1 to 8 comma-separated user data words: ")
            strArr = values.split(",")
            words = []
            for i in range(len(strArr)):
                words.append(int(strArr[i].strip()))
            result = rfidReader.writeWordsToTag(3, 0, words)
            print("Result: " + result)
        elif cmd != '':
            print("Unknown command: ["+cmd+"]")

rfidReader.disconnect()
