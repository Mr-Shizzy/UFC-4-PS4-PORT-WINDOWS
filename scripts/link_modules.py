"""Link the eboot with the game's bundled system modules into one probe image.

Successor of link_libc.py for several modules (default: libc.prx, then
libSceFios2.prx). Every module is placed after the previous one; imports of
all modules share one import table, so the C runtime can override any
function (host contracts first) and otherwise binds the native export.

Exports are matched by (NID, library identity, module identity). Imports of
libSceLibcInternal are served by libc.prx's same-NID exports: the internal
library is not shipped with the game and exposes the same functions.
Output: out/boot-linked.bin (format BBPROBE5) and out/link.json.
"""
import collections
import hashlib
import json
from pathlib import Path
import struct
from prepare import parse_self, span, unpack
from link_libc import encode_id

DEFAULT_MODULES = ('libc.prx', 'libSceFios2.prx')
FS_LOAD = bytes.fromhex('64488b042500000000')  # mov rax, fs:[0]


def module(path):
    source = path.read_bytes()
    elf, header, ph, _, missing = parse_self(source)
    dp = next(p for p in ph if p['type'] == 2)
    dynamic = []
    for pos in range(dp['offset'], dp['offset'] + dp['filesz'], 16):
        tag, value = unpack('<QQ', elf, pos)
        if not tag:
            break
        dynamic.append((tag, value))
    tags = dict(dynamic)
    lp = next(p for p in ph if p['type'] == 0x61000000)
    blob = span(elf, lp['offset'], lp['filesz'])
    strings = span(blob, tags[0x61000035], tags[0x61000037])

    def string(offset):
        span(strings, offset, 1)
        return strings[offset:strings.index(0, offset)].decode('ascii')
    libraries, modules = {}, {}
    for tag, value in dynamic:
        if tag in (0x61000013, 0x61000015, 0x6100000d, 0x6100000f):
            table = libraries if tag in (0x61000013, 0x61000015) else modules
            key = encode_id(value >> 48)
            identity = (string(value & 0xffffffff), (value >> 32) & 65535)
            if key in table and table[key] != identity:
                raise ValueError('conflicting module/library IDs')
            table[key] = identity

    def identity(name):
        parts = name.split('#')
        if len(parts) != 3:
            return None  # plain names such as module_start are not linkable
        n, lib, mod = parts
        return (n, libraries[lib], modules[mod])
    symbols = []
    table = span(blob, tags[0x61000039], tags[0x6100003f])
    for pos in range(0, len(table), 24):
        n, info, other, section, value, size = unpack('<IBBHQQ', table, pos)
        name = string(n)
        symbols.append(dict(name=name, type=info & 15, binding=info >> 4, section=section,
                            value=value, size=size, identity=identity(name) if name else None))
    relocations = []
    for ot, st in ((0x61000029, 0x6100002d), (0x6100002f, 0x61000031)):
        table = span(blob, tags[ot], tags[st])
        for pos in range(0, len(table), 24):
            target, info, addend = unpack('<QQq', table, pos)
            relocations.append((target, info & 0xffffffff, info >> 32, addend))
    return dict(elf=elf, header=header, ph=ph, tags=tags, symbols=symbols, relocs=relocations,
                identity=identity, libraries=libraries, modules=modules,
                sha256=hashlib.sha256(source).hexdigest(), missing=missing)


def patch_fs_loads(image, ph, base):
    """Rewrite initial-exec `mov rax, fs:[0]` to GS: glibc owns FS on Linux."""
    patched = 0
    for p in ph:
        if p['type'] != 1 or not p['flags'] & 1:
            continue
        start, end = base + p['vaddr'], base + p['vaddr'] + p['filesz']
        at = image.find(FS_LOAD, start, end)
        while at >= 0:
            image[at] = 0x65
            patched += 1
            at = image.find(FS_LOAD, at + len(FS_LOAD), end)
    return patched


def link(game, out, module_names=DEFAULT_MODULES):
    main = module(game / 'eboot.bin')
    raw = (out / 'boot.bin').read_bytes()
    magic, size, entry, ns, nr, ni, flags = unpack('<8s6Q', raw, 0)
    if magic != b'BBPROBE2':
        raise ValueError('linker expects freshly prepared BBPROBE2')
    pos = 56
    segments = [unpack('<3Q', raw, pos + i * 24) for i in range(ns)]
    pos += ns * 24
    names = [span(raw, pos + i * 128, 128).split(b'\0', 1)[0].decode() for i in range(ni)]
    pos += ni * 128
    relocs = [unpack('<QQqq', raw, pos + i * 32) for i in range(nr)]
    pos += nr * 32
    image = bytearray(span(raw, pos, size))
    if pos + size != len(raw):
        raise ValueError('unexpected boot trailer')

    identities = {main['identity'](name): i for i, name in enumerate(names)}
    main_libraries = {identity: key for key, identity in main['libraries'].items()}
    main_modules = {identity: key for key, identity in main['modules'].items()}

    def imported(symbol):
        key = symbol['identity']
        if key not in identities:
            n, lib, mod = key
            # Main-program spelling when the identity matches (existing host
            # tables use it); otherwise NID#library for new libraries.
            name = (f'{n}#{main_libraries[lib]}#{main_modules[mod]}'
                    if lib in main_libraries and mod in main_modules else f'{n}#{lib[0]}')
            identities[key] = len(names)
            names.append(name)
        return identities[key]

    exports, by_nid = {}, collections.defaultdict(list)
    table = []
    base = (size + 65535) & ~65535
    fs_patched = patch_fs_loads(image, main['ph'], 0)
    tls_module = 2
    for filename in module_names:
        m = module(game / 'sce_module' / filename)
        loads = [p for p in m['ph'] if p['type'] in (1, 0x61000010)]
        modsize = max(p['vaddr'] + p['memsz'] for p in loads)
        if base + modsize > 512 * 1024 * 1024:
            raise ValueError('linked image exceeds probe limit')
        image.extend(bytes(base + modsize - len(image)))

        def mapped(address, length=8, loads=loads):
            return any(p['vaddr'] <= address and address + length <= p['vaddr'] + p['memsz'] for p in loads)
        for p in loads:
            if p['filesz'] > p['memsz']:
                raise ValueError(f'{filename}: invalid segment size')
            image[base + p['vaddr']:base + p['vaddr'] + p['filesz']] = span(m['elf'], p['offset'], p['filesz'])
            segments.append((base + p['vaddr'], p['memsz'], p['flags']))
        tls = next((p for p in m['ph'] if p['type'] == 7), None)
        module_id = 0
        if tls:
            if tls['filesz'] > tls['memsz'] or not mapped(tls['vaddr'], tls['memsz']):
                raise ValueError(f'{filename}: unsupported TLS layout')
            module_id = tls_module
            tls_module += 1
        tls_relocations = 0
        for target, kind, symid, addend in m['relocs']:
            if not mapped(target):
                raise ValueError(f'{filename}: relocation outside image {target:#x}')
            target += base
            if kind == 8:
                relocs.append((target, 0, base + addend, 0))
            elif kind == 16:
                symbol = m['symbols'][symid]
                if symbol['name'] or symbol['type'] != 3 or addend or not module_id:
                    raise ValueError(f'{filename}: unsupported external TLS relocation')
                struct.pack_into('<Q', image, target, module_id)
                tls_relocations += 1
            elif kind in (1, 6, 7):
                symbol = m['symbols'][symid]
                if symbol['section']:
                    if symbol['section'] == 0xfff1:
                        struct.pack_into('<Q', image, target, symbol['value'] + addend)
                    else:
                        relocs.append((target, 0, base + symbol['value'] + addend, 0))
                elif not symbol['identity'] and symbol['binding'] == 2:
                    struct.pack_into('<Q', image, target, 0)  # weak undefined (module_start/stop)
                else:
                    rk = 2 if symbol['type'] == 1 else 1
                    if (rk == 1 and addend) or not 0 <= addend < 4096:
                        raise ValueError(f'{filename}: unsupported import addend')
                    relocs.append((target, rk, imported(symbol), addend))
            else:
                raise ValueError(f'{filename}: unsupported relocation type {kind}')
        count = 0
        for s in m['symbols']:
            if s['section'] and s['binding'] in (1, 2) and s['identity'] and s['type'] in (1, 2):
                if not mapped(s['value'], max(1, s['size'])):
                    raise ValueError(f'{filename}: export outside load segments')
                if s['identity'] in exports:
                    raise ValueError(f'{filename}: ambiguous export')
                entry_value = (base + s['value'], 2 if s['type'] == 1 else 1, filename)
                exports[s['identity']] = entry_value
                by_nid[(s['identity'][0], s['identity'][1][0])].append(entry_value)
                count += 1
        fs_patched += patch_fs_loads(image, m['ph'], base)
        table.append(dict(file=filename, base=base, size=modsize, init=base + m['tags'].get(12, 0),
                          tls_address=base + tls['vaddr'] if tls else 0, tls_memsz=tls['memsz'] if tls else 0,
                          tls_filesz=tls['filesz'] if tls else 0, tls_module=module_id,
                          tls_relocations=tls_relocations, exports=count, sha256=m['sha256']))
        base = (base + modsize + 65535) & ~65535

    NID_ALIASES = {
        # pthread_rwlock -> scePthreadRwlock
        'iGjsr1WAtI0#libkernel': 'Ox9i0c7L5w0#libkernel',
        'sIlRvQqsN2Y#libkernel': 'mqdNorrB+gI#libkernel',
        'EgmLo6EWgso#libkernel': '+L98PIbGttk#libkernel',
    }

    EMBEDDED_STUBS = {
        # sceAppContentGetPftFlag(uint32_t *flag): if (rdi) *rdi = 0; return 0;
        'xmhnAoxN3Wk#libSceAppContentPft': bytes.fromhex('4885ff7406c7070000000031c0c3'),
        'xmhnAoxN3Wk#libSceAppContent': bytes.fromhex('4885ff7406c7070000000031c0c3'),
        # sceKernelIsProspero(): return 0 (not PS5)
        'mpxAdqW7dKY#libkernel_cpumode_platform': bytes.fromhex('31c0c3'),
        # sceRemoteplay*
        'k1SwgkMSOM8#libSceRemoteplay': bytes.fromhex('31c0c3'),
        'mrNh78tBpmg#libSceRemoteplay': bytes.fromhex('31c0c3'),
        'BOwybKVa3Do#libSceRemoteplay': bytes.fromhex('31c0c3'),
        # sceGameLiveStreamingPermitLiveStreaming
        'K0QxEbD7q+c#libSceGameLiveStreaming': bytes.fromhex('31c0c3'),
        # sceAudioInGetSilentState, sceAudioInIsSharedDevice: if (rsi) *rsi = 0; return 0;
        'BohEAQ7DlUE#libSceAudioIn': bytes.fromhex('4885f67406c7060000000031c0c3'),
        '6QP1MzdFWhs#libSceAudioIn': bytes.fromhex('4885f67406c7060000000031c0c3'),
        # sceNpWebApiAddHttpRequestHeader
        'joRjtRXTFoc#libSceNpWebApi': bytes.fromhex('31c0c3'),
        # sceDiscMap unknown
        'fJgP+wqifno#libSceDiscMap': bytes.fromhex('31c0c3'),
        # EAWebKit unknown
        'qiOZEn26Kds#EAWebKit': bytes.fromhex('31c0c3'),
    }

    # SacredFire: the loader and runtime see every import as NID#library (the eboot's own
    # library/module indices stay inside boot.bin and this linker). Plain names stay as they are.
    def canonical(name):
        identity = main['identity'](name)
        return f'{identity[0]}#{identity[1][0]}' if identity else name
    names = [canonical(name) for name in names]

    # Generate embedded stubs for known functions that return 0 or clear out-pointers
    stub_base = (base + 65535) & ~65535
    stub_bytes = bytearray()
    stub_addrs = {}
    init_code = bytes.fromhex('31c0c3cccccccccc') # 8 bytes: xor eax, eax; ret; int3...
    stub_bytes.extend(init_code)
    for scoped, code in EMBEDDED_STUBS.items():
        addr = stub_base + len(stub_bytes)
        stub_addrs[scoped] = addr
        stub_bytes.extend(code)
        while len(stub_bytes) % 8 != 0:
            stub_bytes.append(0xcc)  # int3 padding
    if len(stub_bytes) > len(init_code):
        stub_size = (len(stub_bytes) + 65535) & ~65535
        stub_bytes.extend(bytes(stub_size - len(stub_bytes)))
        if stub_base + stub_size > len(image):
            image.extend(bytes(stub_base + stub_size - len(image)))
        image[stub_base:stub_base + len(stub_bytes)] = stub_bytes
        segments.append((stub_base, stub_size, 5))  # RX: PROT_READ | PROT_EXEC
        table.append(dict(file='stubs.prx', base=stub_base, size=stub_size, init=stub_base,
                          tls_address=0, tls_memsz=0, tls_filesz=0, tls_module=0,
                          tls_relocations=0, exports=len(EMBEDDED_STUBS), sha256='0'*64))
        base = stub_base + stub_size

    bindings, unresolved = [], []
    for identity, index in identities.items():
        orig_name = names[index]
        if orig_name in NID_ALIASES:
            names[index] = NID_ALIASES[orig_name]
        found = exports.get(identity)
        if not found and identity and identity[1][0] == 'libSceLibcInternal':
            candidates = by_nid.get((identity[0], 'libc'), [])
            found = candidates[0] if len(candidates) == 1 else None
        if found:
            bindings.append((index, found[0], found[1]))
        elif orig_name in stub_addrs:
            bindings.append((index, stub_addrs[orig_name], 1))
        else:
            unresolved.append(names[index])

    main_tls = next((p for p in main['ph'] if p['type'] == 7), None)
    main_tls_values = (main_tls['vaddr'], main_tls['filesz'], main_tls['memsz'], main_tls['align']) if main_tls else (0, 0, 0, 0)
    if main_tls and (main_tls['filesz'] > main_tls['memsz'] or main_tls['memsz'] > 1024 * 1024
                     or main_tls['vaddr'] + main_tls['filesz'] > size):
        raise ValueError('unsupported eboot TLS layout')
    procparam = next(p for p in main['ph'] if p['type'] == 0x61000001)
    with (out / 'boot-linked.bin').open('wb') as f:
        f.write(struct.pack('<8s6Q', b'BBPROBE5', len(image), entry, len(segments), len(relocs), len(names), flags))
        f.write(struct.pack('<Q', procparam['vaddr']))
        f.write(struct.pack('<4Q', *main_tls_values))
        f.write(struct.pack('<Q', len(table)))
        for t in table:
            f.write(struct.pack('<7Q', t['base'], t['size'], t['init'], t['tls_address'], t['tls_memsz'],
                                t['tls_filesz'], t['tls_module']))
        f.write(struct.pack('<Q', len(bindings)))
        for binding in bindings:
            f.write(struct.pack('<3Q', *binding))
        for segment in segments:
            f.write(struct.pack('<3Q', *segment))
        for name in names:
            if len(name.encode()) >= 128:
                raise ValueError('name too long')
            f.write(name.encode().ljust(128, b'\0'))
        for relocation in relocs:
            f.write(struct.pack('<QQqq', *relocation))
        f.write(image)
    report = dict(modules=[{k: (hex(v) if k in ('base', 'init', 'tls_address') else v) for k, v in t.items()} for t in table],
                  bindings=len(bindings), imports=len(names), fs_loads_patched=fs_patched,
                  main_tls=dict(zip(('vaddr', 'filesz', 'memsz', 'align'), main_tls_values)),
                  unresolved_imports=unresolved)
    (out / 'link.json').write_text(json.dumps(report, indent=2) + '\n')
    summary = ', '.join(f"{t['file']}@{t['base']:#x}" for t in table)
    print(f'Linked modules: {summary}; {len(bindings)} native bindings, {len(unresolved)} imports left to the host runtime, '
          f'fs->gs patched={fs_patched}')


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('game', type=Path)
    p.add_argument('--out', type=Path, default=Path(__file__).resolve().parent.parent / 'out')
    p.add_argument('--modules', nargs='*', default=list(DEFAULT_MODULES))
    a = p.parse_args()
    link(a.game, a.out, a.modules)
