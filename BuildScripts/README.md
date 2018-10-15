# Building with Jenkins

The XSCT that is used for building SDK projects requires an X11 framework to be present. Since Jenkins runs on a server that does not have X11 installed, we use a virtual frame buffer to make XSCT work. To do so, enable Xvfb in the Jenkins job.

*Build Environment > Start Xvfb before the build, and shut it down after.*

# Known Issues

## Case Sensitivity of Paths

Vivado has some issues with the case sensitivity of paths. On Windows paths are not case sensitive, so Vivado seems not to maintain case correctness in .xpr files if they are created on Windows. If the same project is built on Linux, the build fails because Linux is case sensitive and the path in the .xpr is therefore wrong.

To ensure a project can be built on Linux and Windows, it is recommended to use only lower-case folder- and file-names inside the Vivado project. This mainly affects the path to the .bd File since everything else is packed into IP-Cores. Within packaged IP-Cores, case correctness of the paths seems to be maintained on Windows and Linux, so in IP-Cores there is no problem.

## Error Handling
The error handling in the build-scripts is not yet perfect. The build fails if any errors in Vivado or SDK occur but the details about the errors are not forwarded to the console. For details about the errors, the log-files of the tools must be consulted.

# Build Script Usage

## Build a Vivado Project
```
#Configure
#  VIVADO_2017_2: Environment variable pointing to the Vivado installation (e.g. C:\Xilinx\Vivado\2017.2)
#  2017.2:        String for the version. This is required to handle differences between vivado versions
viv = Vivado("VIVADO_2017_2", "2017.2")

#Only required for TCL based flow, if the XPR is present, this line can be omitted
viv.ExecuteTcl("<tclPath>", "project.tcl")

#Build project
viv.BuildXpr("<xprPath>", project.xpr, generateBd=True)

#Check if errors or critical warnings occured and if timig is OK (optional)
if len(viv.errors) > 0:
    raise Exception("Errors Occured during build!")
if len(viv.criticalWarnings) > 0:
    raise Exception("Critical Warnings Occured during build!")
if viv.WHS < 0 or viv.WNS < 0:
    raise Exception("Timing not met!")
    
#Export HDF File (only required if SDK is executed too)
viv.ExportHdf("<xprPath>", project.xpr, "./build.hdf")

```

## Create a Flash Image from Multiple Bitstreams
```
#Configure
#  VIVADO_2017_2: Environment variable pointing to the Vivado installation (e.g. C:\Xilinx\Vivado\2017.2)
#  2017.2:        String for the version. This is required to handle differences between vivado versions
viv = Vivado("VIVADO_2017_2", "2017.2")

#Configure address mapping of the bitstreams
bitstreams = {0x00000000 : ./path/to/bitstreamA.bit,
              0x01400000 : ./path/to/bitstreamB.bit}
viv.CreateFlashImage(bitstreams, "sls_dbpm3.bin", 64)

#Print output of the process (optional)
print(viv.stdout)
```

## Build an SDK Project
```
#Configure
#  SDK_2017_2: Environment variable pointing to the Vivado installation (e.g. C:\Xilinx\SDK\2017.2)
#  2017.2:        String for the version. This is required to handle differences between SDK versions
sdk = Sdk("SDK_2017_2", "2017.2")

#Create workspace and import projects
sdk.CreateEmtpyWorkspace("build_ws")
sdk.ImportProjects(hwPath="./soc.sdk/soc_wrapper_hw_platform_0",
                           bspPath="./soc.sdk/bsp",
                           appPath="./soc.sdk/sw")
                           
#Update HW platform specificiation (from Vivado)
sdk.UpdateHwSpec("./build.hdf")

#Build complete workspace (BSP and SW project)
sdk.BuildWorkspace()

#Update bitstream with the SW binary
sdk.CreateBitWithSw("Debug", "soc_i/microblaze_0", "./output.bit")
```



