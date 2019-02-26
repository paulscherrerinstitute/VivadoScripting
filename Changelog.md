## 3.0.0
* Non-reverse compatible changes
  * Modified *\_\_init\_\_.py* to import classes without specifying their file-name.
    * Old form: *from VivadoScripting.BuildScripts.Sdk import Sdk*
    * New form: *from VivadoScripting.BuildScripts import Sdk*
* New Features
  * Added packaging script and distribute as PIP package

## 2.0.0
* First open-source release (older history discarded)
* Changes (not reverse compatible)
  * Upgraded PsiPyUtils to version 2.0.0

## 1.1.1
* Features
  * None
* Bugfixes
  * Bulid using interactive XPS shell sometimes failed on linux. This was fixed by using XPS in tcl mode (script evaluation).
* Dependencies
  * Removed dependency to python PIP package *pexpect*
  * Required *Utils* >= 1.1.1

## 1.1.0
* Features
  * Implemented ISE project navigator flow
* Bugfixes
  * None

## 1.0.0
* First release (EDK, SDK, Tools)