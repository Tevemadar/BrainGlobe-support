print("Initializing")

import time
start = time.time()
def ts(msg):
    if "debug" in sys.argv:
        print(str(time.time() - start), __name__, msg)

import brainglobe_atlasapi, numpy, struct, sys, zlib, random, re
ts("Imports.")

compression = 0 if "nocompress" in sys.argv else 9

print("Loading atlas")
atlas = brainglobe_atlasapi.bg_atlas.BrainGlobeAtlas(sys.argv[1])
ts("Atlas object.")

(ydim, zdim, xdim) = atlas.shape
print(f"Dimensions: {atlas.shape}")

if xdim * ydim * zdim > 0x7FFFFFF0:
    print("Atlas can't be packed into cutlas.")
    sys.exit()

print("Building annotations")

# support for incomplete structure lists
unknownids = set(numpy.unique(atlas.annotation).tolist()) - {structure["id"] for structure in atlas.structures_list} - {0}
unknownlabels = [{"id": id, "name": f"Unknown label {id}", "rgb_triplet": [128, 128, 128]} for id in unknownids]

random.seed(0)
palette = bytearray()
remap = {0:0}
blocked = set()
for structure in atlas.structures_list + unknownlabels:
    id = structure["id"]
    if id != 0:
        print(" ", structure["name"], end = "\r")
        basecolor = tuple(structure["rgb_triplet"])
        color = basecolor
        attempt = 0
        while color in blocked:
            print("-\\|/"[attempt & 3], end = "\r")
            attempt += 1
            color = tuple([min(255,max(0,component+random.randint(-attempt,attempt))) for component in basecolor])
            # print("Recoloring", structure["name"], f"attempt #{attempt}", basecolor, color, end = "\r")
        # print()
        for a in range(0,10):
            for b in range(0,10-a):
                for c in range(0,10-a-b):
                    blocked.add((color[0]-a,color[1]-b,color[2]-c))
                    blocked.add((color[0]-a,color[1]-b,color[2]+c))
                    blocked.add((color[0]-a,color[1]+b,color[2]-c))
                    blocked.add((color[0]-a,color[1]+b,color[2]+c))
                    blocked.add((color[0]+a,color[1]-b,color[2]-c))
                    blocked.add((color[0]+a,color[1]-b,color[2]+c))
                    blocked.add((color[0]+a,color[1]+b,color[2]-c))
                    blocked.add((color[0]+a,color[1]+b,color[2]+c))
        remap[id] = len(remap)
        name = structure["name"]
        name = name.encode("utf-8")
        name = struct.pack(f">H{len(name)}s", len(name), name)
        palette.extend(struct.pack("3B", *color))
        palette.extend(name)
        print(" " * (len(structure["name"]) + 2), end = "\r")

if len(unknownids):
    print()
    print(f">>>> WARNING <<<<\nAtlas contains unspecified identifiers:\n{" ".join(str(id) for id in unknownids)}")
    print("These will appear in grayish shades and with name \"Unkown label <numerical id>\"")
    print()

palette = struct.pack(f">H{len(palette)}s", len(remap)-1, palette)
palette = zlib.compress(palette, level = 9)
palette = struct.pack(f">I{len(palette)}s", len(palette), palette)
ts("Palette.")

annotation = atlas.annotation
annotation = numpy.flip(atlas.annotation, (0, 1, 2))
annotation = numpy.swapaxes(annotation, 0, 1)
byteannotation = len(remap) < 256
cahi = bytearray()
calo = bytearray()
comphi = zlib.compressobj(level = compression)
complo = zlib.compressobj(level = compression)
for z in range(zdim):
    prg = int(50 * z / zdim)
    print("[", "*" * prg, " " * (50 - prg), "] ", z, "/", zdim, sep = "", end = " \r")
    for line in annotation[z]:
        lihi = bytearray()
        lilo = bytearray()
        for v in line:
            s = remap[v]
            lihi.append(s >> 8)
            lilo.append(s & 255)
        cahi += comphi.compress(lihi)
        calo += complo.compress(lilo)
cahi += comphi.flush()
calo += complo.flush()
print("[", "*" * 50, "] ", zdim, "/", zdim, sep = "")
ts("Annotation.")

ts(str(len(cahi)))
ts(str(len(calo)))

print("Building template image")
template = atlas.template
minval = template.min()
maxval = template.max()
print(f"Range: {minval} - {maxval}")
template = (template - minval) * 65535.0 / (maxval - minval)

template = template.astype(numpy.uint16)
template = numpy.flip(template, (0,1,2))
template = numpy.swapaxes(template, 0, 1)

thi = (template >> 8).astype(numpy.uint8).tobytes()
tlo = template.astype(numpy.uint8).tobytes()

ts("Compressing template image")
cthi = zlib.compress(thi, level = compression)
ctlo = zlib.compress(tlo, level = compression)
ts("Done.")

extras = []
if "skipextras" not in sys.argv:
    for extra in atlas.additional_references:
        print(f"Building {extra}")
        etemplate = atlas.additional_references[extra]
        eminval = etemplate.min()
        emaxval = etemplate.max()
        print(f"Range: {eminval} - {emaxval}")
        etemplate = (etemplate - eminval) * 65535.0 / (emaxval - eminval)

        etemplate = etemplate.astype(numpy.uint16)
        etemplate = numpy.flip(etemplate, (0,1,2))
        etemplate = numpy.swapaxes(etemplate, 0, 1)

        ehi = (etemplate >> 8).astype(numpy.uint8).tobytes()
        elo = etemplate.astype(numpy.uint8).tobytes()

        ts(f"Compressing {extra}")
        cehi = zlib.compress(ehi, level = compression)
        celo = zlib.compress(elo, level = compression)
        extras.append({"name": extra, "min": eminval, "max": emaxval, "hi": cehi, "lo": celo})
        ts("Done.")

filename = atlas.atlas_name + ".cutlas"
print("Writing " + filename)
with open(filename, "wb") as f:
    f.write(b"v0")

    name = atlas.atlas_name
    name = name.encode("utf-8")
    name = struct.pack(f">H{len(name)}s", len(name), name)
    f.write(name)

    citation = re.sub(r"(https://\S*)", r'<a href="\g<1>">\g<1></a>', atlas.metadata["citation"])

    license = f'''<b>{atlas.atlas_name.replace("_", " ").capitalize()} (v{atlas.metadata["version"]})</b>
    <br>
    <br><b>Species:</b> {atlas.metadata["species"]}
    <br><b>Link:</b> <a href="{atlas.metadata["atlas_link"]}">{atlas.metadata["atlas_link"]}</a>
    <br><b>Citation:</b> {citation}
    <br>
    <br>Generated from <a href="https://brainglobe.info/">BrainGlobe</a> package.
    '''
    license = license.encode("utf-8")
    license = struct.pack(f">H{len(license)}s", len(license), license)
    license = zlib.compress(license, level = 9, wbits = -15)
    license = struct.pack(f">I{len(license)}s", len(license), license)
    f.write(license)

    f.write(struct.pack(">HHH", xdim, ydim, zdim))

    f.write(struct.pack("B", 2 + len(extras)))

    name = "Template"
    name = name.encode("utf-8")
    name = struct.pack(f">H{len(name)}s", len(name), name)
    head = struct.pack(f">B{len(name)}sBdd", 2, name, 0, minval, maxval)
    f.write(head)

    name = "Segmentation"
    name = name.encode("utf-8")
    name = struct.pack(f">H{len(name)}s", len(name), name)
    head = struct.pack(f">B{len(name)}sB", 3 if byteannotation else 4, name, 2)
    f.write(head)
    f.write(palette)

    for i in range(len(extras)):
        extra = extras[i]
        name = extra["name"]
        name = name.encode("utf-8")
        name = struct.pack(f">H{len(name)}s", len(name), name)
        head = struct.pack(f">B{len(name)}sBdd", 2, name, 4 + 2 * i - (1 if byteannotation else 0), extra["min"], extra["max"])
        f.write(head)

    f.write(struct.pack("B", 0))

    f.write(struct.pack("B", 4 + 2 * len(extras) - (1 if byteannotation else 0)))

    f.write(struct.pack(">I", len(cthi)))
    f.write(cthi)
    f.write(struct.pack(">I", len(ctlo)))
    f.write(ctlo)

    if not byteannotation:
        f.write(struct.pack(">I", len(cahi)))
        f.write(cahi)
    f.write(struct.pack(">I", len(calo)))
    f.write(calo)

    for extra in extras:
        f.write(struct.pack(">I", len(extra["hi"])))
        f.write(extra["hi"])
        f.write(struct.pack(">I", len(extra["lo"])))
        f.write(extra["lo"])

if len(extras) > 0:
    print(f"\n>>>> INFO <<<<\n{len(extras)} additional templates were processed: {", ".join(list(atlas.additional_references.keys()))}")
    print("If this cutlas file makes QuickNII running out of memory, please add the command line parameter skipextras, like")
    print(f"{" ".join(sys.argv)} skipextras")

print("All done (", int(time.time() - start), "s)", sep = "")
