##############################################################################
#  Copyright (c) 2018 by Paul Scherrer Institute, Switzerland
#  All rights reserved.
#  Authors: Oliver Bruendler
##############################################################################

import sys
sys.path.append("..")
from ChipscopeI2cParse import *

#Setup Parser
parser = I2cParser(scl_name="soc_i/i_i2c_scl_rx_1", sda_name="soc_i/i_i2c_sda_rx_1")

#Parse CSV file
accesses = parser.Parse("data_edges_only1.csv")

#Filter for accesses to a given address and print them
address = 0x26
for acc in accesses:
    print(acc)
exit()

