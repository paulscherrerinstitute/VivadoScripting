# Parser Descriptions 

## I2C Parser Usage
This python package allows easily extracting I2C bus transactions from Vivado ILA traces. To do so, follow the
steps below.

1. Add an ILA to the design that records at least SDA and SCL. Make sure "Capture Control" is enabled.
2. Before recording data, set the "Caputre Setup" to "SDA=B or SCL=B" (record data if either SDA or SCL has an edge).
   This is required to capture as muich I2C traffic as possible (all I2C events are fully defined by only recording
   the edges).
3. Record data
4. Write the data to a CSV (Vivado TCL Console: write_hw_ila_data -csv_file -force <fileName>
5. Parse the CSV file using this library (see example for details)

Usage Examle
```
from ChipscopeI2cParse import *

#Setup Parser
parser = I2cParser(scl_name="i_i2c_scl_rx_1", sda_name="i_i2c_sda_rx_1")

#Parse CSV file
accesses = parser.Parse("data_edges_only1.csv")

#Filter for accesses to a given address and print them
address = 0x26
for acc in filter(lambda x: x.address is address, accesses):
    print(acc)
exit()
```