import setuptools
import shutil
import os
from setuptools.command.sdist import sdist


#Cleanup before sdist
class CustomSdist(sdist):
    def run(self):
        #Cleanup before building
        shutil.rmtree("dist", ignore_errors=True)

        #Build from directory above
        sdist.run(self)

#Package
setuptools.setup(
    name="VivadoScripting",
    version="3.0.0",
    author="Oliver Bründler",
    author_email="oliver.bruendler@psi.ch",
    description="Tools to easily script Xilinx vivado from Python",
    license="PSI HDL Library License, Version 1.0",
    url="https://github.com/paulscherrerinstitute/VivadoScripting",
    package_dir = {"VivadoScripting" : "."},
    packages = ["VivadoScripting", "VivadoScripting.BuildScripts", "VivadoScripting.IlaParsers.I2c"],
    install_requires = [
        "PsiPyUtils",
        "typing"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent"
    ],
    cmdclass = {
        "sdist" : CustomSdist
    }
)