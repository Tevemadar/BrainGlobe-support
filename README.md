# BrainGlobe support

Python converters for using atlases from https://brainglobe.info with NeSys utilities (actual list of atlases is [here](https://brainglobe.info/documentation/brainglobe-atlasapi/usage/atlas-details.html)). So far a single one.

## QuickNII cutlas creator

Install BrainGlobe Atlas API if needed: 
`pip install brainglobe-atlasapi`

Supply atlas identifier as command-line parameter: 
`python makecutlas.py allen_mouse_25um`

Expected output is `allen_mouse_25um.cutlas` for the example. It then can be copied into any QuickNII release. 
Launching the custom atlas with QuickNII:
 - either as command-line parameter (e.g. `QuickNII.exe allen_mouse_25um.cutlas`)
 - or edit `pack.txt` (next to QuickNII.exe) to contain the name of the new file (`allen_mouse_25um`). Without any trailing characters (not even a line-break).

Tested with a couple atlases only, allen_mouse_25um, whs_sd_rat_39um, kim_dev_mouse_e18-5_lsfm_20um.

Known limitations:

 - QuickNII needs isotropic (or near-isotropic) resolution (it will load non-isotropic atlases, but they won't really work)
 - atlases are unconditionally converted into a 4-volume format (2-byte template and 2-byte segmentation), that runs out of memory sooner than the theoretical limit (bit less than 2 gigavoxels)
 - license information is not emitted yet
 - single template - single segmentation.
