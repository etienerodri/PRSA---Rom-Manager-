from typing import Dict, List, Tuple, Optional
from load.lz10util import decompress_lz10
from load.narcutil import parse_narc

def detect_graphics_magic(data: bytes) -> Tuple[bool, str]:
    if not data or len(data) < 4:
        return (False, '')
    magic = data[:4]
    graphics_magics = [(b'RGCN', 'RGCN'), (b'NCGR', 'NCGR'), (b'NCBR', 'NCBR'), (b'NCER', 'NCER'), (b'RNAN', 'RNAN')]
    for magic_bytes, name in graphics_magics:
        if magic == magic_bytes:
            return (True, name)
    magic_reversed = magic[::-1]
    for magic_bytes, name in graphics_magics:
        if magic_reversed == magic_bytes:
            return (True, f'{name}_REVERSED')
    for magic_bytes, name in graphics_magics:
        if magic[:3] == magic_bytes[:3] or magic[1:4] == magic_bytes[1:4]:
            return (True, f'{name}_PARTIAL')
    return (False, '')

def detect_palette_magic(data: bytes) -> Tuple[bool, str]:
    if not data or len(data) < 4:
        return (False, '')
    magic = data[:4]
    palette_magics = [(b'RLCN', 'RLCN'), (b'NCLR', 'NCLR'), (b'RTFN', 'RTFN')]
    for magic_bytes, name in palette_magics:
        if magic == magic_bytes:
            return (True, name)
    magic_reversed = magic[::-1]
    for magic_bytes, name in palette_magics:
        if magic_reversed == magic_bytes:
            return (True, f'{name}_REVERSED')
    for magic_bytes, name in palette_magics:
        if magic[:3] == magic_bytes[:3] or magic[1:4] == magic_bytes[1:4]:
            return (True, f'{name}_PARTIAL')
    return (False, '')

def try_parse_as_graphics(data: bytes) -> Optional[bytes]:
    if not data or len(data) < 32:
        return None
    is_gfx, fmt = detect_graphics_magic(data)
    if is_gfx:
        return data
    for offset in range(0, min(len(data) - 4, 64)):
        section_magic = data[offset:offset + 4]
        if section_magic in [b'RAHC', b'CHAR', b'CRAH', b'RAHC'[::-1]]:
            return data
    return None

def try_parse_as_palette(data: bytes) -> Optional[bytes]:
    if not data or len(data) < 32:
        return None
    is_pal, fmt = detect_palette_magic(data)
    if is_pal:
        return data
    for offset in range(0, min(len(data) - 4, 64)):
        section_magic = data[offset:offset + 4]
        if section_magic in [b'TTLP', b'PLTT', b'PLTL', b'TTLP'[::-1]]:
            return data
    return None

def classify_tileset_data(inner_files: List[bytes]) -> Tuple[Optional[bytes], Optional[bytes]]:
    rgcn = None
    rlcn = None
    for bf in inner_files:
        if not bf or len(bf) < 4:
            continue
        if not rgcn:
            graphics_data = try_parse_as_graphics(bf)
            if graphics_data:
                rgcn = graphics_data
                continue
        if not rlcn:
            palette_data = try_parse_as_palette(bf)
            if palette_data:
                rlcn = palette_data
                continue
        if rgcn and rlcn:
            break
    if not rgcn or not rlcn:
        for bf in inner_files:
            if not bf:
                continue
            if not rgcn and len(bf) >= 1024:
                rgcn = bf
            elif not rlcn and len(bf) < 1024:
                rlcn = bf
    return (rgcn, rlcn)

def parse_tex_map(tex_path: str) -> Dict:
    try:
        with open(tex_path, 'rb') as f:
            raw = f.read()
        dec = decompress_lz10(raw)
        if dec[:4] in [b'TEX\x00', b'TEX.', b'TEX\xff', b'TEX ', b'\x00XET']:
            dec = dec[4:]
        elif dec[:3] == b'TEX':
            dec = dec[4:]
        try:
            outer_files = parse_narc(dec)
        except ValueError as e:
            print(f'Warning: TEX not a valid NARC ({e}), treating as single tileset')
            outer_files = [dec]
        tilesets = []
        for i, ts_blob in enumerate(outer_files):
            if not ts_blob:
                tilesets.append({'index': i, 'RGCN': None, 'RLCN': None, 'NCGR': None, 'NCLR': None, 'error': 'Empty tileset data'})
                continue
            inner_files = []
            if ts_blob[:4] == b'NARC':
                try:
                    inner_files = parse_narc(ts_blob)
                except ValueError:
                    inner_files = [ts_blob]
            elif len(ts_blob) > 8:
                parts = []
                current_start = 0
                for offset in range(4, len(ts_blob) - 4):
                    magic = ts_blob[offset:offset + 4]
                    is_gfx, _ = detect_graphics_magic(magic)
                    is_pal, _ = detect_palette_magic(magic)
                    if is_gfx or is_pal:
                        if current_start < offset:
                            parts.append(ts_blob[current_start:offset])
                        current_start = offset
                if current_start < len(ts_blob):
                    parts.append(ts_blob[current_start:])
                if len(parts) > 1:
                    inner_files = parts
                else:
                    inner_files = [ts_blob]
            else:
                inner_files = [ts_blob]
            rgcn, rlcn = classify_tileset_data(inner_files)
            tileset_entry = {'index': i, 'RGCN': rgcn, 'RLCN': rlcn, 'NCGR': rgcn, 'NCLR': rlcn}
            if not rgcn and (not rlcn):
                tileset_entry['error'] = 'No valid graphics or palette data found'
            elif not rgcn:
                tileset_entry['warning'] = 'Graphics data (RGCN) missing'
            elif not rlcn:
                tileset_entry['warning'] = 'Palette data (RLCN) missing'
            tilesets.append(tileset_entry)
        return {'tilesets': tilesets, 'tileset_count': len(tilesets)}
    except Exception as e:
        print(f'ERROR parsing TEX file: {e}')
        import traceback
        traceback.print_exc()
        return {'tilesets': [], 'tileset_count': 0, 'error': str(e)}
