from PIL import Image, ImageTk, ImageDraw
from typing import List, Tuple, Optional, Dict
import customtkinter as ctk

def u16(b: bytes, o: int) -> int:
    return b[o] | b[o + 1] << 8 if o + 1 < len(b) else 0

def u32(b: bytes, o: int) -> int:
    return b[o] | b[o + 1] << 8 | b[o + 2] << 16 | b[o + 3] << 24 if o + 3 < len(b) else 0

def is_valid_palette_magic(magic: bytes) -> bool:
    if len(magic) < 4:
        return False
    valid_magics = [b'RLCN', b'NCLR', b'RTFN', b'NCLR'[::-1], b'RLCN'[::-1]]
    return magic in valid_magics or magic[:3] in [m[:3] for m in valid_magics]

def is_valid_graphics_magic(magic: bytes) -> bool:
    if len(magic) < 4:
        return False
    valid_magics = [b'RGCN', b'NCGR', b'NCBR', b'NCER', b'NCGR'[::-1], b'RGCN'[::-1]]
    return magic in valid_magics or magic[:3] in [m[:3] for m in valid_magics]

def parse_palette(rlcn_data: bytes) -> List[Tuple[int, int, int, int]]:
    if not rlcn_data or len(rlcn_data) < 24:
        return [(i, i, i, 255 if i > 0 else 0) for i in range(256)]
    magic = rlcn_data[0:4]
    if not is_valid_palette_magic(magic):
        print(f'Warning: Unusual palette magic {magic.hex()}, attempting to parse anyway')
    ttlp_off = None
    for offset in [20, 16, 24, 28, 32]:
        if offset + 4 <= len(rlcn_data):
            section_magic = rlcn_data[offset:offset + 4]
            if section_magic in [b'TTLP', b'PLTT', b'PLTL', b'TLTP']:
                ttlp_off = offset
                break
    if ttlp_off is None:
        for offset in range(0, min(len(rlcn_data) - 4, 128)):
            section_magic = rlcn_data[offset:offset + 4]
            if section_magic in [b'TTLP', b'PLTT', b'PLTL', b'TLTP']:
                ttlp_off = offset
                break
    if ttlp_off is None:
        print('Warning: No palette section found, using default grayscale')
        return [(i, i, i, 255 if i > 0 else 0) for i in range(256)]
    pal_data_off = ttlp_off + 24
    if pal_data_off >= len(rlcn_data):
        for try_offset in [16, 20, 24, 28, 32]:
            test_off = ttlp_off + try_offset
            if test_off < len(rlcn_data) - 32:
                pal_data_off = test_off
                break
    if pal_data_off >= len(rlcn_data):
        print('Warning: Palette data offset out of range, using default')
        return [(i, i, i, 255 if i > 0 else 0) for i in range(256)]
    palette = []
    pal_offset = pal_data_off
    for i in range(256):
        if pal_offset + 2 > len(rlcn_data):
            break
        bgr555 = u16(rlcn_data, pal_offset)
        pal_offset += 2
        r = (bgr555 & 31) << 3
        g = (bgr555 >> 5 & 31) << 3
        b = (bgr555 >> 10 & 31) << 3
        r = r | r >> 5
        g = g | g >> 5
        b = b | b >> 5
        a = 0 if i == 0 else 255
        palette.append((r, g, b, a))
    while len(palette) < 256:
        palette.append((255, 0, 255, 255))
    return palette

def parse_graphics(rgcn_data: bytes) -> Tuple[bytes, int, int, int]:
    if not rgcn_data or len(rgcn_data) < 48:
        print('Warning: Graphics data too small')
        return (b'', 256, 256, 4)
    magic = rgcn_data[0:4]
    if not is_valid_graphics_magic(magic):
        print(f'Warning: Unusual graphics magic {magic.hex()}, attempting to parse anyway')
    rahc_off = None
    for offset in [20, 16, 24, 28, 32]:
        if offset + 4 <= len(rgcn_data):
            section_magic = rgcn_data[offset:offset + 4]
            if section_magic in [b'RAHC', b'CHAR', b'CRAH', b'RHAC']:
                rahc_off = offset
                break
    if rahc_off is None:
        for offset in range(16, min(len(rgcn_data) - 4, 128), 4):
            section_magic = rgcn_data[offset:offset + 4]
            if section_magic in [b'RAHC', b'CHAR', b'CRAH', b'RHAC']:
                rahc_off = offset
                break
    if rahc_off is None:
        print('Warning: No graphics section found')
        return (b'', 256, 256, 4)
    if rahc_off + 32 > len(rgcn_data):
        print('Warning: Graphics section header incomplete')
        width, height, bpp = (256, 256, 4)
        data_off = rahc_off + 16
        if data_off < len(rgcn_data):
            gfx_data = rgcn_data[data_off:]
            return (gfx_data, width, height, bpp)
        return (b'', width, height, bpp)
    height_value = u16(rgcn_data, rahc_off + 8)
    width_value = u16(rgcn_data, rahc_off + 10)
    bit_depth_flag = u32(rgcn_data, rahc_off + 12)
    tile_data_size = u32(rgcn_data, rahc_off + 24)
    bpp = 4 if bit_depth_flag == 3 else 8
    bytes_per_pixel = 0.5 if bpp == 4 else 1.0
    expected_size = int(width_value * height_value * bytes_per_pixel)
    if abs(expected_size - tile_data_size) < 16:
        width = width_value
        height = height_value
    elif abs(expected_size * 64 - tile_data_size) < 16:
        width = width_value * 8
        height = height_value * 8
    else:
        if tile_data_size > 0 and bytes_per_pixel > 0:
            total_pixels = int(tile_data_size / bytes_per_pixel)
        else:
            total_pixels = 65536
        common_sizes = [(256, 256), (256, 128), (128, 256), (128, 128), (256, 64), (64, 256), (512, 256), (256, 512), (512, 512), (64, 64), (32, 32), (16, 16)]
        width, height = (256, 256)
        for w, h in common_sizes:
            if w * h == total_pixels:
                width, height = (w, h)
                break
        else:
            width = int(total_pixels ** 0.5)
            height = total_pixels // width if width > 0 else 8
            width = max(8, (width + 7) // 8 * 8)
            height = max(8, (height + 7) // 8 * 8)
    width = max(8, min(512, width))
    height = max(8, min(512, height))
    data_off = rahc_off + 32
    if data_off >= len(rgcn_data):
        for try_offset in [16, 20, 24, 28, 32, 36, 40]:
            test_off = rahc_off + try_offset
            if test_off < len(rgcn_data):
                data_off = test_off
                break
    if data_off >= len(rgcn_data):
        print('Warning: Graphics data offset out of range')
        return (b'', width, height, bpp)
    if tile_data_size > 0 and data_off + tile_data_size <= len(rgcn_data):
        gfx_data = rgcn_data[data_off:data_off + tile_data_size]
    else:
        gfx_data = rgcn_data[data_off:]
    return (gfx_data, width, height, bpp)

def create_error_tileset(width: int, height: int, error_msg: str) -> Image.Image:
    img = Image.new('RGBA', (width, height), (60, 60, 80, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, width - 1, height - 1], outline=(255, 0, 0, 255), width=2)
    for i in range(0, max(width, height), 16):
        draw.line([(i, 0), (i - height, height)], fill=(255, 0, 0, 128), width=1)
    if width >= 100 and height >= 50:
        try:
            text_lines = ['ERROR', error_msg[:20]]
            y_offset = height // 2 - 20
            for line in text_lines:
                bbox = draw.textbbox((0, 0), line)
                text_width = bbox[2] - bbox[0]
                x = (width - text_width) // 2
                draw.text((x, y_offset), line, fill=(255, 255, 0, 255))
                y_offset += 20
        except:
            pass
    return img

def render_tileset(rgcn_data: bytes, rlcn_data: bytes) -> Image.Image:
    width, height = (256, 256)
    if not rlcn_data or len(rlcn_data) < 32:
        print('Warning: No valid palette data, using default grayscale')
        palette = [(i, i, i, 255 if i > 0 else 0) for i in range(256)]
    else:
        palette = parse_palette(rlcn_data)
    while len(palette) < 256:
        palette.append((255, 0, 255, 255))
    if not rgcn_data or len(rgcn_data) < 32:
        print('Warning: No valid graphics data')
        return create_error_tileset(width, height, 'No RGCN data')
    gfx_data, width, height, bpp = parse_graphics(rgcn_data)
    if not gfx_data or len(gfx_data) == 0:
        print('Warning: No graphics data found in RGCN')
        return create_error_tileset(width, height, 'Empty graphics')
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    pixels = img.load()
    try:
        indices = []
        if bpp == 4:
            for byte in gfx_data:
                indices.append(byte & 15)
                indices.append(byte >> 4 & 15)
        else:
            indices.extend(gfx_data)
        pixels_rendered = 0
        for i, idx in enumerate(indices):
            if i >= width * height:
                break
            y, x = divmod(i, width)
            if x < width and y < height:
                color = palette[idx % len(palette)]
                pixels[x, y] = color
                pixels_rendered += 1
        if pixels_rendered == 0:
            print('Warning: No pixels rendered')
            return create_error_tileset(width, height, 'Render failed')
    except Exception as e:
        print(f'Error rendering tileset: {e}')
        return create_error_tileset(width, height, str(e)[:20])
    return img

class TilesetRenderer:

    def __init__(self):
        self.tilesets = []
        self.selected_tileset_index = None
        self.rendered_image = None
        self.tk_image = None
        self.on_tileset_selected = None
        self.on_tileset_rendered = None

    def load_tilesets(self, tilesets: List[Dict]):
        self.tilesets = tilesets
        self.selected_tileset_index = None
        self.rendered_image = None
        self.tk_image = None
        print(f'\n=== TilesetRenderer: Loaded {len(tilesets)} tilesets ===')
        for i, ts in enumerate(tilesets):
            has_rgcn = 'Yes' if ts.get('RGCN') or ts.get('NCGR') else 'No'
            has_rlcn = 'Yes' if ts.get('RLCN') or ts.get('NCLR') else 'No'
            print(f'  Tileset {i}: RGCN={has_rgcn}, RLCN={has_rlcn}')

    def get_tilesets(self) -> List[Dict]:
        return self.tilesets

    def get_tileset_count(self) -> int:
        return len(self.tilesets)

    def select_tileset(self, index: int) -> bool:
        if index < 0 or index >= len(self.tilesets):
            print(f'Warning: Invalid tileset index {index}')
            return False
        self.selected_tileset_index = index
        tileset = self.tilesets[index]
        print(f'\n=== Tileset {index} selected ===')
        rgcn_data = tileset.get('RGCN') or tileset.get('NCGR')
        rlcn_data = tileset.get('RLCN') or tileset.get('NCLR')
        if not rgcn_data and (not rlcn_data):
            print('Error: No graphics or palette data available')
            if 'error' in tileset:
                print(f"  Error: {tileset['error']}")
            return False
        if self.on_tileset_selected:
            self.on_tileset_selected(index, tileset)
        self.render_current_tileset()
        return True

    def render_current_tileset(self) -> Optional[Image.Image]:
        if self.selected_tileset_index is None:
            print('Warning: No tileset selected')
            return None
        tileset = self.tilesets[self.selected_tileset_index]
        rgcn_data = tileset.get('RGCN') or tileset.get('NCGR') or b''
        rlcn_data = tileset.get('RLCN') or tileset.get('NCLR') or b''
        print(f'Rendering tileset {self.selected_tileset_index}...')
        print(f'  RGCN size: {len(rgcn_data)} bytes')
        print(f'  RLCN size: {len(rlcn_data)} bytes')
        self.rendered_image = render_tileset(rgcn_data, rlcn_data)
        print(f'  Rendered: {self.rendered_image.size[0]}x{self.rendered_image.size[1]}')
        if self.on_tileset_rendered:
            self.on_tileset_rendered(self.rendered_image)
        return self.rendered_image

    def get_rendered_image(self) -> Optional[Image.Image]:
        return self.rendered_image

    def get_tk_image(self, max_width: int=800, max_height: int=600) -> Optional[ImageTk.PhotoImage]:
        if self.rendered_image is None:
            return None
        img_width, img_height = self.rendered_image.size
        scale_x = max_width / img_width if img_width > max_width else 1.0
        scale_y = max_height / img_height if img_height > max_height else 1.0
        scale = min(scale_x, scale_y, 1.0)
        if scale < 1.0:
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            scaled_img = self.rendered_image.resize((new_width, new_height), Image.NEAREST)
        else:
            scaled_img = self.rendered_image
        self.tk_image = ImageTk.PhotoImage(scaled_img)
        return self.tk_image

    def export_png(self, output_path: str) -> bool:
        if self.rendered_image is None:
            print('Error: No tileset rendered')
            return False
        try:
            self.rendered_image.save(output_path, 'PNG')
            print(f'Tileset exported to: {output_path}')
            return True
        except Exception as e:
            print(f'Error exporting PNG: {e}')
            return False

    def clear(self):
        self.tilesets = []
        self.selected_tileset_index = None
        self.rendered_image = None
        self.tk_image = None
        print('TilesetRenderer: Cleared')
