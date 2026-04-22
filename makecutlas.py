import brainglobe_atlasapi, struct, sys, zlib, random

print("Loading atlas")
atlas = brainglobe_atlasapi.bg_atlas.BrainGlobeAtlas(sys.argv[1])
(ydim, zdim, xdim) = atlas.shape
print(f"Shape: {atlas.shape}")

if xdim * ydim * zdim > 0x7FFFFFF0:
    print("Atlas can't be packed into cutlas.")
    sys.exit()

random.seed(0)
print("Building annotations")
palette = bytearray()
remap = {0:0}
# colors = []
# for structure in atlas.structures_list:
#     id = structure["id"]
#     if id != 0:
#         basecolor = structure["rgb_triplet"]
#         color = basecolor
#         similar = True
#         attempt = 0
#         print(structure["name"], end = "\r")
#         while similar:
#             similar = False
#             for existing in colors:
#                 if sum(abs(a-b) for (a,b) in zip(color,existing)) < 10:
#                     attempt += 1
#                     color = [min(255,max(0,component+random.randint(-attempt,attempt))) for component in basecolor]
#                     print("Recoloring", structure["name"], attempt, basecolor, color, end = "\r")
#                     similar = True
#                     break
#         print()
#         colors.append(color)
blocked = set()
for structure in atlas.structures_list:
    id = structure["id"]
    if id != 0:
        print(structure["name"], end = "\r")
        basecolor = tuple(structure["rgb_triplet"])
        color = basecolor
        attempt = 0
        while color in blocked:
            attempt += 1
            color = tuple([min(255,max(0,component+random.randint(-attempt,attempt))) for component in basecolor])
            print("Recoloring", structure["name"], f"attempt #{attempt}", basecolor, color, end = "\r")
        print()
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
palette = struct.pack(f">H{len(palette)}s", len(remap)-1, palette)
palette = zlib.compress(palette, level = 9)
palette = struct.pack(f">I{len(palette)}s", len(palette), palette)

print("Building annotation image")
annotation = atlas.annotation
ahi = bytearray()
alo = bytearray()
for z in reversed(range(zdim)):
    print(z, end = " \r")
    for y in reversed(range(ydim)):
        for x in reversed(range(xdim)):
            v = remap[int(annotation[y, z, x])]
            alo.append(v & 255)
            ahi.append(v >> 8)

print("Compressing annotation image")
cahi = zlib.compress(ahi, level = 9)
calo = zlib.compress(alo, level = 9)

print("Building template image")
template = atlas.reference
minval = template.min()
maxval = template.max()
print(f"Range: {minval} - {maxval}")
template = (template - minval) * 65535.0 / (maxval - minval)

thi = bytearray()
tlo = bytearray()
for z in reversed(range(zdim)):
    print(z, end = " \r")
    for y in reversed(range(ydim)):
        for x in reversed(range(xdim)):
            v = int(template[y, z, x])
            tlo.append(v & 255)
            thi.append(v >> 8)

print("Compressing template image")
cthi = zlib.compress(thi, level = 9)
ctlo = zlib.compress(tlo, level = 9)

filename = atlas.atlas_name + ".cutlas"
print("Writing " + filename)
with open(filename, "wb") as f:
    f.write(b"v0")

    name = atlas.atlas_name
    name = name.encode("utf-8")
    name = struct.pack(f">H{len(name)}s", len(name), name)
    f.write(name)

    license = "<b>License placeholder</b>"
    license = license.encode("utf-8")
    license = struct.pack(f">H{len(license)}s", len(license), license)
    license = zlib.compress(license, level = 9, wbits = -15)
    license = struct.pack(f">I{len(license)}s", len(license), license)
    f.write(license)

    f.write(struct.pack(">HHH", xdim, ydim, zdim))

    f.write(struct.pack("B", 2))

    name = "Template"
    name = name.encode("utf-8")
    name = struct.pack(f">H{len(name)}s", len(name), name)
    head = struct.pack(f">B{len(name)}sBdd", 2, name, 0, minval, maxval)
    f.write(head)

    name = "Segmentation"
    name = name.encode("utf-8")
    name = struct.pack(f">H{len(name)}s", len(name), name)
    head = struct.pack(f">B{len(name)}sB", 4, name, 2)
    f.write(head)
    f.write(palette)

    f.write(struct.pack("B", 0))

    f.write(struct.pack("B", 4))

    f.write(struct.pack(">I", len(cthi)))
    f.write(cthi)
    f.write(struct.pack(">I", len(ctlo)))
    f.write(ctlo)

    f.write(struct.pack(">I", len(cahi)))
    f.write(cahi)
    f.write(struct.pack(">I", len(calo)))
    f.write(calo)
