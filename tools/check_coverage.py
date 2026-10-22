import re
from pathlib import Path
from collections import Counter

# Paths relative to repository root
REPO_DIR = Path(__file__).resolve().parent.parent
src_dir = REPO_DIR / "src"
c_files = list(src_dir.glob("runtime_*.c")) + [src_dir / "runtime.c", src_dir / "probe.c"]

handled_nids = set()
handled_symbols = set()

# Pattern for any string literal that looks like an 11-char NID (base64-like) or NID#lib
nid_literal_pattern = re.compile(r'"([A-Za-z0-9_+-]{11}(?:#[A-Za-z0-9_]+)?)"')
sym_pattern = re.compile(r'\{\s*"([A-Za-z0-9_]+)"\s*,')
libfunc_pattern = re.compile(r'LIB_FUNCTION\(\s*"([^"]+)"')

for c in c_files:
    if not c.exists():
        continue
    text = c.read_text(encoding="latin1")
    for m in nid_literal_pattern.finditer(text):
        target = m.group(1)
        nid = target.partition("#")[0]
        handled_nids.add(nid)
        handled_nids.add(target)
    for m in sym_pattern.finditer(text):
        handled_symbols.add(m.group(1))

# Check bbgpu and shadps4
gpu_dir = REPO_DIR / "gpu"
if gpu_dir.exists():
    for ext in ("*.cpp", "*.h", "*.inl"):
        for f in gpu_dir.rglob(ext):
            try:
                text = f.read_text(encoding="latin1")
            except Exception:
                continue
            for m in nid_literal_pattern.finditer(text):
                target = m.group(1)
                nid = target.partition("#")[0]
                handled_nids.add(nid)
                handled_nids.add(target)
            for m in sym_pattern.finditer(text):
                handled_symbols.add(m.group(1))
            for m in libfunc_pattern.finditer(text):
                handled_nids.add(m.group(1))

import_names_file = REPO_DIR / "out" / "import_names.txt"
if not import_names_file.exists():
    print(f"Error: {import_names_file} not found. Run tools/gen_import_names.py first.")
    exit(1)

lines = import_names_file.read_text().splitlines()
resolved = []
unresolved = []

for l in lines:
    if l.startswith("#") or not l.strip():
        continue
    parts = l.split()
    if len(parts) >= 2:
        nid = parts[0]
        lib = parts[1]
        sym = parts[2] if len(parts) >= 3 else "?"
        scoped = f"{nid}#{lib}"
        if nid in handled_nids or scoped in handled_nids or (sym != "?" and sym in handled_symbols):
            resolved.append((nid, lib, sym))
        else:
            unresolved.append((nid, lib, sym))

print(f"Total imports in UFC 4: {len(resolved) + len(unresolved)}")
print(f"Resolved by SacredFire runtime / GPU: {len(resolved)}")
print(f"Unresolved imports needing stubs/impl: {len(unresolved)}")

c = Counter(lib for _, lib, _ in unresolved)
print("\nUnresolved imports by library:")
for lib, cnt in c.most_common():
    print(f"  {lib}: {cnt}")

print("\nAll unresolved imports:")
for nid, lib, sym in unresolved:
    print(f"  [{lib}] {sym} ({nid})")
