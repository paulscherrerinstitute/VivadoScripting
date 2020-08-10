##############################################################################
#  Copyright (c) 2018 by Paul Scherrer Institute, Switzerland
#  All rights reserved.
#  Authors: Oliver Bruendler
##############################################################################

########################################################################################################################
# Import Statements
########################################################################################################################
from PsiPyUtils.TempFile import TempFile
from PsiPyUtils.TempWorkDir import TempWorkDir
from PsiPyUtils.ExtAppCall import ExtAppCall
from typing import Iterable, Dict
import shutil
import os, sys

########################################################################################################################
# Class Defintion
########################################################################################################################
class Vivado:
    """
    This class allows building Vivado projects from the command line.

    Usage example:
        viv = Vivado("VIVADO_2017_2", "2017.2")
        viv.ExecuteTcl("D:/dbpm/BPM_FPGA/Vivado", "project.tcl")
        viv.BuildXpr("D:/dbpm/BPM_FPGA/Vivado/soc", "soc.xpr")
        viv.ExportHdf("D:/dbpm/BPM_FPGA/Vivado/soc", "soc.xpr", "export.hdf")
    """

    ####################################################################################################################
    # Public Methods
    ####################################################################################################################
    def __init__(self, vivadoPathEnv : str, version : str):
        """
        Constructor

        :param vivadoPathEnv: Environment variable that points to the Vivado installation. This can be used to have multiple
                              Vivado installations in parallel and have an environment variable pointint to each one. By
                              choosing the right environment variable, one can choose the Vivado version to use.
        :param version:       Toolversion in the form "2017.2". This version string may be used in future for the case that
                              commands or paths change between versions.
        """
        if vivadoPathEnv not in os.environ:
            raise Exception("Enviromental variable {} does not exists. Please specify it".format(vivadoPathEnv))
        self._vivado_path = os.environ[vivadoPathEnv]
        self.stderr = ""
        self.stdout = ""
        self.whs = None
        self.wns = None
        self.criticalWarnings = []
        self.errors = []

    def ExecuteTcl(self, workDir : str, script : str):
        """
        Execute a TCL script in vivado

        :param workDir: Working directory to execute the TCL script in
        :param script: Script to execute (path relative to the working directory or absolute)
        """
        self._RunVivado(workDir, "-source {}".format(script))

    def BuildXpr(self, workDir : str, xprName : str, generateBd : bool = False, bdNames : Iterable[str] = None):
        """
        Build an XPR project

        :param workDir: Working directory for the project (directory the .xpr file is in)
        :param xprName: Name of the XPR file (including extension) to build
        :param generateBd: If true, block diagrams in the design are (re-)generated. The re-generation is forced, so
                           they are even re-generated if they are unchanged. Note that re-generatino of BDs is required
                           after checking out an XPR project from a version control system.
                           Depending on bdNames, either all BDs or only the selected ones are re-generated.
        :param bdNames: A list of bd-names can be passed (e.g. ["system.bd", "other.bd]) to only re-generate pecific BDs.
                        If the parameter is omitted, all BDs are regenerated.
        """
        #Clear whs/wns to make sure no old values are read if the compilation fails
        self.whs = None
        self.wns = None
        #Build
        with TempWorkDir(workDir):
            #Create vivado tcl
            tcl = ""
            tcl += "open_project {}\n".format(xprName)
            #Run Implementation
            tcl += "update_compile_order -fileset sources_1\n"
            if generateBd:
                if bdNames is None:
                    tcl += "generate_target -force all [get_files -regexp .*bd]\n"
                else:
                    for name in bdNames:
                        tcl += "generate_target -force all [get_files -regexp .*{}]\n".format(name)
            tcl += "set_param general.maxThreads 1\n" #Workaround for multithreading bug in the xilinx tools (DRC hangs)
            tcl += "reset_run synth_1\n"
            tcl += "launch_runs impl_1 -to_step write_bitstream -jobs 4\n"
            tcl += "wait_on_run impl_1\n"
            #Print Worst-case slacks
            tcl += "puts \"RESULT-WNS: [get_property STATS.WNS [current_run]]\"\n"
            tcl += "puts \"RESULT-WHS: [get_property STATS.WHS [current_run]]\"\n"
            tcl += "close_project\n"
            with TempFile("__viv.tcl") as f:
                f.write(tcl)
                f.flush()
                #Execute Vivado
                self._RunVivado(".", "-source __viv.tcl")
            #Parse Log File
            with open("vivado.log", "r") as f:
                for line in f.readlines():
                    if line.startswith("CRITICAL WARNING:"):
                        self.criticalWarnings.append(line)
                    if line.startswith("ERROR:"):
                        self.errors.append(line)
                    if line.startswith("RESULT-WNS:"):
                        #An empty string may be returned if the compilation failed
                        try:
                            self.wns = float(line.split(":")[1].strip())
                        except:
                            self.wns = None
                    if line.startswith("RESULT-WHS:"):
                        # An empty string may be returned if the compilation failed
                        try:
                            self.whs = float(line.split(":")[1].strip())
                        except:
                            self.wns = None



    def ExportHdf(self, workDir : str, xprName : str, hdfPath : str):
        """
        Export HDF file

        :param workDir: Working directory for the project (directory the .xpr file is in)
        :param xprName: Name of the XPR file (including extension) to export the .hdf file for
        :param hdfPath: Path of the HDF file to create
        """
        hdfAbs = os.path.abspath(hdfPath).replace("\\", "/")
        with TempWorkDir(workDir):
            tcl = ""
            tcl += "open_project {}\n".format(xprName)
            tcl += "set PRJ_NAME [get_property NAME [current_project ]]\n"
            tcl += "set TOP_NAME [get_property TOP [current_fileset]]\n"
            tcl += "file copy -force ./$PRJ_NAME.runs/impl_1/$TOP_NAME.sysdef {}\n".format(hdfAbs)
            tcl += "close_project\n"
            with TempFile("__viv.tcl") as f:
                f.write(tcl)
                f.flush()
                #Execute Vivado
                self._RunVivado(".", "-source __viv.tcl")
                
    def ExportXsa(self, workDir : str, xprName : str, xsaPath : str):
        """
        Export XSA file

        :param workDir: Working directory for the project (directory the .xpr file is in)
        :param xprName: Name of the XPR file (including extension) to export the .xsa file for
        :param xsaPath: Path of the XSA file to create
        """
        xsaAbs = os.path.abspath(xsaPath).replace("\\", "/")
        with TempWorkDir(workDir):
            tcl = ""
            tcl += "open_project {}\n".format(xprName)
            tcl += "write_hw_platform -fixed -include_bit -force -file {}\n".format(xsaAbs)
            tcl += "close_project\n"
            with TempFile("__viv.tcl") as f:
                f.write(tcl)
                f.flush()
                #Execute Vivado
                self._RunVivado(".", "-source __viv.tcl")
                
    def CreateFlashImage(self, bitstreams : dict, outFile : str, flashSizeMb : int, interface : str = "SPIx1"):
        """
        Create a flash image containing multiple bitstreams

        :param bitstreams: Dictionary containing bitstream paths as value and addresses as key. example {0x0100 : bla.bit}
        :param outFile: Output file to write
        :param flashSizeMb: Size of the flash in MB
        :param interface: configuration interface to use (see Vivado help for write_cfgmem for details)
        :return: None
        """
        with TempFile("__viv.tcl") as f:
            bsStringParts = ["up {:08x} {}".format(size, path) for size, path in bitstreams.items()]
            bsString = " ".join(bsStringParts)
            string = "write_cfgmem -force -disablebitswap -size {fsize} -format BIN -loadbit \"{bitstreams}\" -interface {itf} {file}"
            f.write(string.format(fsize=flashSizeMb, bitstreams=bsString, itf=interface, file=outFile))
            f.flush()
            # Execute Vivado
            self._RunVivado(".", "-source __viv.tcl")

    def PackageBdAsIp(self, workDir : str, xprName : str, bdName : str, outputDir : str, vendor : str = "NoVendor", addrBlockRenaming : Dict[str, str] = None):
        """
        Package a block design inside a vivado project as IP. This is useful for building hierarchial projects.

        :param workDir: Working directory for the project (directory the .xpr file is in)
        :param xprName: Name of the XPR file (including extension) to build
        :param bdName: Name of the BD to package
        :param outputDir: Directory to put the IP-Core into
        :param vendor: Vendor name to use
        :param addrBlockRenaming: Dictionary containing new names for address blocks based on their base address in the form {"0x1000":"NewName"}.
                                  This is required because Vivado by default just names the blocks Reg0, Reg1, etc. which
                                  is not very helpful when defining the address map of the core.
        :return: None
        """

        outAbs = os.path.abspath(outputDir).replace("\\", "/") #Vivado always requires linux paths
        #Build
        with TempWorkDir(workDir):
            #Create vivado tcl
            tcl = ""
            tcl += "open_project {}\n".format(xprName)
            tcl += "ipx::package_project -vendor {} -root_dir {} -library user -taxonomy /UserIP -module {} -import_files -force\n".format(vendor, outAbs, bdName)
            if addrBlockRenaming is not None:
                tcl += "set allBlocks [ipx::get_address_blocks -of_objects [ipx::get_memory_maps * -of_objects [ipx::current_core]] *]\n"
                for addr, name in addrBlockRenaming.items():
                    tcl += "foreach block $allBlocks {\n" + \
                           "  scan [get_property BASE_ADDRESS $block] %x blkAddr\n"+ \
                           "  if {{ {thisAddr} == $blkAddr}} {{\n".format(thisAddr=int(addr)) + \
                           "    set_property NAME {{{}}} $block\n".format(name) + \
                           "  }\n" + \
                           "}\n"
            tcl += "ipx::create_xgui_files [ipx::current_core]\n" + \
                   "ipx::update_checksums [ipx::current_core]\n" + \
                   "ipx::save_core [ipx::current_core]\n"
            tcl += "close_project\n"
            with TempFile("__viv.tcl") as f:
                f.write(tcl)
                f.flush()
                # Execute Vivado
                try:
                    self._RunVivado(".", "-source __viv.tcl")
                except:
                    shutil.copy("__viv.tcl", "__failedViv.tcl", )
                    raise

    ####################################################################################################################
    # Public Properties
    ####################################################################################################################
    @property
    def StdErr(self):
        """
        Get standard error output of the last command executed

        :return: stderr output of the last command
        """
        return self.stderr


    @property
    def StdOut(self):
        """
        Get standard output of the last command executed

        :return: stdout output of the last command
        """
        return self.stdout

    @property
    def CriticalWarnings(self):
        """
        Get critical warnings after building a project using BuildXpr()

        :return: critical warnings that occured during BuildXpr() as a list
        """
        return self.criticalWarnings

    @property
    def Errors(self):
        """
        Get errors after building a project using BuildXpr()

        :return: critical warnings that occured during BuildXpr() as a list
        """
        return self.errors

    @property
    def WNS(self):
        """
        Get worst case setup slack after building a project using BuildXpr()

        :return: Worst case setup slack in ns
        """
        #Raise exception if WNS is not yet set
        if self.wns is None:
            raise Exception("Compilation not complete, WNS not available")
        #Return value
        return self.wns

    @property
    def WHS(self):
        """
        Get worst case hold slack after building a project using BuildXpr()

        :return: Worst case hold slack in ns
        """
        #Raise exception if WHS is not yet set
        if self.whs is None:
            raise Exception("Compilation not complete, WHS not available")
        #Return value
        return self.whs


    ####################################################################################################################
    # Private Methods
    ####################################################################################################################
    def _RunVivado(self, workDir : str, args : str):
        #Windows
        if sys.platform.startswith("win"):
            vivadoCmd = "bin/vivado.bat"
        #Other OS not yet supported
        elif sys.platform.startswith("linux"):
            vivadoCmd = "bin/vivado"
        else:
            raise Exception("OS Not Supported")

        call = ExtAppCall(workDir, "{}/{} -mode batch {}".format(self._vivado_path, vivadoCmd, args))
        call.run_sync()
        self.stderr = call.get_stderr()
        self.stdout = call.get_stdout()
        if len(self.stderr) != 0:
            raise Exception("STDERR not empty\n" + self.stderr)
        if call.get_exit_code() != 0:
            raise Exception("Command exited with code {}".format(call.get_exit_code()))