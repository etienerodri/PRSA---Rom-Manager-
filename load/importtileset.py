from pathlib import Path
from typing import Tuple, Optional, Dict, List
import struct
from load.lz10util import compress_lz10, decompress_lz10
from load.narcutil import parse_narc, build_narc
from load.datparser import parse_dat_map
from load.texparser import parse_tex_map

def detect_file_type(file_data: bytes) -> Tuple[str, str]:
    if not file_data or len(file_data) < 4:
        return ('UNKNOWN', 'Too small')
    magic = file_data[:4]
    graphics_magics = [(b'RGCN', 'RGCN'), (b'NCGR', 'NCGR'), (b'NCBR', 'NCBR'), (b'NCER', 'NCER')]
    palette_magics = [(b'RLCN', 'RLCN'), (b'NCLR', 'NCLR'), (b'RTFN', 'RTFN')]
    for magic_bytes, name in graphics_magics:
        if magic == magic_bytes:
            return ('RGCN', name)
    for magic_bytes, name in palette_magics:
        if magic == magic_bytes:
            return ('RLCN', name)
    magic_reversed = magic[::-1]
    for magic_bytes, name in graphics_magics:
        if magic_reversed == magic_bytes:
            return ('RGCN', f'{name}_REVERSED')
    for magic_bytes, name in palette_magics:
        if magic_reversed == magic_bytes:
            return ('RLCN', f'{name}_REVERSED')
    for magic_bytes, name in graphics_magics:
        if magic[:3] == magic_bytes[:3]:
            return ('RGCN', f'{name}_PARTIAL')
    for magic_bytes, name in palette_magics:
        if magic[:3] == magic_bytes[:3]:
            return ('RLCN', f'{name}_PARTIAL')
    for offset in range(0, min(len(file_data) - 4, 128), 4):
        section_magic = file_data[offset:offset + 4]
        if section_magic in [b'RAHC', b'CHAR']:
            return ('RGCN', 'RGCN_BY_SECTION')
        if section_magic in [b'TTLP', b'PLTT']:
            return ('RLCN', 'RLCN_BY_SECTION')
    return ('UNKNOWN', f'Magic: {magic.hex().upper()}')

def validate_tileset_files(rgcn_data: bytes, rlcn_data: bytes) -> Tuple[bool, str]:
    errors = []
    rgcn_type, rgcn_format = detect_file_type(rgcn_data)
    if rgcn_type != 'RGCN':
        errors.append(f'RGCN file invalid: detected as {rgcn_type} ({rgcn_format})')
    if len(rgcn_data) < 32:
        errors.append(f'RGCN file too small: {len(rgcn_data)} bytes')
    rlcn_type, rlcn_format = detect_file_type(rlcn_data)
    if rlcn_type != 'RLCN':
        errors.append(f'RLCN file invalid: detected as {rlcn_type} ({rlcn_format})')
    if len(rlcn_data) < 32:
        errors.append(f'RLCN file too small: {len(rlcn_data)} bytes')
    if errors:
        return (False, '; '.join(errors))
    return (True, 'Valid')

def create_txif_rule(texture_id: int, rule_type: int=1, unknown1: int=0, unknown2: int=0) -> bytes:
    rule = bytearray(8)
    struct.pack_into('<H', rule, 0, rule_type)
    struct.pack_into('<H', rule, 2, texture_id)
    struct.pack_into('<H', rule, 4, unknown1)
    struct.pack_into('<H', rule, 6, unknown2)
    return bytes(rule)

def add_txif_rule(existing_txif: bytes, new_texture_id: int, rule_type: int=1) -> bytes:
    if not existing_txif or len(existing_txif) < 8:
        raise ValueError('Invalid TXIF section')
    magic = existing_txif[:4]
    if magic != b'TXIF':
        raise ValueError(f'Invalid TXIF magic: {magic.hex()}')
    rule_count = struct.unpack('<H', existing_txif[4:6])[0]
    override_flag = struct.unpack('<H', existing_txif[6:8])[0]
    print(f'  Current TXIF: {rule_count} rules')
    print(f'  Adding rule for texture ID: {new_texture_id}')
    new_rule = create_txif_rule(new_texture_id, rule_type)
    new_txif = bytearray()
    new_txif.extend(b'TXIF')
    new_txif.extend(struct.pack('<H', rule_count + 1))
    new_txif.extend(struct.pack('<H', override_flag))
    new_txif.extend(existing_txif[8:])
    new_txif.extend(new_rule)
    print(f'  New TXIF: {rule_count + 1} rules')
    return bytes(new_txif)

def determine_next_texture_id(dat_result: Dict, tex_result: Dict) -> int:
    tileset_count = tex_result.get('tileset_count', 0)
    print(f'\n=== Texture ID Determination ===')
    print(f'  TEX currently has {tileset_count} tilesets')
    print(f'  New tileset will be at position: {tileset_count}')
    print(f'  Creating TXIF rule for texture ID: {tileset_count}')
    return tileset_count

def add_tileset_to_tex(tex_result: Dict, rgcn_data: bytes, rlcn_data: bytes) -> Dict:
    new_index = len(tex_result['tilesets'])
    new_tileset = {'index': new_index, 'RGCN': rgcn_data, 'RLCN': rlcn_data, 'NCGR': rgcn_data, 'NCLR': rlcn_data}
    tex_result['tilesets'].append(new_tileset)
    tex_result['tileset_count'] = len(tex_result['tilesets'])
    print(f'\n=== TEX Modification ===')
    print(f'  Added tileset at index: {new_index}')
    print(f'  RGCN size: {len(rgcn_data):,} bytes')
    print(f'  RLCN size: {len(rlcn_data):,} bytes')
    print(f"  Total tilesets: {tex_result['tileset_count']}")
    return tex_result

def build_tex_file(tex_result: Dict) -> bytes:
    print(f'\n=== Building TEX File ===')
    tilesets = tex_result.get('tilesets', [])
    print(f'  Building {len(tilesets)} tilesets')
    tileset_narcs = []
    for ts in tilesets:
        rgcn = ts.get('RGCN')
        rlcn = ts.get('RLCN')
        if not rgcn or not rlcn:
            print(f"  WARNING: Tileset {ts['index']} missing data, skipping")
            continue
        inner_narc = build_narc([rgcn, rlcn])
        tileset_narcs.append(inner_narc)
        print(f"  Tileset {ts['index']}: NARC size = {len(inner_narc):,} bytes")
    outer_narc = build_narc(tileset_narcs)
    print(f'  Outer NARC size: {len(outer_narc):,} bytes')
    tex_file = b'TEX\x00' + outer_narc
    print(f'  Final TEX size: {len(tex_file):,} bytes (uncompressed)')
    return tex_file

def modify_dat_txif(dat_result: Dict, new_texture_id: int) -> Dict:
    existing_txif = dat_result.get('txif')
    if not existing_txif:
        raise ValueError('DAT file has no TXIF section')
    print(f'\n=== DAT TXIF Modification ===')
    new_txif = add_txif_rule(existing_txif, new_texture_id)
    dat_result['txif'] = new_txif
    return dat_result

def build_dat_file(dat_result: Dict) -> bytes:
    print(f'\n=== Building DAT File ===')
    sections = []
    if dat_result.get('mpif'):
        sections.append(dat_result['mpif'])
        print(f"  MPIF: {len(dat_result['mpif']):,} bytes")
    if dat_result.get('txif'):
        sections.append(dat_result['txif'])
        print(f"  TXIF: {len(dat_result['txif']):,} bytes")
    layers = dat_result.get('layers', [])
    if layers:
        layer_data_list = [layer['data'] for layer in layers]
        inner_layer_narc = build_narc(layer_data_list)
        lyr_section = b'LYR\x00' + inner_layer_narc
        sections.append(lyr_section)
        print(f'  LYR: {len(lyr_section):,} bytes ({len(layers)} layers)')
    if dat_result.get('cta'):
        sections.append(dat_result['cta'])
        print(f"  CTA: {len(dat_result['cta']):,} bytes")
    main_narc = build_narc(sections)
    print(f'  Main NARC size: {len(main_narc):,} bytes (uncompressed)')
    return main_narc

def import_tileset(dat_path: str, tex_path: str, rgcn_path: str, rlcn_path: str, output_dat_path: str=None, output_tex_path: str=None) -> Tuple[bool, str]:
    try:
        print('\n' + '=' * 60)
        print('=== TILESET IMPORT OPERATION ===')
        print('=' * 60)
        if output_dat_path is None:
            output_dat_path = dat_path
        if output_tex_path is None:
            output_tex_path = tex_path
        print('\n=== Step 1: Loading Files ===')
        print(f'  RGCN: {rgcn_path}')
        print(f'  RLCN: {rlcn_path}')
        with open(rgcn_path, 'rb') as f:
            rgcn_data = f.read()
        with open(rlcn_path, 'rb') as f:
            rlcn_data = f.read()
        print(f'  RGCN size: {len(rgcn_data):,} bytes')
        print(f'  RLCN size: {len(rlcn_data):,} bytes')
        rgcn_type, rgcn_format = detect_file_type(rgcn_data)
        rlcn_type, rlcn_format = detect_file_type(rlcn_data)
        print(f'  RGCN detected as: {rgcn_type} ({rgcn_format})')
        print(f'  RLCN detected as: {rlcn_type} ({rlcn_format})')
        is_valid, error_msg = validate_tileset_files(rgcn_data, rlcn_data)
        if not is_valid:
            return (False, f'Validation failed: {error_msg}')
        print('  Validation: PASSED')
        print('\n=== Step 2: Parsing Map Files ===')
        print(f'  DAT: {dat_path}')
        print(f'  TEX: {tex_path}')
        dat_result = parse_dat_map(dat_path)
        tex_result = parse_tex_map(tex_path)
        if not dat_result or not tex_result:
            return (False, 'Failed to parse map files')
        print(f"  DAT parsed: {len(dat_result.get('layers', []))} layers")
        print(f"  TEX parsed: {tex_result.get('tileset_count', 0)} tilesets")
        print('\n=== Step 3: Determining Texture ID ===')
        new_texture_id = determine_next_texture_id(dat_result, tex_result)
        print('\n=== Step 4: Adding Tileset to TEX ===')
        tex_result = add_tileset_to_tex(tex_result, rgcn_data, rlcn_data)
        print('\n=== Step 5: Modifying DAT TXIF ===')
        dat_result = modify_dat_txif(dat_result, new_texture_id)
        print('\n=== Step 6: Building Files ===')
        new_tex = build_tex_file(tex_result)
        new_dat = build_dat_file(dat_result)
        print('\n=== Step 7: Compressing and Saving ===')
        print('  Compressing TEX...')
        tex_compressed = compress_lz10(new_tex)
        print(f'  TEX compressed: {len(tex_compressed):,} bytes')
        print('  Compressing DAT...')
        dat_compressed = compress_lz10(new_dat)
        print(f'  DAT compressed: {len(dat_compressed):,} bytes')
        print(f'\n  Saving TEX to: {output_tex_path}')
        with open(output_tex_path, 'wb') as f:
            f.write(tex_compressed)
        print(f'  Saving DAT to: {output_dat_path}')
        with open(output_dat_path, 'wb') as f:
            f.write(dat_compressed)
        print('\n' + '=' * 60)
        print('=== IMPORT COMPLETE ===')
        print('=' * 60)
        print(f'Successfully imported tileset!')
        print(f'  New tileset index: {new_texture_id}')
        print(f"  Total tilesets: {tex_result['tileset_count']}")
        print(f'  Files saved:')
        print(f'    - {output_dat_path}')
        print(f'    - {output_tex_path}')
        print('=' * 60)
        return (True, f'Tileset imported successfully as texture ID {new_texture_id}')
    except Exception as e:
        error_msg = f'Import failed: {str(e)}'
        print(f'\nERROR: {error_msg}')
        import traceback
        traceback.print_exc()
        return (False, error_msg)

def import_tileset_auto_detect(dat_path: str, tex_path: str, file1_path: str, file2_path: str, output_dat_path: str=None, output_tex_path: str=None) -> Tuple[bool, str]:
    print('\n=== Auto-Detecting File Types ===')
    with open(file1_path, 'rb') as f:
        file1_data = f.read()
    with open(file2_path, 'rb') as f:
        file2_data = f.read()
    file1_type, file1_format = detect_file_type(file1_data)
    file2_type, file2_format = detect_file_type(file2_data)
    print(f'  File 1: {file1_type} ({file1_format})')
    print(f'  File 2: {file2_type} ({file2_format})')
    if file1_type == 'RGCN' and file2_type == 'RLCN':
        rgcn_path = file1_path
        rlcn_path = file2_path
    elif file1_type == 'RLCN' and file2_type == 'RGCN':
        rgcn_path = file2_path
        rlcn_path = file1_path
    else:
        return (False, f'Could not identify files: {file1_type} and {file2_type}')
    print(f'  Identified: RGCN = {Path(rgcn_path).name}, RLCN = {Path(rlcn_path).name}')
    return import_tileset(dat_path, tex_path, rgcn_path, rlcn_path, output_dat_path, output_tex_path)

def get_file_info(file_path: str) -> Dict:
    with open(file_path, 'rb') as f:
        data = f.read()
    file_type, format_name = detect_file_type(data)
    return {'path': file_path, 'name': Path(file_path).name, 'size': len(data), 'type': file_type, 'format': format_name, 'magic': data[:4].hex().upper() if len(data) >= 4 else 'N/A'}

def print_file_info(file_path: str):
    info = get_file_info(file_path)
    print(f"\nFile: {info['name']}")
    print(f"  Path: {info['path']}")
    print(f"  Size: {info['size']:,} bytes")
    print(f"  Type: {info['type']}")
    print(f"  Format: {info['format']}")
    print(f"  Magic: {info['magic']}")
