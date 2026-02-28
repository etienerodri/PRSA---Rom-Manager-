import struct
from typing import List

def u16(b: bytes, o: int) -> int:
    return b[o] | b[o + 1] << 8

def u32(b: bytes, o: int) -> int:
    return b[o] | b[o + 1] << 8 | b[o + 2] << 16 | b[o + 3] << 24

def parse_narc(blob: bytes) -> List[bytes]:
    if blob[:4] != b'NARC':
        raise ValueError('Not a NARC file')
    off = 16
    if blob[off:off + 4] != b'BTAF':
        raise ValueError('NARC missing BTAF')
    btaf_size = u32(blob, off + 4)
    count = u32(blob, off + 8)
    entries_off = off + 12
    entries = []
    for i in range(count):
        s = u32(blob, entries_off + i * 8)
        e = u32(blob, entries_off + i * 8 + 4)
        entries.append((s, e))
    fntb_off = off + btaf_size
    if blob[fntb_off:fntb_off + 4] != b'BTNF':
        raise ValueError('NARC missing BTNF')
    fntb_size = u32(blob, fntb_off + 4)
    fimg_off = fntb_off + fntb_size
    if blob[fimg_off:fimg_off + 4] != b'GMIF':
        raise ValueError('NARC missing GMIF')
    base = fimg_off + 8
    files = []
    for s, e in entries:
        files.append(blob[base + s:base + e])
    return files

def build_narc(files: List[bytes]) -> bytes:

    def align4(n: int) -> int:
        return n + 3 & ~3

    def pad4(data: bytes) -> bytes:
        padding = -len(data) & 3
        return data + b'\x00' * padding
    gmif_data = bytearray()
    file_offsets = []
    for file_data in files:
        file_offsets.append(len(gmif_data))
        gmif_data.extend(file_data)
        padding = -len(gmif_data) & 3
        if padding:
            gmif_data.extend(b'\x00' * padding)
    file_offsets.append(len(gmif_data))
    gmif_size = 8 + len(gmif_data)
    gmif_section = b'GMIF' + struct.pack('<I', gmif_size) + bytes(gmif_data)
    file_count = len(files)
    btaf_entries = bytearray()
    for i in range(file_count):
        start_offset = file_offsets[i]
        end_offset = file_offsets[i + 1]
        btaf_entries.extend(struct.pack('<II', start_offset, end_offset))
    btaf_size = 12 + len(btaf_entries)
    btaf_size = align4(btaf_size)
    btaf_padding = btaf_size - (12 + len(btaf_entries))
    btaf_section = b'BTAF' + struct.pack('<II', btaf_size, file_count) + bytes(btaf_entries) + b'\x00' * btaf_padding
    btnf_size = 16
    btnf_section = b'BTNF' + struct.pack('<I', btnf_size) + b'\x00' * 8
    total_size = 16 + len(btaf_section) + len(btnf_section) + len(gmif_section)
    header = b'NARC'
    header += b'\xfe\xff'
    header += b'\x00\x01'
    header += struct.pack('<I', total_size)
    header += struct.pack('<H', 16)
    header += struct.pack('<H', 3)
    narc = header + btaf_section + btnf_section + gmif_section
    return narc
