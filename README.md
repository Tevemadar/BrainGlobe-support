# BrainGlobe support

Python converters for using atlases from https://brainglobe.info with NeSys utilities (actual list of atlases is [here](https://brainglobe.info/documentation/brainglobe-atlasapi/usage/atlas-details.html)). For QuickNII and VisuAlign so far. Partially Nutil (NIfTI and label files are generated).

## QUINT converter - `mkquint.py`

This is the preferred converter, it tries to make all the data files (cutlas, NIfTI, label), accompanied by complete QuickNII and VisuAlign packages (this part is for Windows/Linux only).

Prerequisites are BrainGlobe Atlas API, NiBabel, and tqdm:  
`pip install --upgrade brainglobe-atlasapi nibabel tqdm`

Supply atlas identifier as command-line parameter:  
`python mkquint.py allen_mouse_25um`

Expected output files are:

- `allen_mouse_25um.cutlas` - QuickNII data file that can be copied into an existing QuickNII distribution if the creation of whole QuickNII software package fails
- `allen_mouse_25um.nii.gz` - a standard NIfTI volume containing the segmentation of the given atlas
- `allen_mouse_25um.txt` - ITK label file for the segmentation
- `allen_mouse_25um.zip` - atlas package that can be uncompressed into an existing VisuAlign distribution if the creation of whole VisuAlign software package fails. This file contains an `allen_mouse_25um.cutlas` folder that then contains the previous two files renamed as `labels.nii.gz` and `labels.txt` respectively
- `QuickNII-allen_mouse_25um.zip` - complete QuickNII software package with the converted atlas
- `VisuAlign-allen_mouse_25um.zip` - complete VisuAlign software package with the converted atlas.

Creation of the two software packages is subject to availability of their base packages on EBRAINS. If they fail, see "QuickNII cutlas creator" and "VisuAlign package creator" sections below about how the data files can be added to an existing software package.

Optional command line parameters:

- `nocompress` - apply 0-level ("STORE") compression. This parameter exists to save time when experimenting with new atlases, conversion is significantly faster this way. After an atlas turns out to be usable with QuickNII, it's advisable to re-run conversion without this parameter
- `skipextras` - do not pack additional references. Try using this parameter if QuickNII reports running out of memory at startup (and additional reference volumes exist at all)
- `nomp` - if the converter itself fails because of running out of memory, this switch may help
- `debug` - extra log messages about progress.

Non-trivial features:

- label colors are made distinct for QuickNII, the enforced distance is `|r1-r2| + |g1-g2| + |b1-b2| >= 10`
- missing labels are added and reported
- packing of additional references where available (also see `skipextras` parameter above)
- rudimentary license information is provided for QuickNII (atlas specification, homepage, citation/doi).

Tested with a couple atlases only, `allen_mouse_25um`, `whs_sd_rat_39um`, `kim_dev_mouse_e18-5_lsfm_20um`, `azba_zfish_4um`, `mpin_zfish_1um` (this atlas has an incomplete distribution in 2026 October), `allen_human_500um`.  
`unam_axolotl_40um` was used to develop the color distinction feature.  
`demba_allen_seg_dev_mouse_p4_25um` was used for developing and testing support for additional references. Coincidentally this was the atlas requiring introduction of support for unspecified labels too.  
`azba_zfish_4um` was used for recognizing and supporting single-byte segmentations.

Known limitations:

- QuickNII needs isotropic (or near-isotropic) resolution (it will load non-isotropic atlases, but they won't really work)
- template volumes are unconditionally converted into a 16-bit format, this may cause QuickNII run out of memory sooner than the theoretical limit (bit less than 2 gigavoxels).

## QuickNII cutlas creator - `makecutlas.py`

Install BrainGlobe Atlas API: 
`pip install --upgrade brainglobe-atlasapi`

Supply atlas identifier as command-line parameter: 
`python makecutlas.py allen_mouse_25um`

Expected output is `allen_mouse_25um.cutlas` for the example. It then can be copied into any QuickNII release.

Launching the atlas with QuickNII:
 - either as command-line parameter (e.g. `QuickNII.exe allen_mouse_25um.cutlas`)
 - or edit `pack.txt` (next to QuickNII.exe) to contain the name of the new file (`allen_mouse_25um.cutlas`). Without any trailing characters (not even a line-break).

Optional command line parameters:

 - `nocompress` - apply 0-level ("STORE") compression. This parameter exists to save time when experimenting with new atlases, conversion is significantly faster this way). After an atlas turns out to be usable with QuickNII, it's advisable to re-run conversion without this parameter
 - `skipextras` - do not pack additional references. Try using this parameter if additional reference volumes exist at all and QuickNII reports running out of memory at startup.

Non-trivial features:

 - label colors are made distinct, the enforced distance is `|r1-r2| + |g1-g2| + |b1-b2| >= 10`
 - missing labels are added and reported
 - packs additional references where available (also see `skipextras` parameter above).

Tested with a couple atlases only, `allen_mouse_25um`, `whs_sd_rat_39um`, `kim_dev_mouse_e18-5_lsfm_20um`, `azba_zfish_4um`, `mpin_zfish_1um` (this atlas has an incomplete distribution in 2026 October).  
`unam_axolotl_40um` was used to develop the color distinction feature.  
`demba_allen_seg_dev_mouse_p4_25um` was used for developing and testing support for additional references. Coincidentally this was the atlas requiring introduction of support for unspecified labels too.  
`azba_zfish_4um` was used for recognizing and supporting single-byte segmentations.

Known limitations:

 - QuickNII needs isotropic (or near-isotropic) resolution (it will load non-isotropic atlases, but they won't really work)
 - template volumes are unconditionally converted into a 16-bit format, that may run out of memory sooner than the theoretical limit (bit less than 2 gigavoxels)
 - license information is not emitted yet.

## VisuAlign package creator - `makenifti.py`

Install BrainGlobe Atlas API and NiBabel: 
`pip install --upgrade brainglobe-atlasapi nibabel`

Supply atlas identifier as command-line parameter: 
`python makenifti.py allen_mouse_25um`

Expected outputs for this example are:

 - `allen_mouse_25um.nii.gz` - a standard NIfTI volume containing the segmentation of the given atlas
 - `allen_mouse_25um.txt` - ITK label file for the segmentation
 - `allen_mouse_25um.zip` - atlas package that can be uncompressed into VisuAlign (it contains an `allen_mouse_25um.cutlas` folder that then contains the previous two files renamed as `labels.nii.gz` and `labels.txt` respectively).

This converter also completes the label file with any unspecified label identifiers it encounters. Colors are not made distinct though, as VisuAlign has a fully functional "outline" view.

Known quirks:

 - no remapping is applied, output volume uses 32-bit unsigned integers without checking if they're really needed - the compressed file itself still remains small, because it contains mostly zero values
 - however, if the NIfTI is used with ITK Snap, it may end up truncating label values, and its label-value limit can be reached too (a known atlas to trigger this is the adult Allen Mouse Brain Atlas)
 - transformation code fields are incomplete.
