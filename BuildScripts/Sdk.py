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
import os, sys
import shutil
from distutils import dir_util
import pyparsing as pp
import glob

class SdkStdErrNotEmpty(Exception):
    pass

class SdkExitCodeNotZero(Exception):
    pass

########################################################################################################################
# Class Defintion
########################################################################################################################
class Sdk:


    """
    This class allows building SDK projects from the command line.

    Usage example:
        sdk = Sdk("SDK_2017_2", "myWs", "2017.2")
        sdk.CreateEmtpyWorkspace()
        sdk.ImportProjects( hwPath="D:/dbpm/BPM_FPGA/Vivado/soc.sdk/soc_wrapper_hw_platform_0",
                            bspPath="D:/dbpm/BPM_FPGA/Vivado/soc.sdk/bsp",
                            appPath="D:/dbpm/BPM_FPGA/Vivado/soc.sdk/sw")
        sdk.UpdateHwSpec("D:/dbpm/BPM_FPGA/Vivado/soc/SdkExport/soc_wrapper.hdf")
        sdk.BuildWorkspace()
        sdk.CreateBitWithSw("Debug", "soc_i/processor/microblaze_0", "out.bit")
        sdk.CleanWorkpace()
    """

    ####################################################################################################################
    # Public Methods
    ####################################################################################################################
    def __init__(self, sdkPathEnv : str, version : str):
        """
        Initialize an SDK workspace to build.

        :param sdkPathEnv: Environment variable that points to the SDk installation. This can be used to have multiple
                           SDK installations in parallel and have an environment variable pointint to each one. By
                           choosing the right environment variable, one can choose the SDK version to use.
        :param version:    Toolversion in the form "2017.2". This version string may be used in future for the case that
                           commands or paths change between versions.
        """
        if sdkPathEnv not in os.environ:
            raise Exception("Enviromental variable {} does not exists. Please specify it".format(sdkPathEnv))
        self._sdk_path = os.environ[sdkPathEnv]
        self.workspace = None
        self.stderr = ""
        self.stdout = ""
        self.allStdOut = ""
        self._SetPaths()

    def UseExistingWorkspace(self, workspace : str, hw_name : str = None, bsp_name : str = None):
        """
        :param workspace:  Path of the workspace to use.

        WARNING: This method is deprecated! Use "CreateEmptyWorkspace" and "ImportProjects" instead
        """
        self.workspace = os.path.abspath(workspace)
        self.hwName = hw_name
        self.bspName = bsp_name

    def CreateEmtpyWorkspace(self, workspace : str):
        """
        Delete the workspace folder if it exists and create a new, completely empty folder.

        :param workspace:  Path of the workspace to use.
        """
        out = ""
        err = ""
        shutil.rmtree(workspace, ignore_errors=True)
        os.mkdir(workspace)
        self.UseExistingWorkspace(workspace)

    def ImportProjects(self, hwPath : str, bspPath : str, appPath : str, debug : bool = False):
        """
        Import projects into workspace

        :param hwPath:  Path to the HW project
        :param bspPath: Path to the BSP project
        :param appPath: Path to the application project
        :param debug: Optional parameter. If true, the standard output is printed to the console. In this case the automatic checking for
                      errors is disabled, so it shall only be used for debugging purposes.
        """
        importClauses = ""
        self.hwName = os.path.split(hwPath)[-1] if hwPath is not None else None
        self.hwPath = hwPath
        self.appName = os.path.split(appPath)[-1] if appPath is not None else None
        self.appPath = appPath
        self.bspName = os.path.split(bspPath)[-1] if bspPath is not None else None
        self.bspPath = bspPath
        for path in [hwPath, bspPath, appPath]:
            if path is not None:
                importClauses += "importprojects {} \n".format(os.path.abspath(path).replace("\\", "/"))
        self._RunSdk(importClauses, debug)

    def UpdateHwSpec(self, hdfPath : str, debug : bool = False):
        """
        Update the HW specification with a new .hdf file

        :param hdfPath: Path to the new HDF file
        :param debug: Optional parameter. If true, the standard output is printed to the console. In this case the automatic checking for
                      errors is disabled, so it shall only be used for debugging purposes.
        """

        # Parse MSS file to restore OS Settings later
        # .. This is a workaround for the issue that the BSP settings are overwritten by the Xilinx tools.
        # .. Replacement is done after updating the spec
        PP_END = pp.CaselessKeyword("END")
        PP_OS = pp.CaselessKeyword("BEGIN OS") + pp.OneOrMore(pp.Combine(~PP_END + pp.restOfLine())) + PP_END
        mssFile = glob.glob(os.path.join(self.workspace, self.bspName, "*.mss"))[0]
        os_block = None
        with open(mssFile) as f:
            content = f.read()
            for t, s, e in PP_OS.scanString(content):
                os_block = content[s:e]

        #Update HW Spec
        tclStr = ""
        tclStr += "updatehw -hw {} -newhwspec {}\n".format(self.hwName, os.path.abspath(hdfPath).replace("\\","/"))
        tclStr += "after 1000\n" #Wait for one second to allow the first command to complete
        tclStr += "regenbsp -bsp {}\n".format(self.bspName)
        self._RunSdk(tclStr, debug)

        # Restore MSS File, second part of workaround described above
        with open(mssFile) as f:
            print("file: " + mssFile)
            content = f.read()
            for t, s, e in PP_OS.scanString(content):
                content = content.replace(content[s:e], os_block)
                print("replaced \n{} by \n{}".format(content[s:e], os_block))
        with open(mssFile, "w+") as f:
            f.write(content)

    def CopyToSrcLoc(self):
        """
        Copy the projects from the workspace back to their source locations.

        This is required as workaround for the fact, that XSCT always copies all sources into the project (instead of linking them)
        """
        for name, dir in zip((self.hwName, self.bspName, self.appName), (self.hwPath, self.bspPath, self.appPath)):
            if name is not None:
                dir_util.copy_tree(self.workspace + "/" + name, dir)

    def BuildWorkspace(self, debug : bool = False):
        """
        Clean and build bsp and app in workspace

        :param debug: Optional parameter. If true, the standard output is printed to the console. In this case the automatic checking for
                      errors is disabled, so it shall only be used for debugging purposes.
        """
        tclStr = ""
        tclStr += "projects -clean -type all\n"
        tclStr += "projects -build -type bsp -name {}\n".format(self.bspName)
        tclStr += "projects -build -type app -name {}\n".format(self.appName)
        self._RunSdk(tclStr, debug)

        #WORKAROUND: XSCT always copies all sources into the project (instead of linking them). So after building they
        #            must be copied back to ensure the original location contains correct files (e.g. the .mss file
        #            must be stored)
        self.CopyToSrcLoc()

    def CreateBitWithSw(self, appBuildConfig: str, procName: str, outFile: str):
        """
        Create a bit file that contains the freshly built software. This command can only be used after the
        ImportProjects() command was called.

        :param appBuildConfig: Application configuration to use (usually "Debug" or "Release")
        :param procName: Name of the processor to use (e.g. soc_i/microblaze_0)
        :param outFile: Path of the output .bit file to write (relative to the HW project dir)
        """
        with TempWorkDir("/".join([self.workspace, self.hwName])):
            mmi = list(filter(lambda x: x.endswith(".mmi"), os.listdir()))[0]
            prefix = mmi.split(".")[0]
            mmi = os.path.abspath(os.curdir) + "/" + mmi
            bitin = os.path.abspath(os.curdir) + "/" + prefix + ".bit"
        appDir = "/".join([self.workspace, self.appName, appBuildConfig])
        with TempWorkDir(appDir):
            try:
                elfName = list(filter(lambda x: x.endswith(".elf"), os.listdir()))[0]
            except IndexError:
                raise Exception("No ELF file found in application directory " + appDir)
            elf = os.path.abspath(os.curdir) + "/" + elfName
        with TempWorkDir("/".join([self.workspace, self.hwName])):
            call = ExtAppCall(".",
                              "{} -meminfo {} -data {} -bit {} -proc {} -out {} -force".format(self._updatememCmd, mmi,
                                                                                        elf, bitin, procName,
                                                                                        outFile))
            call.run_sync()
            self._UpdateStdOut(call)

    def CleanWorkpace(self):
        """
        Delete complete workspace
        """
        shutil.rmtree(self.workspace, ignore_errors=True)

    def ClearAllStdOut(self):
        """
        Clear the standard output history
        """
        self.allStdOut = ""

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
    def AllStdOut(self):
        """
        Get all standard output of all commands executed since the last execution of ClearAllStdOut().

        :return: stdout output
        """
        return self.allStdOut


    ####################################################################################################################
    # Private Methods
    ####################################################################################################################
    def _UpdateStdOut(self, call : ExtAppCall):
        self.stderr = call.get_stderr()
        self.stdout = call.get_stdout()
        self.allStdOut += self.stdout
        #Remove expected error messages
        stderr = self.stderr
        stderr = stderr.replace("Xlib:  extension \"RANDR\" missing on display \":1\".","").strip() #Expected error from xvfb
        if len(stderr) != 0:
            raise SdkStdErrNotEmpty("STDERR not empty:\n<includes expected errors!>\n" + self.stderr)
        if call.get_exit_code() != 0:
            raise SdkExitCodeNotZero("Command exited with code {}".format(call.get_exit_code()))


    def _SetPaths(self):
        if sys.platform.startswith("win"):
            os.environ["PATH"] += ";{}/bin".format(self._sdk_path).replace("/", "\\")
            os.environ["PATH"] += ";{}/gnu/microblaze/nt/bin".format(self._sdk_path).replace("/", "\\")
            os.environ["PATH"] += ";{}/gnu/arm/nt/bin".format(self._sdk_path).replace("/", "\\")
            os.environ["PATH"] += ";{}/gnu/microblaze/linux_toolchain/nt64_be/bin".format(self._sdk_path).replace("/", "\\")
            os.environ["PATH"] += ";{}/gnu/aarch32/nt/gcc-arm-linux-gnueabi/bin".format(self._sdk_path).replace("/", "\\")
            os.environ["PATH"] += ";{}/gnu/aarch32/nt/gcc-arm-none-eabi/bin".format(self._sdk_path).replace("/", "\\")
            os.environ["PATH"] += ";{}/gnu/aarch64/nt/aarch64-linux/bin".format(self._sdk_path).replace("/", "\\")
            os.environ["PATH"] += ";{}/gnu/aarch64/nt/aarch64-none/bin".format(self._sdk_path).replace("/", "\\")
            os.environ["PATH"] += ";{}/gnu/armr5/nt/gcc-arm-none-eabi/bin".format(self._sdk_path).replace("/", "\\")
            os.environ["PATH"] += ";{}/tps/win64/cmake-3.3".format(self._sdk_path).replace("/", "\\")
            self._xsctCmd = "xsct.bat"
            self._updatememCmd = "updatemem.bat"
        elif sys.platform.startswith("linux"):
            os.environ["PATH"] += ":{}/bin".format(self._sdk_path)
            os.environ["PATH"] += ":{}/gnu/microblaze/lin/bin".format(self._sdk_path)
            os.environ["PATH"] += ":{}/gnu/arm/lin/bin".format(self._sdk_path)
            os.environ["PATH"] += ":{}/gnu/microblaze/linux_toolchain/lin64_le/bin".format(self._sdk_path)
            os.environ["PATH"] += ":{}/gnu/aarch32/lin/gcc-arm-linux-gnueabi/bin".format(self._sdk_path)
            os.environ["PATH"] += ":{}/gnu/aarch32/lin/gcc-arm-none-eabi/bin".format(self._sdk_path)
            os.environ["PATH"] += ":{}/gnu/aarch64/lin/aarch64-linux/bin".format(self._sdk_path)
            os.environ["PATH"] += ":{}/gnu/aarch64/lin/aarch64-none/bin".format(self._sdk_path)
            os.environ["PATH"] += ":{}/gnu/armr5/lin/gcc-arm-none-eabi/bin".format(self._sdk_path)
            os.environ["PATH"] += ":{}/tps/lnx64/cmake-3.3".format(self._sdk_path)
            # required to suppress non-real error message related to graphics framework (tool bug), Xvfb must be running
            os.environ["DISPLAY"] = ":1"
            self._xsctCmd = "xsct"
            self._updatememCmd = "updatemem"
        else:
            raise Exception("Unsupported OS")

    def _RunSdk(self, tclString : str, debug : bool = False):
        with TempWorkDir(self.workspace):
            with TempFile("__sdk.tcl") as f:
                #Write Temporary TCL
                f.write("setws .\n")    #Set workspace
                f.write(tclString)
                f.flush()
                if not debug:
                    call = ExtAppCall(".", "{}  __sdk.tcl".format(self._xsctCmd))
                    call.run_sync()
                    self._UpdateStdOut(call)
                else:
                    os.system("{}  __sdk.tcl".format(self._xsctCmd))

