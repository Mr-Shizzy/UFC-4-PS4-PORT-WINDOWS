from pathlib import Path

elf = Path('out/eboot.elf').read_bytes()

# The 14 unpatched functions with 14 NOPs:
funcs = [
    0x358140, 0x38b440, 0x38b570, 0x38b7b0, 0x38b8c0, 0xb144f0, 
    0xf93a40, 0xf993d0, 0xf994d0, 0xf99cf0,
    0x1582f60, 0x1607390, 0x189f050, 0x18b0590
]

xml_entries = []
for f in funcs:
    base = f
    stub_start = base - 14
    vaddr = stub_start + 0x400000
    sig_bytes = elf[0x4000 + stub_start - 12 : 0x4000 + stub_start + 6]
    sig_str = ' '.join(f'{b:02x}' for b in sig_bytes)
    entry = f'''    <Metadata Title="EA SPORTS\u2122 UFC\u00ae 4"
              Name="Container Iterator {hex(base)} Null-Safety Bypass"
              Note="Prevents crash in container iteration {hex(base)} when container pointer is NULL"
              Author="Antigravity UFC4 Port"
              PatchVer="1.0"
              AppVer="28.00"
              AppElf="eboot.bin"
              isEnabled="true">
        <PatchList>
            <Line Type="bytes" Address="{vaddr:#010x}"
                  Value="4885ff7408554889e5eb079090c3ebf09090"
                  Signature="{sig_str}"
                  SignatureOffset="0x0c"/>
        </PatchList>
    </Metadata>'''
    xml_entries.append(entry)

# Append to patches/UFC4.xml before </Patch>
xml_path = Path('patches/UFC4.xml')
content = xml_path.read_text(encoding='utf-8')
pos = content.rfind('</Patch>')
new_content = content[:pos] + '\n'.join(xml_entries) + '\n</Patch>\n'
xml_path.write_text(new_content, encoding='utf-8')
print(f'Successfully added {len(xml_entries)} patches to patches/UFC4.xml')

# Also mirror directly into out/boot-linked.bin
image_offset = 0x68d1c0
with open('out/boot-linked.bin', 'r+b') as bf:
    stub = bytes.fromhex('4885ff7408554889e5eb079090c3ebf09090')
    for f in funcs:
        offset = image_offset + (f - 14)
        bf.seek(offset)
        bf.write(stub)
print('Successfully mirrored all 14 patches into out/boot-linked.bin')
