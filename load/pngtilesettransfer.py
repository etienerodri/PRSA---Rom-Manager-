from pathlib import Path
from typing import Tuple, Optional, List
import struct
from PIL import Image
from load.lz10util import compress_lz10, decompress_lz10
from load.narcutil import parse_narc, build_narc
from load.datparser import parse_dat_map
from load.texparser import parse_tex_map

def quantize_image_simple(img: Image.Image) -> Tuple[Optional[Image.Image], Optional[List[Tuple[int, int, int]]]]:
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    quantized_img = img.quantize(colors=256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
    palette_flat = quantized_img.getpalette()
    if not palette_flat:
        return (None, None)
    palette = []
    for i in range(0, min(len(palette_flat), 256 * 3), 3):
        palette.append((palette_flat[i], palette_flat[i + 1], palette_flat[i + 2]))
    quantized_img = quantized_img.convert('RGBA')
    alpha = img.getchannel('A')
    quantized_img.putalpha(alpha)
    final_quantized = quantized_img.quantize(colors=256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
    final_palette_flat = final_quantized.getpalette()
    final_palette = []
    if final_palette_flat:
        for i in range(0, min(len(final_palette_flat), 256 * 3), 3):
            final_palette.append((final_palette_flat[i], final_palette_flat[i + 1], final_palette_flat[i + 2]))
    return (final_quantized.convert('P'), final_palette)

def quantize_image_with_banks(img: Image.Image, max_colors: int=15) -> Tuple[Optional[Image.Image], Optional[List[Tuple[int, int, int]]]]:
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    alpha = img.getchannel('A')
    img_with_bg = Image.new('RGBA', img.size, (0, 0, 0, 255))
    img_with_bg.paste(img, mask=alpha)
    quantized_img = img_with_bg.quantize(colors=max_colors, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
    palette_flat = quantized_img.getpalette()
    if not palette_flat:
        return (None, None)
    palette = []
    palette.append((0, 0, 0))
    for i in range(0, min(len(palette_flat), max_colors * 3), 3):
        palette.append((palette_flat[i], palette_flat[i + 1], palette_flat[i + 2]))
    pixel_data = list(quantized_img.getdata())
    new_pixel_data = []
    for idx, alpha_val in enumerate(alpha.getdata()):
        if alpha_val < 128:
            new_pixel_data.append(0)
        else:
            new_pixel_data.append(pixel_data[idx] + 1 if pixel_data[idx] < 15 else 15)
    final_img = Image.new('P', quantized_img.size)
    final_img.putdata(new_pixel_data)
    while len(palette) < 16:
        palette.append((0, 0, 0))
    palette = palette[:16]
    return (final_img, palette)

def build_rlcn_256color(palette: List[Tuple[int, int, int]]) -> bytes:
    while len(palette) < 256:
        palette.append((0, 0, 0))
    palette = palette[:256]
    ttlp_data = bytearray()
    for r, g, b in palette:
        r5 = r >> 3 & 31
        g5 = g >> 3 & 31
        b5 = b >> 3 & 31
        bgr555 = b5 << 10 | g5 << 5 | r5
        ttlp_data.extend(struct.pack('<H', bgr555))
    ttlp_section_size = 536
    ttlp_header = b'TTLP'
    ttlp_header += struct.pack('<I', ttlp_section_size)
    ttlp_header += struct.pack('<I', 3)
    ttlp_header += struct.pack('<I', 0)
    ttlp_header += struct.pack('<I', 512)
    ttlp_header += struct.pack('<I', 16)
    ttlp_section = ttlp_header + ttlp_data
    file_size = 552
    rlcn_header = b'RLCN'
    rlcn_header += b'\xff\xfe\x01\x00'
    rlcn_header += struct.pack('<I', file_size)
    rlcn_header += struct.pack('<H', 16)
    rlcn_header += struct.pack('<H', 1)
    return rlcn_header + ttlp_section

def build_rlcn_with_banks(palette: List[Tuple[int, int, int]], num_banks: int=16) -> bytes:
    full_palette = []
    for bank in range(num_banks):
        if bank == 0:
            for i, (r, g, b) in enumerate(palette[:16]):
                if i == 0:
                    full_palette.append((0, 0, 0))
                else:
                    full_palette.append((r, g, b))
            while len(full_palette) < (bank + 1) * 16:
                full_palette.append((0, 0, 0))
        else:
            for i in range(16):
                if i == 0:
                    full_palette.append((0, 0, 0))
                elif len(palette) > i:
                    full_palette.append(palette[i])
                else:
                    gray = i * 17 % 256
                    full_palette.append((gray, gray, gray))
    ttlp_data = bytearray()
    for r, g, b in full_palette:
        r5 = r >> 3 & 31
        g5 = g >> 3 & 31
        b5 = b >> 3 & 31
        bgr555 = b5 << 10 | g5 << 5 | r5
        ttlp_data.extend(struct.pack('<H', bgr555))
    ttlp_section_size = 536
    ttlp_header = b'TTLP'
    ttlp_header += struct.pack('<I', ttlp_section_size)
    ttlp_header += struct.pack('<I', 3)
    ttlp_header += struct.pack('<I', 0)
    ttlp_header += struct.pack('<I', 512)
    ttlp_header += struct.pack('<I', 16)
    ttlp_section = ttlp_header + ttlp_data
    file_size = 552
    rlcn_header = b'RLCN'
    rlcn_header += b'\xff\xfe\x01\x00'
    rlcn_header += struct.pack('<I', file_size)
    rlcn_header += struct.pack('<H', 16)
    rlcn_header += struct.pack('<H', 1)
    return rlcn_header + ttlp_section

def build_rgcn(img: Image.Image) -> bytes:
    width, height = img.size
    if width % 8 != 0 or height % 8 != 0:
        new_width = (width + 7) // 8 * 8
        new_height = (height + 7) // 8 * 8
        padded_img = Image.new('P', (new_width, new_height), 0)
        padded_img.paste(img, (0, 0))
        img = padded_img
        width, height = (new_width, new_height)
        print(f'  Image padded to {width}x{height} for 8-pixel alignment')
    linear_indices = bytearray()
    pixels = list(img.getdata())
    for y in range(height):
        for x in range(width):
            pixel_index = y * width + x
            if pixel_index < len(pixels):
                linear_indices.append(pixels[pixel_index] & 15)
            else:
                linear_indices.append(0)
    packed_data = bytearray()
    for i in range(0, len(linear_indices), 2):
        low_nibble = linear_indices[i] & 15
        high_nibble = (linear_indices[i + 1] & 15) << 4 if i + 1 < len(linear_indices) else 0
        packed_data.append(low_nibble | high_nibble)
    tile_data_size = len(packed_data)
    char_section_size = 32 + tile_data_size
    char_header = b'RAHC'
    char_header += struct.pack('<I', char_section_size)
    char_header += struct.pack('<H', height // 8)
    char_header += struct.pack('<H', width // 8)
    char_header += struct.pack('<I', 3)
    char_header += struct.pack('<I', 0)
    char_header += struct.pack('<I', 1)
    char_header += struct.pack('<I', tile_data_size)
    char_header += struct.pack('<I', 24)
    char_section = char_header + packed_data
    sopc_section = b'SOPC'
    sopc_section += struct.pack('<I', 16)
    sopc_section += struct.pack('<I', 0)
    sopc_section += struct.pack('<H', width // 8)
    sopc_section += struct.pack('<H', height // 8)
    file_size = 16 + len(char_section) + len(sopc_section)
    rgcn_header = b'RGCN'
    rgcn_header += b'\xff\xfe\x01\x01'
    rgcn_header += struct.pack('<I', file_size)
    rgcn_header += struct.pack('<H', 16)
    rgcn_header += struct.pack('<H', 2)
    return rgcn_header + char_section + sopc_section

def convert_png_to_tileset(png_path: str, use_tile_banks: bool=True, output_rgcn_path: str=None, output_rlcn_path: str=None) -> Tuple[bool, str, Optional[bytes], Optional[bytes]]:
    try:
        print(f'\n=== Converting PNG to Tileset ===')
        print(f'  Input: {png_path}')
        print(f"  Mode: {('Tile Banking (15 colors)' if use_tile_banks else 'Standard (256 colors)')}")
        img = Image.open(png_path)
        print(f'  Image size: {img.size[0]}x{img.size[1]}')
        print(f'  Image mode: {img.mode}')
        if use_tile_banks:
            quantized_img, palette = quantize_image_with_banks(img, max_colors=15)
        else:
            quantized_img, palette = quantize_image_simple(img)
        if quantized_img is None or palette is None:
            return (False, 'Image quantization failed', None, None)
        print(f'  Quantized to {len(palette)} palette colors')
        print('  Building RGCN...')
        rgcn_data = build_rgcn(quantized_img)
        print(f'    RGCN size: {len(rgcn_data):,} bytes')
        print('  Building RLCN...')
        if use_tile_banks:
            rlcn_data = build_rlcn_with_banks(palette, num_banks=16)
        else:
            rlcn_data = build_rlcn_256color(palette)
        print(f'    RLCN size: {len(rlcn_data):,} bytes')
        if output_rgcn_path:
            with open(output_rgcn_path, 'wb') as f:
                f.write(rgcn_data)
            print(f'  Saved RGCN: {output_rgcn_path}')
        if output_rlcn_path:
            with open(output_rlcn_path, 'wb') as f:
                f.write(rlcn_data)
            print(f'  Saved RLCN: {output_rlcn_path}')
        print('=== Conversion Complete ===\n')
        return (True, 'PNG converted successfully', rgcn_data, rlcn_data)
    except Exception as e:
        error_msg = f'PNG conversion failed: {str(e)}'
        print(f'ERROR: {error_msg}')
        import traceback
        traceback.print_exc()
        return (False, error_msg, None, None)

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

def add_tileset_to_tex(tex_result: dict, rgcn_data: bytes, rlcn_data: bytes) -> dict:
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

def build_tex_file(tex_result: dict) -> bytes:
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

def modify_dat_txif(dat_result: dict, new_texture_id: int) -> dict:
    existing_txif = dat_result.get('txif')
    if not existing_txif:
        raise ValueError('DAT file has no TXIF section')
    print(f'\n=== DAT TXIF Modification ===')
    new_txif = add_txif_rule(existing_txif, new_texture_id)
    dat_result['txif'] = new_txif
    return dat_result

def build_dat_file(dat_result: dict) -> bytes:
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

def transfer_png_to_map(png_path: str, dat_path: str, tex_path: str, use_tile_banks: bool=None, output_dat_path: str=None, output_tex_path: str=None) -> Tuple[bool, str]:
    try:
        print('\n' + '=' * 60)
        print('=== PNG TILESET TRANSFER OPERATION ===')
        print('=' * 60)
        if output_dat_path is None:
            output_dat_path = dat_path
        if output_tex_path is None:
            output_tex_path = tex_path
        if use_tile_banks is None:
            print('\n=== Auto-Detecting Best Conversion Mode ===')
            png_info = get_png_info(png_path)
            if 'error' in png_info:
                return (False, f"Failed to analyze PNG: {png_info['error']}")
            unique_colors = png_info.get('unique_colors', 256)
            print(f'  PNG has {unique_colors} unique colors')
            if unique_colors <= 16:
                use_tile_banks = True
                mode_reason = 'PNG has <=16 colors, optimal for tile banking'
            else:
                use_tile_banks = False
                mode_reason = 'PNG has >16 colors, using standard 256-color mode'
            print(f"  Auto-selected: {('Tile Banking Mode' if use_tile_banks else 'Standard 256-Color Mode')}")
            print(f'  Reason: {mode_reason}')
        else:
            mode_reason = 'User-specified mode'
        mode_name = 'Tile Banking (15 colors + transparency)' if use_tile_banks else 'Standard (256 colors)'
        print(f'  Conversion mode: {mode_name}')
        print('\n=== Step 1: Converting PNG ===')
        success, message, rgcn_data, rlcn_data = convert_png_to_tileset(png_path, use_tile_banks=use_tile_banks)
        if not success:
            return (False, message)
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
        tileset_count = tex_result.get('tileset_count', 0)
        new_texture_id = tileset_count
        print(f'  New tileset will be at index: {new_texture_id}')
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
        print('=== TRANSFER COMPLETE ===')
        print('=' * 60)
        print(f'PNG tileset successfully integrated!')
        print(f'  New tileset index: {new_texture_id}')
        print(f"  Total tilesets: {tex_result['tileset_count']}")
        print(f'  Mode: {mode_name}')
        print(f'  Selection: {mode_reason}')
        print(f'  Files saved:')
        print(f'    - {output_dat_path}')
        print(f'    - {output_tex_path}')
        print('=' * 60)
        return (True, f'PNG tileset integrated as texture ID {new_texture_id} using {mode_name}')
    except Exception as e:
        error_msg = f'Transfer failed: {str(e)}'
        print(f'\nERROR: {error_msg}')
        import traceback
        traceback.print_exc()
        return (False, error_msg)

def get_png_info(png_path: str) -> dict:
    try:
        img = Image.open(png_path)
        img_rgba = img.convert('RGBA')
        unique_colors = len(set(img_rgba.getdata()))
        has_alpha = img.mode == 'RGBA' and img.getchannel('A').getextrema() != (255, 255)
        return {'path': png_path, 'name': Path(png_path).name, 'width': img.size[0], 'height': img.size[1], 'mode': img.mode, 'unique_colors': unique_colors, 'has_transparency': has_alpha, 'file_size': Path(png_path).stat().st_size}
    except Exception as e:
        return {'path': png_path, 'error': str(e)}

def print_png_info(png_path: str):
    info = get_png_info(png_path)
    if 'error' in info:
        print(f"\nError reading PNG: {info['error']}")
        return
    print(f"\nPNG File: {info['name']}")
    print(f"  Path: {info['path']}")
    print(f"  Size: {info['width']}x{info['height']} pixels")
    print(f"  Mode: {info['mode']}")
    print(f"  Unique colors: {info['unique_colors']}")
    print(f"  Has transparency: {('Yes' if info['has_transparency'] else 'No')}")
    print(f"  File size: {info['file_size']:,} bytes")
    if info['unique_colors'] <= 16:
        print('  Recommendation: Use tile banking mode (15 colors)')
    elif info['unique_colors'] <= 256:
        print('  Recommendation: Use standard mode (256 colors)')
    else:
        print('  WARNING: Image has >256 colors, quantization will reduce quality')
if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print('PNG Tileset Transfer - Standalone Mode')
        print('\nUsage:')
        print('  Convert PNG only:')
        print('    python pngtilesettransfer.py <png_file> [--simple]')
        print('\n  Transfer to map:')
        print('    python pngtilesettransfer.py <png_file> <dat_file> <tex_file> [--simple]')
        print('\nOptions:')
        print('  --simple    Use simple 256-color mode instead of tile banking')
        sys.exit(1)
    png_path = sys.argv[1]
    use_tile_banks = '--simple' not in sys.argv
    if len(sys.argv) >= 4:
        dat_path = sys.argv[2]
        tex_path = sys.argv[3]
        success, message = transfer_png_to_map(png_path, dat_path, tex_path, use_tile_banks=use_tile_banks)
        if success:
            print(f'\nSUCCESS: {message}')
            sys.exit(0)
        else:
            print(f'\nFAILED: {message}')
            sys.exit(1)
    else:
        print_png_info(png_path)
        base_name = Path(png_path).stem
        rgcn_path = f'{base_name}.rgcn'
        rlcn_path = f'{base_name}.rlcn'
        success, message, rgcn_data, rlcn_data = convert_png_to_tileset(png_path, use_tile_banks=use_tile_banks, output_rgcn_path=rgcn_path, output_rlcn_path=rlcn_path)
        if success:
            print(f'\nSUCCESS: {message}')
            print(f'Files saved:')
            print(f'  - {rgcn_path}')
            print(f'  - {rlcn_path}')
            sys.exit(0)
        else:
            print(f'\nFAILED: {message}')
            sys.exit(1)
