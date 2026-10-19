"""HWP 5.0 binary helpers: record (de)serialization + minimal Compound File (CFB v3) writer."""
import struct, zlib, olefile

# ---------- records ----------
def parse_records(data):
    out, i = [], 0
    while i < len(data):
        h, = struct.unpack_from('<I', data, i); i += 4
        tag, lvl, size = h & 0x3FF, (h >> 10) & 0x3FF, (h >> 20) & 0xFFF
        if size == 0xFFF:
            size, = struct.unpack_from('<I', data, i); i += 4
        out.append([tag, lvl, data[i:i + size]]); i += size
    return out


def dump_records(recs):
    b = bytearray()
    for tag, lvl, p in recs:
        n = len(p)
        if n >= 0xFFF:
            b += struct.pack('<II', tag | (lvl << 10) | (0xFFF << 20), n)
        else:
            b += struct.pack('<I', tag | (lvl << 10) | (n << 20))
        b += p
    return bytes(b)


def inflate(b):
    return zlib.decompress(b, -15)


def deflate(b):
    c = zlib.compressobj(9, zlib.DEFLATED, -15)
    return c.compress(b) + c.flush()


def read_hwp(path):
    o = olefile.OleFileIO(path)
    streams = {}
    for e in o.listdir(streams=True, storages=False):
        streams['/'.join(e)] = o.openstream(e).read()
    return streams


# ---------- CFB writer ----------
SECT, MINI, CUTOFF = 512, 64, 4096
FREE, ENDC, FATS = 0xFFFFFFFF, 0xFFFFFFFE, 0xFFFFFFFD


def _key(name):
    return (len(name), name.upper())


def write_cfb(path, streams):
    """streams: {'A/B/name': bytes}. Storages are created from paths."""
    # build tree
    root = {'name': 'Root Entry', 'type': 5, 'kids': {}, 'data': b''}
    for p, data in streams.items():
        parts = p.split('/')
        node = root
        for s in parts[:-1]:
            node = node['kids'].setdefault(s, {'name': s, 'type': 1, 'kids': {}, 'data': b''})
        node['kids'][parts[-1]] = {'name': parts[-1], 'type': 2, 'kids': {}, 'data': data}
    entries = []

    def add(n):
        n['id'] = len(entries); entries.append(n)
        for k in sorted(n['kids'].values(), key=lambda x: _key(x['name'])):
            add(k)
    add(root)

    # sibling trees: balanced BST over sorted kids
    def bst(kids):
        if not kids:
            return FREE
        m = len(kids) // 2
        n = kids[m]
        n['left'] = bst(kids[:m]); n['right'] = bst(kids[m + 1:])
        return n['id']
    for n in entries:
        n.setdefault('left', FREE); n.setdefault('right', FREE)
    for n in entries:
        n['child'] = bst(sorted(n['kids'].values(), key=lambda x: _key(x['name']))) if n['type'] != 2 else FREE
        for k in n['kids'].values():
            k.setdefault('left', FREE); k.setdefault('right', FREE)
    for n in entries:
        n['child'] = bst(sorted(n['kids'].values(), key=lambda x: _key(x['name']))) if n['type'] != 2 else FREE

    # mini stream
    mini = bytearray(); minifat = []
    big = []
    for n in entries:
        if n['type'] != 2:
            continue
        d = n['data']
        if len(d) < CUTOFF:
            start = len(mini) // MINI
            cnt = max(1, -(-len(d) // MINI)) if d else 0
            if cnt == 0:
                n['start'] = ENDC
            else:
                n['start'] = start
                minifat += [start + i + 1 for i in range(cnt - 1)] + [ENDC]
                mini += d + b'\0' * (cnt * MINI - len(d))
        else:
            big.append(n)
        n['size'] = len(d)
    root['data'] = bytes(mini)

    # sector allocation: [directory][minifat][ministream][big streams][fat]
    sectors = []  # list of bytes chunks, each SECT
    fat = []

    def alloc(data):
        if not data:
            return ENDC
        cnt = -(-len(data) // SECT)
        start = len(sectors)
        for i in range(cnt):
            sectors.append(data[i * SECT:(i + 1) * SECT].ljust(SECT, b'\0'))
            fat.append(start + i + 1 if i < cnt - 1 else ENDC)
        return start

    # directory bytes built later (needs starts) -> reserve
    ndir = -(-len(entries) * 128 // SECT)
    dir_start = len(sectors)
    for i in range(ndir):
        sectors.append(b'\0' * SECT); fat.append(dir_start + i + 1 if i < ndir - 1 else ENDC)
    mf = b''.join(struct.pack('<I', x) for x in minifat)
    minifat_start = alloc(mf) if mf else ENDC
    nminifat = -(-len(mf) // SECT)
    root['start'] = alloc(bytes(mini)) if mini else ENDC
    root['size'] = len(mini)
    for n in big:
        n['start'] = alloc(n['data'])
    # FAT sectors
    nfat = 1
    while True:
        total = len(sectors) + nfat
        if nfat * (SECT // 4) >= total:
            break
        nfat += 1
    fat_start = len(sectors)
    for i in range(nfat):
        fat.append(FATS)
    fat += [FREE] * (nfat * (SECT // 4) - len(fat))
    fatb = b''.join(struct.pack('<I', x) for x in fat)
    for i in range(nfat):
        sectors.append(fatb[i * SECT:(i + 1) * SECT])
    assert nfat <= 109
    # directory
    db = bytearray()
    for n in entries:
        nm = n['name'].encode('utf-16le') + b'\0\0'
        e = bytearray(128)
        e[0:len(nm)] = nm
        struct.pack_into('<H', e, 64, len(nm))
        e[66] = n['type']; e[67] = 1  # black
        struct.pack_into('<III', e, 68, n['left'], n['right'], n['child'])
        struct.pack_into('<I', e, 116, n.get('start', ENDC) if n['type'] != 1 else 0)
        struct.pack_into('<I', e, 120, n.get('size', 0) if n['type'] != 1 else 0)
        db += e
    db += b'\0' * (ndir * SECT - len(db))
    for i in range(len(entries), ndir * 4):
        struct.pack_into('<III', db, i * 128 + 68, FREE, FREE, FREE)
    for i in range(ndir):
        sectors[dir_start + i] = bytes(db[i * SECT:(i + 1) * SECT])
    # header
    h = bytearray(512)
    h[0:8] = bytes.fromhex('D0CF11E0A1B11AE1')
    struct.pack_into('<HHHHH', h, 24, 0x3E, 3, 0xFFFE, 9, 6)
    struct.pack_into('<I', h, 44, nfat)
    struct.pack_into('<I', h, 48, dir_start)
    struct.pack_into('<I', h, 56, CUTOFF)
    struct.pack_into('<II', h, 60, minifat_start, nminifat)
    struct.pack_into('<II', h, 68, ENDC, 0)
    difat = [fat_start + i for i in range(nfat)] + [FREE] * (109 - nfat)
    struct.pack_into('<109I', h, 76, *difat)
    with open(path, 'wb') as f:
        f.write(h); f.write(b''.join(sectors))
