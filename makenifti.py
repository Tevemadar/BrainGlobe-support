import brainglobe_atlasapi, numpy, nibabel, sys, zipfile

print("Loading atlas")
atlas = brainglobe_atlasapi.bg_atlas.BrainGlobeAtlas(sys.argv[1])
(ydim, zdim, xdim) = atlas.shape
print(f"Shape: {atlas.shape}")

print("Building NIfTI")
hdr = nibabel.Nifti1Header()
hdr.set_data_dtype("uint32")
hdr.set_data_shape((xdim, ydim, zdim))
hdr.set_sform([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], 2)
nii = nibabel.Nifti1Image(numpy.flip(numpy.transpose(atlas.annotation, (2, 0, 1))), None, header = hdr)
print("Writing NIfTI")
nibabel.openers.Opener.default_compresslevel = 9
nibabel.save(nii, atlas.atlas_name + ".nii.gz")

print("Writing label file")
with open(atlas.atlas_name + ".txt", "w") as f:
    f.write(
"""################################################
# ITK-SnAP Label Description File
# File format: 
# IDX   -R-  -G-  -B-  -A--  VIS MSH  LABEL
# Fields: 
#    IDX:   Zero-based index 
#    -R-:   Red color component (0..255)
#    -G-:   Green color component (0..255)
#    -B-:   Blue color component (0..255)
#    -A-:   Label transparency (0.00 .. 1.00)
#    VIS:   Label visibility (0 or 1)
#    IDX:   Label mesh visibility (0 or 1)
#  LABEL:   Label description 
################################################
    0     0    0    0        0  0  0    "Clear Label"
""")
    for structure in atlas.structures_list:
        id = structure["id"]
        if id != 0:
            rgb = structure["rgb_triplet"]
            f.write(f"{id:5} {rgb[0]:5} {rgb[1]:4} {rgb[2]:4}        1  1  0    \"{structure["name"]}\"\n")

print("Creating package")
with zipfile.ZipFile(atlas.atlas_name + ".zip", "w") as zf:
    zf.write(atlas.atlas_name + ".nii.gz", arcname = atlas.atlas_name + ".cutlas/labels.nii.gz")
    zf.write(atlas.atlas_name + ".txt", arcname = atlas.atlas_name + ".cutlas/labels.txt")
