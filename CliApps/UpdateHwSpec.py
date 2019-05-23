from argparse import ArgumentParser

import sys
import os
FILEPATH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, FILEPATH + "/..")
from BuildScripts.Sdk import Sdk

parser = ArgumentParser()
parser.add_argument("-hw", help="HW platform directory", required=True, type=str)
parser.add_argument("-bsp", help="BSP directory", required=True, type=str)
parser.add_argument("-hdf", help="New HDF File", required=True, type=str)
args = parser.parse_args()

print(">> Update HW")
sdk = Sdk("SDK_2018_2", "2018.2")
print("Create Workspace")
sdk.CreateEmtpyWorkspace("tempWs")
print("Import Projects")
sdk.ImportProjects(args.hw, args.bsp, None)
print("Update HW")
sdk.UpdateHwSpec(args.hdf)
print("Copy Back")
sdk.CopyToSrcLoc()
print("Clean Up")