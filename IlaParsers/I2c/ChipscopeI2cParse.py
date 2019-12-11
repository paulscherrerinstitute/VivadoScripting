##############################################################################
#  Copyright (c) 2018 by Paul Scherrer Institute, Switzerland
#  All rights reserved.
#  Authors: Oliver Bruendler
##############################################################################

#######################################################################################################################
# This python package allows easily extracting I2C bus transactions from Vivado ILA traces. To do so, follow the
# steps below.
#
# 1. Add an ILA to the design that records at least SDA and SCL. Make sure "Capture Control" is enabled.
# 2. Before recording data, set the "Caputre Setup" to "SDA=B or SCL=B" (record data if either SDA or SCL has an edge).
#    This is required to capture as muich I2C traffic as possible (all I2C events are fully defined by only recording
#    the edges).
# 3. Record data
# 4. Write the data to a CSV (Vivado TCL Console: write_hw_ila_data -csv_file -force <fileName>
# 5. Parse the CSV file using this library (see example for details)
#######################################################################################################################
from enum import Enum

#I2C Bus Access Type
class AccessType:
    Write = 0
    Read = 1

#I2C transaction container
class I2cAccess:

    def __init__(self):
        self.address = 0
        self.access_type = AccessType.Write
        self._bus_transactions = []
        self.data = []
        self.addr_ack = False
        self.data_ack = []

    def _AckToStr(self, ack : bool):
        return "ACK" if ack else "NACK"

    def _AddStart(self):
        self._bus_transactions.append("START")

    def _AddRepStart(self):
        self._bus_transactions.append("REPEATED START")

    def _AddStop(self):
        self._bus_transactions.append("STOP")

    def _AddAddr(self, addr : int, op : AccessType, ack : bool):
        strop = "WR" if op == AccessType.Write else "RD"
        self._bus_transactions.append("ADDR: 0x{:x} {} {}".format(addr, strop, self._AckToStr(ack)))
        self.address = addr
        self.access_type = op
        self.addr_ack = ack

    def _AddData(self, value : int, ack : bool):
        self.data.append(value)
        self._bus_transactions.append("DATA: 0x{:02x} {}".format(value, self._AckToStr(ack)))
        self.data_ack.append(ack)

    def ToString(self, ignoreAck : bool):
        str = self.__str__()
        if ignoreAck:
            str = str.replace("NACK", "").replace("ACK", "")
        return str

    def __str__(self):
        return "\n  ".join(self._bus_transactions)



#Parser Class
class I2cParser:

    def __init__(self, scl_name : str, sda_name : str):
        self.scl_name = scl_name
        self.sda_name = sda_name

    def Parse(self, file : str) -> list:
        #Read File
        with open(file, "r+") as f:
            data = f.readlines()

        #Find indexes
        sclIdx = -1
        sdaIdx = -1
        for idx, title in enumerate(data[0].split(",")):
            if title.strip().endswith(self.scl_name):
                sclIdx = idx
            if title.strip().endswith(self.sda_name):
                sdaIdx = idx
        if sclIdx == -1:
            raise Exception("SCL signal name not found")
        if sdaIdx == -1:
            raise Exception("SDA signal name not found")

        #Initialize
        scl_last = 0
        sda_last = 0
        accesses = []
        curBit = 0
        curByte = 0x00
        byteNr = 0
        state = _State.Idle
        sda_last = 1 #idle state

        #Parse samples
        for nr, line in enumerate(data[1:]):
            #Skip lines containing radixes (added by newer vivado versions)
            if line.startswith("Radix"):
                continue
            parts = line.split(",")
            scl = int(parts[sclIdx].strip())
            sda = int(parts[sdaIdx].strip())
            # Start Condition
            if scl == 1 and sda == 0 and sda_last == 1:
                # Start
                if state is _State.Idle:
                    curAcc = I2cAccess()
                    curAcc._AddStart()
                    state = _State.Running
                # Repeated start
                else:
                    curAcc._AddRepStart()
                byteNr = 0
                curBit = 0
                curByte = 0x00
            # Stop Condition
            elif scl == 1 and sda == 1 and sda_last == 0:
                if state is _State.Running:
                    curAcc._AddStop()
                    accesses.append(curAcc)
                    state = _State.Idle
            # Rising Edge
            elif scl == 1 and scl_last == 0:
                if state is _State.Running:
                    if curBit == 8:
                        ack = not sda
                        # Address handling
                        if byteNr is 0:
                            addr = curByte >> 1
                            rnw = curByte % 2
                            if rnw is 0:
                                acctype = AccessType.Write
                            else:
                                acctype = AccessType.Read
                            curAcc._AddAddr(addr, acctype, ack)
                            curAcc.address = addr
                        # Data handling
                        else:
                            curAcc._AddData(curByte, ack)
                        curBit = 0
                        curByte = 0x00
                        byteNr += 1
                    else:
                        curByte = curByte * 2 + sda
                        curBit += 1
            scl_last = scl
            sda_last = sda
        return accesses

class _State(Enum):
    Idle = 0,
    Running = 1