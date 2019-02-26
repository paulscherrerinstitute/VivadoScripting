## 4.0.0
* Non-reverse compatible changes
  * Modified *\_\_init\_\_.py* to import classes without specifying their file-name.
    * Old form: *from IseScripting.Build.Ise import Ise*
    * New form: *from IseScripting.Build import Ise*
* New Features
  * Added packaging script and distribute as PIP package

## 3.0.0
* First open-source release (older history discarded)
* Changes (not reverse compatible)
  * Upgraded PsiPyUtils to version 2.0.0

## 2.0.3
* New Features
  * None
* Bugfixes
  * Write back projects after building them in a new workspace (required since .mss must be updated)

## 2.0.2
* New Features
  * None
* Bugfixes
  * Removed workaround to run *import HW* in SDK twice (this was not a tool-bug but a bug in a PSI makefile, so the workaround is not required)

## 2.0.1
* New Features
  * None
* Bugfixes
  * Sdk.CreateBitWithSw() did not overwrite existing bitstreams. This is now fixed.

## 2.0.0
* New Features
  * None
* Bugfixes
  * None
* Changes
  * Changed directory structure to cleanly organize different kinds of scripts

## 1.1.0
* New Features
  * Added ILA parsers to this repository
* Bugfixes
  * None

## 1.0.0
* First release