import time

if __name__ == "__main__":
    start = time.time()
    print("Initializing")

import brainglobe_atlasapi, io, lzma, nibabel, multiprocessing, numpy, random, re, struct, sys, time, tqdm, urllib.request, zipfile, zlib

atlasid = sys.argv[1]
cutlas = atlasid + ".cutlas"
quicknii = "QuickNII-" + atlasid + ".zip"
nifti = atlasid + ".nii.gz"
labels = atlasid + ".txt"
visualign = "VisuAlign-" + atlasid + ".zip"
debug = "debug" in sys.argv
compression = 0 if "nocompress" in sys.argv else 9
nomp = "nomp" in sys.argv
doextras = "skipextras" not in sys.argv

def main():
    def ts(msg):
        if debug:
            print(str(time.time() - start), __name__, msg)

    ts("Start")

    meta = checkatlas()
    ts("Atlas.")

    if nomp:
        makecutlas(start, meta)
        makenifti(start)
        if preparezip(start, "https://data-proxy.ebrains.eu/api/v1/buckets/quint-atlas-binaries/QuickNIIBase.zip.xz", quicknii):
            with zipfile.ZipFile(quicknii, mode = "a") as zw:
                zw.writestr("pack.txt", cutlas)
                zw.write(cutlas)
        else:
            print("QuickNII base package is unavailable, " + cutlas + " is created only.")
        print("Creating VisuAlign data files")
        if preparezip(start, "https://data-proxy.ebrains.eu/api/v1/buckets/quint-atlas-binaries/VisuAlignBase.zip.xz", visualign):
            with zipfile.ZipFile(visualign, mode = "a") as zw:
                zw.write(labels, arcname = cutlas + "/labels.txt")
                zw.write(nifti, arcname = cutlas + "/labels.nii.gz")
        else:
            print("VisuAlign base package is unavailable, data files are created only.")
    else:
        qq = multiprocessing.Queue()
        qp = multiprocessing.Process(target = preparezip, args = (start, "https://data-proxy.ebrains.eu/api/v1/buckets/quint-atlas-binaries/QuickNIIBase.zip.xz", quicknii, qq))
        qp.start()
        vq = multiprocessing.Queue()
        vp = multiprocessing.Process(target = preparezip, args = (start, "https://data-proxy.ebrains.eu/api/v1/buckets/quint-atlas-binaries/VisuAlignBase.zip.xz", visualign, vq))
        vp.start()
        np = multiprocessing.Process(target = makenifti, args = (start,))
        np.start()
        makecutlas(start, meta)

        if qq.get():
            with zipfile.ZipFile(quicknii, mode = "a") as zw:
                zw.writestr("pack.txt", cutlas)
                zw.write(cutlas)
        else:
            print("QuickNII base package is unavailable, " + cutlas + " is created only.")
        qp.join()

        np.join()
        if vq.get():
            with zipfile.ZipFile(visualign, mode = "a") as zw:
                zw.write(labels, arcname = cutlas + "/labels.txt")
                zw.write(nifti, arcname = cutlas + "/labels.nii.gz")
        else:
            print("VisuAlign base package is unavailable, data files are created only.")
        vp.join()

    print("All done (", int(time.time() - start), "s)", sep = "")

def preparezip(start, url, filename, q = None):
    def ts(msg):
        if debug:
            print(str(time.time() - start), __name__, msg)

    try:
        with urllib.request.urlopen(url) as f:
            data = f.read()

        ts("Base " + filename)
        data = lzma.decompress(data)

        ts("Pack " + filename)
        with zipfile.ZipFile(filename, mode = "w", compression = zipfile.ZIP_DEFLATED, compresslevel = compression) as zw:
            with zipfile.ZipFile(io.BytesIO(data)) as zr:
                for zi in zr.filelist:
                    zw.writestr(zi.filename, zr.read(zi))
        if q:
            q.put(True)
        return True
    except:
        if q:
            q.put(False)
        return False

def makenifti(start):
    def ts(msg):
        if debug:
            print(str(time.time() - start), __name__, msg)

    atlas = brainglobe_atlasapi.bg_atlas.BrainGlobeAtlas(atlasid)
    (ydim, zdim, xdim) = atlas.shape

    ts("Building NIfTI")
    hdr = nibabel.Nifti1Header()
    hdr.set_data_dtype("uint32")
    hdr.set_data_shape((xdim, ydim, zdim))
    hdr.set_sform([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], 2)
    nii = nibabel.Nifti1Image(numpy.flip(numpy.transpose(atlas.annotation, (2, 0, 1))), None, header = hdr)
    ts("Writing NIfTI")
    nibabel.openers.Opener.default_compresslevel = compression
    nibabel.save(nii, nifti)

    ts("Writing label file")
    with open(labels, "w") as f:
        f.write("""################################################
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

        # support for incomplete structure lists
        for unknown in set(numpy.unique(atlas.annotation).tolist()) - {structure["id"] for structure in atlas.structures_list} - {0}:
            f.write(f"{unknown:5}   128  128  128        1  1  0    \"Unknown label {unknown}\"\n")

    ts("Creating package")
    with zipfile.ZipFile(atlasid + ".zip", mode = "w") as zw:
        zw.write(labels, arcname = cutlas + "/labels.txt")
        zw.write(nifti, arcname = cutlas + "/labels.nii.gz")

def makecutlas(start, meta):
    if nomp:
        print("Building annotations")
        (palette, byteannotation, cahi, calo) = processannotations(start)

        print("Building primary template image")
        (minval, maxval, cthi, ctlo) = processtemplate(start)

        extras = []
        for extra in meta["extralist"]:
            print(f"Building {extra}")
            (eminval, emaxval, cehi, celo) = processtemplate(start, extra)
            extras.append({"name": extra, "min": eminval, "max": emaxval, "hi": cehi, "lo": celo})
    else:
        tq = multiprocessing.Queue()
        tp = multiprocessing.Process(target = processtemplate, args = (start, None, tq))
        tp.start()

        etasks = []
        for extra in meta["extralist"]:
            eq = multiprocessing.Queue()
            ep = multiprocessing.Process(target = processtemplate, args = (start, extra, eq))
            ep.start()
            etasks.append((extra, eq, ep))
                
        (palette, byteannotation, cahi, calo) = processannotations(start)

        print("Waiting for tasks to complete")
        
        (minval, maxval, cthi, ctlo) = tq.get()
        tp.join()
        
        extras = []
        for task in etasks:
            (eminval, emaxval, cehi, celo) = task[1].get()
            task[2].join()
            extras.append({"name": task[0], "min": eminval, "max": emaxval, "hi": cehi, "lo": celo})

    if nomp:
        print("Writing " + cutlas)

    with open(cutlas, "wb") as f:
        f.write(b"v0")

        name = atlasid
        name = name.encode("utf-8")
        name = struct.pack(f">H{len(name)}s", len(name), name)
        f.write(name)

        citation = re.sub(r"(https://\S*)", r'<a href="\g<1>">\g<1></a>', meta["citation"])
        license = f'''<b>{atlasid.replace("_", " ").capitalize()} (v{meta["version"]})</b>
        <br>
        <br><b>Species:</b> {meta["species"]}
        <br><b>Link:</b> <a href="{meta["link"]}">{meta["link"]}</a>
        <br><b>Citation:</b> {citation}
        <br>
        <br>Generated from <a href="https://brainglobe.info/">BrainGlobe</a> package.
        '''
        license = license.encode("utf-8")
        license = struct.pack(f">H{len(license)}s", len(license), license)
        license = zlib.compress(license, level = 9, wbits = -15)
        license = struct.pack(f">I{len(license)}s", len(license), license)
        f.write(license)

        f.write(struct.pack(">HHH", meta["xdim"], meta["ydim"], meta["zdim"]))

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

        volcnt = 3 if byteannotation else 4
        for extra in extras:
            name = extra["name"]
            name = name.encode("utf-8")
            name = struct.pack(f">H{len(name)}s", len(name), name)
            head = struct.pack(f">B{len(name)}sBdd", 2, name, volcnt, extra["min"], extra["max"])
            volcnt += 2
            f.write(head)

        f.write(struct.pack("B", 0))

        f.write(struct.pack("B", volcnt))

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
        print(f"\n>>>> INFO <<<<\n{len(extras)} additional {"template was" if len(extras) == 1 else "templates were"} processed: {", ".join(meta["extralist"])}")
        print("If this cutlas file makes QuickNII run out of memory, please add the command line parameter skipextras, like")
        print()
        print(f"{" ".join(sys.argv)} skipextras")
        print()

def processannotations(start, q = None):
    def ts(msg):
        if debug:
            print(str(time.time() - start), __name__, msg)

    atlas = brainglobe_atlasapi.bg_atlas.BrainGlobeAtlas(atlasid)
    zdim = atlas.shape[1]

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
    ts(str(len(remap)) + ", " + ("byte" if byteannotation else "word"))
    cahi = bytearray()
    calo = bytearray()
    comphi = zlib.compressobj(level = compression)
    complo = zlib.compressobj(level = compression)
    for z in tqdm.trange(zdim, ascii = " \N{LEFT HALF BLOCK}\N{FULL BLOCK}", unit = "slice"):
        if byteannotation:
            for line in annotation[z]:
                lilo = bytearray()
                for v in line:
                    s = remap[v]
                    lilo.append(s)
                calo += complo.compress(lilo)
        else:
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
    ts("Annotations.")

    ts(str(len(cahi)))
    ts(str(len(calo)))

    if q:
        q.put((palette, byteannotation, cahi, calo))
    return (palette, byteannotation, cahi, calo)

def processtemplate(start, extra = None, q = None):
    def ts(msg):
        if debug:
            print(str(time.time() - start), __name__, msg)

    atlas = brainglobe_atlasapi.bg_atlas.BrainGlobeAtlas(atlasid)

    template = atlas.template if not extra else atlas.additional_references[extra]
    minval = template.min()
    maxval = template.max()
    ts(f"{extra if extra else "template"} range: {minval} - {maxval}")
    template = (template - minval) * 65535.0 / (maxval - minval)

    template = template.astype(numpy.uint16)
    template = numpy.flip(template, (0,1,2))
    template = numpy.swapaxes(template, 0, 1)

    thi = (template >> 8).astype(numpy.uint8).tobytes()
    tlo = template.astype(numpy.uint8).tobytes()

    ts(f"Compressing {extra if extra else "template image"}")
    cthi = zlib.compress(thi, level = compression)
    ctlo = zlib.compress(tlo, level = compression)
    ts(f"{extra if extra else "Template"}.")

    if q:
        q.put((minval, maxval, cthi, ctlo))
    return (minval, maxval, cthi, ctlo)

def checkatlas():
    print("Checking atlas availability")
    atlas = brainglobe_atlasapi.bg_atlas.BrainGlobeAtlas(atlasid)
    (ydim, zdim, xdim) = atlas.shape
    print(f"Dimensions: {atlas.shape}")

    if xdim * ydim * zdim > 0x7FFFFFF0:
        print("Atlas can't be packed into cutlas.")
        sys.exit()

    extralist = []

    if not nomp:
        print("Checking annotations")
        _ = atlas.annotation
        print("Checking template")
        _ = atlas.template
        if doextras:
            for extra in atlas.additional_references:
                print(f"Checking {extra}")
                _ = atlas.additional_references[extra]
                extralist.append(extra)
    else:
        def checkannotation():
            atlas = brainglobe_atlasapi.bg_atlas.BrainGlobeAtlas(atlasid)
            _ = atlas.annotation
        print("Checking annotations")
        checkannotation()
        def checktemplate(extra = None):
            atlas = brainglobe_atlasapi.bg_atlas.BrainGlobeAtlas(atlasid)
            _ = atlas.template if not extra else atlas.additional_references[extra]
        print("Checking template")
        checktemplate()
        if doextras:
            for extra in atlas.additional_references:
                print(f"Checking {extra}")
                checktemplate(extra)
                extralist.append(extra)

    print("Preliminary checks complete.")

    return {
        "xdim": xdim,
        "ydim": ydim,
        "zdim": zdim,
        "extralist": extralist,
        "citation": atlas.metadata["citation"],
        "version": atlas.metadata["version"],
        "species": atlas.metadata["species"],
        "link": atlas.metadata["atlas_link"]
    }

if __name__ == "__main__":
    main()
