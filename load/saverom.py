import struct
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
CRC16_TABLE = [0, 49345, 49537, 320, 49921, 960, 640, 49729, 50689, 1728, 1920, 51009, 1280, 50625, 50305, 1088, 52225, 3264, 3456, 52545, 3840, 53185, 52865, 3648, 2560, 51905, 52097, 2880, 51457, 2496, 2176, 51265, 55297, 6336, 6528, 55617, 6912, 56257, 55937, 6720, 7680, 57025, 57217, 8000, 56577, 7616, 7296, 56385, 5120, 54465, 54657, 5440, 55041, 6080, 5760, 54849, 53761, 4800, 4992, 54081, 4352, 53697, 53377, 4160, 61441, 12480, 12672, 61761, 13056, 62401, 62081, 12864, 13824, 63169, 63361, 14144, 62721, 13760, 13440, 62529, 15360, 64705, 64897, 15680, 65281, 16320, 16000, 65089, 64001, 15040, 15232, 64321, 14592, 63937, 63617, 14400, 10240, 59585, 59777, 10560, 60161, 11200, 10880, 59969, 60929, 11968, 12160, 61249, 11520, 60865, 60545, 11328, 58369, 9408, 9600, 58689, 9984, 59329, 59009, 9792, 8704, 58049, 58241, 9024, 57601, 8640, 8320, 57409, 40961, 24768, 24960, 41281, 25344, 41921, 41601, 25152, 26112, 42689, 42881, 26432, 42241, 26048, 25728, 42049, 27648, 44225, 44417, 27968, 44801, 28608, 28288, 44609, 43521, 27328, 27520, 43841, 26880, 43457, 43137, 26688, 30720, 47297, 47489, 31040, 47873, 31680, 31360, 47681, 48641, 32448, 32640, 48961, 32000, 48577, 48257, 31808, 46081, 29888, 30080, 46401, 30464, 47041, 46721, 30272, 29184, 45761, 45953, 29504, 45313, 29120, 28800, 45121, 20480, 37057, 37249, 20800, 37633, 21440, 21120, 37441, 38401, 22208, 22400, 38721, 21760, 38337, 38017, 21568, 39937, 23744, 23936, 40257, 24320, 40897, 40577, 24128, 23040, 39617, 39809, 23360, 39169, 22976, 22656, 38977, 34817, 18624, 18816, 35137, 19200, 35777, 35457, 19008, 19968, 36545, 36737, 20288, 36097, 19904, 19584, 35905, 17408, 33985, 34177, 17728, 34561, 18368, 18048, 34369, 33281, 17088, 17280, 33601, 16640, 33217, 32897, 16448]

def calculate_crc16(data: bytes) -> int:
    crc = 65535
    for byte in data:
        crc = crc >> 8 & 255 ^ CRC16_TABLE[(crc ^ byte) & 255]
    return crc & 65535

@dataclass
class NDSHeader:
    game_title: bytes = field(default_factory=lambda: b'\x00' * 12)
    game_code: bytes = field(default_factory=lambda: b'\x00' * 4)
    maker_code: bytes = field(default_factory=lambda: b'\x00' * 2)
    unit_code: int = 0
    device_type: int = 0
    device_size: int = 0
    reserved1: bytes = field(default_factory=lambda: b'\x00' * 9)
    rom_version: int = 0
    flags: int = 0
    arm9_rom_addr: int = 0
    arm9_entry_addr: int = 0
    arm9_ram_addr: int = 0
    arm9_size: int = 0
    arm7_rom_addr: int = 0
    arm7_entry_addr: int = 0
    arm7_ram_addr: int = 0
    arm7_size: int = 0
    filename_table_addr: int = 0
    filename_size: int = 0
    fat_addr: int = 0
    fat_size: int = 0
    arm9_overlay_addr: int = 0
    arm9_overlay_size: int = 0
    arm7_overlay_addr: int = 0
    arm7_overlay_size: int = 0
    normal_commands_settings: int = 0
    key1_commands_settings: int = 0
    icon_title_addr: int = 0
    secure_area_crc16: int = 0
    secure_area_loading_timeout: int = 0
    arm9_autoload_list_ram_addr: int = 0
    arm7_autoload_list_ram_addr: int = 0
    secure_area_disable: int = 0
    rom_size: int = 0
    header_size: int = 0
    reserved2: bytes = field(default_factory=lambda: b'\x00' * 56)
    nintendo_logo: bytes = field(default_factory=lambda: b'\x00' * 156)
    nintendo_logo_crc: int = 0
    header_crc16: int = 0
    debug_rom_addr: int = 0
    debug_size: int = 0
    debug_ram_addr: int = 0
    reserved3: bytes = field(default_factory=lambda: b'\x00' * 4)
    reserved4: bytes = field(default_factory=lambda: b'\x00' * 144)

    @classmethod
    def from_bytes(cls, data: bytes) -> 'NDSHeader':
        if len(data) < 512:
            raise ValueError(f'Header data too short: {len(data)} < 512 bytes')
        h = cls()
        h.game_title = data[0:12]
        h.game_code = data[12:16]
        h.maker_code = data[16:18]
        h.unit_code = data[18]
        h.device_type = data[19]
        h.device_size = data[20]
        h.reserved1 = data[21:30]
        h.rom_version = data[30]
        h.flags = data[31]
        h.arm9_rom_addr = struct.unpack_from('<I', data, 32)[0]
        h.arm9_entry_addr = struct.unpack_from('<I', data, 36)[0]
        h.arm9_ram_addr = struct.unpack_from('<I', data, 40)[0]
        h.arm9_size = struct.unpack_from('<I', data, 44)[0]
        h.arm7_rom_addr = struct.unpack_from('<I', data, 48)[0]
        h.arm7_entry_addr = struct.unpack_from('<I', data, 52)[0]
        h.arm7_ram_addr = struct.unpack_from('<I', data, 56)[0]
        h.arm7_size = struct.unpack_from('<I', data, 60)[0]
        h.filename_table_addr = struct.unpack_from('<I', data, 64)[0]
        h.filename_size = struct.unpack_from('<I', data, 68)[0]
        h.fat_addr = struct.unpack_from('<I', data, 72)[0]
        h.fat_size = struct.unpack_from('<I', data, 76)[0]
        h.arm9_overlay_addr = struct.unpack_from('<I', data, 80)[0]
        h.arm9_overlay_size = struct.unpack_from('<I', data, 84)[0]
        h.arm7_overlay_addr = struct.unpack_from('<I', data, 88)[0]
        h.arm7_overlay_size = struct.unpack_from('<I', data, 92)[0]
        h.normal_commands_settings = struct.unpack_from('<I', data, 96)[0]
        h.key1_commands_settings = struct.unpack_from('<I', data, 100)[0]
        h.icon_title_addr = struct.unpack_from('<I', data, 104)[0]
        h.secure_area_crc16 = struct.unpack_from('<H', data, 108)[0]
        h.secure_area_loading_timeout = struct.unpack_from('<H', data, 110)[0]
        h.arm9_autoload_list_ram_addr = struct.unpack_from('<I', data, 112)[0]
        h.arm7_autoload_list_ram_addr = struct.unpack_from('<I', data, 116)[0]
        h.secure_area_disable = struct.unpack_from('<Q', data, 120)[0]
        h.rom_size = struct.unpack_from('<I', data, 128)[0]
        h.header_size = struct.unpack_from('<I', data, 132)[0]
        h.reserved2 = data[136:192]
        h.nintendo_logo = data[192:348]
        h.nintendo_logo_crc = struct.unpack_from('<H', data, 348)[0]
        h.header_crc16 = struct.unpack_from('<H', data, 350)[0]
        h.debug_rom_addr = struct.unpack_from('<I', data, 352)[0]
        h.debug_size = struct.unpack_from('<I', data, 356)[0]
        h.debug_ram_addr = struct.unpack_from('<I', data, 360)[0]
        h.reserved3 = data[364:368]
        h.reserved4 = data[368:512]
        return h

    def to_bytes(self) -> bytes:
        data = bytearray(512)
        data[0:12] = self.game_title
        data[12:16] = self.game_code
        data[16:18] = self.maker_code
        data[18] = self.unit_code
        data[19] = self.device_type
        data[20] = self.device_size
        data[21:30] = self.reserved1
        data[30] = self.rom_version
        data[31] = self.flags
        struct.pack_into('<I', data, 32, self.arm9_rom_addr)
        struct.pack_into('<I', data, 36, self.arm9_entry_addr)
        struct.pack_into('<I', data, 40, self.arm9_ram_addr)
        struct.pack_into('<I', data, 44, self.arm9_size)
        struct.pack_into('<I', data, 48, self.arm7_rom_addr)
        struct.pack_into('<I', data, 52, self.arm7_entry_addr)
        struct.pack_into('<I', data, 56, self.arm7_ram_addr)
        struct.pack_into('<I', data, 60, self.arm7_size)
        struct.pack_into('<I', data, 64, self.filename_table_addr)
        struct.pack_into('<I', data, 68, self.filename_size)
        struct.pack_into('<I', data, 72, self.fat_addr)
        struct.pack_into('<I', data, 76, self.fat_size)
        struct.pack_into('<I', data, 80, self.arm9_overlay_addr)
        struct.pack_into('<I', data, 84, self.arm9_overlay_size)
        struct.pack_into('<I', data, 88, self.arm7_overlay_addr)
        struct.pack_into('<I', data, 92, self.arm7_overlay_size)
        struct.pack_into('<I', data, 96, self.normal_commands_settings)
        struct.pack_into('<I', data, 100, self.key1_commands_settings)
        struct.pack_into('<I', data, 104, self.icon_title_addr)
        struct.pack_into('<H', data, 108, self.secure_area_crc16)
        struct.pack_into('<H', data, 110, self.secure_area_loading_timeout)
        struct.pack_into('<I', data, 112, self.arm9_autoload_list_ram_addr)
        struct.pack_into('<I', data, 116, self.arm7_autoload_list_ram_addr)
        struct.pack_into('<Q', data, 120, self.secure_area_disable)
        struct.pack_into('<I', data, 128, self.rom_size)
        struct.pack_into('<I', data, 132, self.header_size)
        data[136:192] = self.reserved2
        data[192:348] = self.nintendo_logo
        struct.pack_into('<H', data, 348, self.nintendo_logo_crc)
        struct.pack_into('<H', data, 350, self.header_crc16)
        struct.pack_into('<I', data, 352, self.debug_rom_addr)
        struct.pack_into('<I', data, 356, self.debug_size)
        struct.pack_into('<I', data, 360, self.debug_ram_addr)
        data[364:368] = self.reserved3
        data[368:512] = self.reserved4
        return bytes(data)

    def update_crc(self):
        self.header_crc16 = calculate_crc16(self.to_bytes()[:350])

    @property
    def game_title_str(self) -> str:
        return self.game_title.decode('ascii', errors='ignore').strip('\x00')

    @property
    def game_code_str(self) -> str:
        return self.game_code.decode('ascii', errors='ignore')

    @property
    def fat_entry_count(self) -> int:
        return self.fat_size // 8

@dataclass
class FATEntry:
    start_addr: int
    end_addr: int

    @property
    def size(self) -> int:
        return self.end_addr - self.start_addr

    @classmethod
    def from_bytes(cls, data: bytes) -> 'FATEntry':
        start, end = struct.unpack('<II', data[0:8])
        return cls(start, end)

    def to_bytes(self) -> bytes:
        return struct.pack('<II', self.start_addr, self.end_addr)

    def __repr__(self):
        return f'FATEntry(start=0x{self.start_addr:08X}  end=0x{self.end_addr:08X}  size={self.size:,})'
MOD_TYPE_LABELS: Dict[str, str] = {'layer_swap': 'Layer Swap', 'import_tileset': 'Import Tileset', 'png_transfer': 'PNG Transfer', 'map_modification': 'Map Modification', 'direct': 'Direct Replace'}

@dataclass
class ModificationRecord:
    file_path: Path
    new_data: bytes
    mod_type: str
    timestamp: datetime = field(default_factory=datetime.now)
    fat_index: int = -1

    @property
    def label(self) -> str:
        return MOD_TYPE_LABELS.get(self.mod_type, self.mod_type)

    @property
    def size(self) -> int:
        return len(self.new_data)

    @property
    def resolved(self) -> bool:
        return self.fat_index >= 0

    def __str__(self):
        status = f'FAT#{self.fat_index}' if self.resolved else 'unresolved'
        return f"[{self.label}] {self.file_path.name}  {self.size:,} bytes  {status}  @ {self.timestamp.strftime('%H:%M:%S')}"

class ModificationTracker:

    def __init__(self):
        self._mods: Dict[str, ModificationRecord] = {}
        print('[ModificationTracker] Initialized')

    def register(self, file_path: Path, new_data: bytes, mod_type: str='direct') -> bool:
        if not new_data:
            print(f'[ModificationTracker] WARNING: empty data for {file_path.name} — skipping')
            return False
        key = str(file_path.resolve())
        is_new = key not in self._mods
        record = ModificationRecord(file_path=file_path.resolve(), new_data=new_data, mod_type=mod_type)
        self._mods[key] = record
        action = 'Added' if is_new else 'Updated'
        print(f'[ModificationTracker] {action}: {record}')
        return True

    def register_from_disk(self, file_path: Path, mod_type: str='direct') -> bool:
        try:
            data = Path(file_path).read_bytes()
            return self.register(Path(file_path), data, mod_type)
        except Exception as e:
            print(f'[ModificationTracker] ERROR reading {file_path}: {e}')
            return False

    def register_map_files(self, dat_path: Path, tex_path: Path, mod_type: str='map_modification') -> bool:
        ok1 = self.register_from_disk(Path(dat_path), mod_type)
        ok2 = self.register_from_disk(Path(tex_path), mod_type)
        if ok1 and ok2:
            print(f'[ModificationTracker] Map pair registered: {Path(dat_path).name} + {Path(tex_path).name}')
        return ok1 and ok2

    def has_modifications(self) -> bool:
        return bool(self._mods)

    def count(self) -> int:
        return len(self._mods)

    def count_by_type(self, mod_type: str) -> int:
        return sum((1 for m in self._mods.values() if m.mod_type == mod_type))

    def get_all(self) -> List[ModificationRecord]:
        return list(self._mods.values())

    def get_by_type(self, mod_type: str) -> List[ModificationRecord]:
        return [m for m in self._mods.values() if m.mod_type == mod_type]

    def get_summary(self) -> Dict:
        mods = self.get_all()
        by_type: Dict[str, int] = {}
        total_size = 0
        files: List[Dict] = []
        for m in mods:
            by_type[m.mod_type] = by_type.get(m.mod_type, 0) + 1
            total_size += m.size
            files.append({'name': m.file_path.name, 'path': str(m.file_path), 'type': m.mod_type, 'label': m.label, 'size': m.size, 'timestamp': m.timestamp.strftime('%H:%M:%S'), 'resolved': m.resolved, 'fat_index': m.fat_index})
        return {'total_count': len(mods), 'by_type': by_type, 'total_size': total_size, 'files': files}

    def get_display_lines(self) -> List[str]:
        mods = self.get_all()
        if not mods:
            return ['No modifications registered.']
        lines: List[str] = []
        lines.append(f'Pending modifications: {len(mods)}')
        lines.append('─' * 50)
        by_type: Dict[str, List[ModificationRecord]] = {}
        for m in mods:
            by_type.setdefault(m.mod_type, []).append(m)
        for mod_type, group in by_type.items():
            label = MOD_TYPE_LABELS.get(mod_type, mod_type)
            lines.append(f'\n  {label} ({len(group)}):')
            for m in group:
                status = f'FAT#{m.fat_index}' if m.resolved else 'pending'
                lines.append(f'    • {m.file_path.name}  ({m.size:,} bytes)  [{status}]')
        return lines

    def clear(self):
        self._mods.clear()
        print('[ModificationTracker] Cleared all modifications')

    def remove(self, file_path: Path) -> bool:
        key = str(file_path.resolve())
        if key in self._mods:
            del self._mods[key]
            print(f'[ModificationTracker] Removed: {file_path.name}')
            return True
        return False

class FNTParser:

    def parse(self, rom_data: bytes, fnt_offset: int, fnt_size: int) -> Dict[str, int]:
        index: Dict[str, int] = {}
        try:
            self._walk_dir(rom_data, fnt_offset, fnt_size, dir_id=61440, parent_path='', index=index)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f'[FNTParser] Error during walk: {e}')
        print(f'[FNTParser] Built index: {len(index)} files')
        return index

    def _walk_dir(self, rom: bytes, fnt_base: int, fnt_size: int, dir_id: int, parent_path: str, index: Dict[str, int]):
        dir_num = dir_id & 4095
        dir_entry_offset = fnt_base + dir_num * 8
        if dir_entry_offset + 8 > len(rom):
            return
        entries_rel = struct.unpack_from('<I', rom, dir_entry_offset)[0]
        first_idx = struct.unpack_from('<H', rom, dir_entry_offset + 4)[0]
        pos = fnt_base + entries_rel
        current_file_idx = first_idx
        fnt_end = fnt_base + fnt_size
        while pos < fnt_end and pos < len(rom):
            type_len = rom[pos]
            pos += 1
            if type_len == 0:
                break
            is_subdir = bool(type_len & 128)
            name_len = type_len & 127
            if pos + name_len > len(rom):
                break
            name = rom[pos:pos + name_len].decode('ascii', errors='replace')
            pos += name_len
            full_path = (f'{parent_path}/{name}' if parent_path else name).lower()
            if is_subdir:
                if pos + 2 > len(rom):
                    break
                sub_dir_id = struct.unpack_from('<H', rom, pos)[0]
                pos += 2
                self._walk_dir(rom, fnt_base, fnt_size, sub_dir_id, full_path, index)
            else:
                index[full_path] = current_file_idx
                current_file_idx += 1

class ROMModificationCache:

    def __init__(self):
        self.tracker: ModificationTracker = ModificationTracker()
        self.original_rom_path: Optional[Path] = None
        self.header: Optional[NDSHeader] = None
        self._fat_index_map: Dict[str, int] = {}
        self._fat_index_map_built: bool = False
        print('[ROMModificationCache] Initialized')

    def has_modifications(self) -> bool:
        return self.tracker.has_modifications()

    def get_modification_count(self) -> int:
        return self.tracker.count()

    def get_modified_files(self) -> List[ModificationRecord]:
        return self.tracker.get_all()

    def add_modification(self, file_path: Path, new_data: bytes, modification_type: str='direct') -> bool:
        return self.tracker.register(file_path, new_data, modification_type)

    def clear(self):
        self.tracker.clear()
        self._fat_index_map = {}
        self._fat_index_map_built = False

    def set_rom_path(self, rom_path: Path):
        self.original_rom_path = rom_path
        self._fat_index_map_built = False
        print(f'[ROMModificationCache] ROM path set: {rom_path}')

    def load_header(self, rom_path: Path) -> bool:
        try:
            with open(rom_path, 'rb') as f:
                raw = f.read(512)
            self.header = NDSHeader.from_bytes(raw)
            print(f"[ROMModificationCache] Header loaded: '{self.header.game_title_str}' ({self.header.game_code_str})")
            print(f'  ROM size   : {self.header.rom_size:,} bytes')
            print(f'  FAT entries: {self.header.fat_entry_count} @ 0x{self.header.fat_addr:08X}')
            print(f'  FNT size   : {self.header.filename_size:,} bytes @ 0x{self.header.filename_table_addr:08X}')
            return True
        except Exception as e:
            print(f'[ROMModificationCache] ERROR loading header: {e}')
            return False

    def build_file_index(self, rom_path: Path) -> bool:
        if not self.header:
            print('[ROMModificationCache] Cannot build index: header not loaded')
            return False
        try:
            with open(rom_path, 'rb') as f:
                rom_data = f.read()
            parser = FNTParser()
            self._fat_index_map = parser.parse(rom_data, self.header.filename_table_addr, self.header.filename_size)
            self._fat_index_map_built = True
            print(f'[ROMModificationCache] File index built: {len(self._fat_index_map)} entries')
            return True
        except Exception as e:
            print(f'[ROMModificationCache] ERROR building file index: {e}')
            return False

    def resolve_fat_index(self, file_path: Path) -> int:
        if not self._fat_index_map_built:
            print('[ROMModificationCache] WARNING: FNT index not built yet; call build_file_index() first')
        abs_str = str(file_path.resolve()).replace('\\', '/')
        if self.original_rom_path:
            extracted_root = self.original_rom_path.parent / (self.original_rom_path.stem + '_extracted')
            root_str = str(extracted_root).replace('\\', '/').lower()
            lower_str = abs_str.lower()
            if lower_str.startswith(root_str):
                rel = lower_str[len(root_str):].lstrip('/')
                if rel in self._fat_index_map:
                    return self._fat_index_map[rel]
        parts = abs_str.lower().split('/')
        for start in range(len(parts)):
            candidate = '/'.join(parts[start:])
            if candidate in self._fat_index_map:
                idx = self._fat_index_map[candidate]
                print(f"[ROMModificationCache] Suffix match: '{candidate}' → FAT#{idx}")
                return idx
        print(f'[ROMModificationCache] WARN: no FAT index for {file_path.name}')
        return -1

class ROMBuilder:

    def __init__(self, cache: 'ROMModificationCache'):
        self.cache = cache

    def build_rom(self, output_path: Path, progress_callback=None) -> Tuple[bool, str]:
        try:
            if not self.cache.original_rom_path:
                return (False, 'No original ROM path set.  Load a ROM first.')
            if not self.cache.original_rom_path.exists():
                return (False, f'Original ROM not found:\n{self.cache.original_rom_path}')
            if not self.cache.header:
                return (False, 'ROM header not loaded.  Call initialize() first.')
            if not self.cache.has_modifications():
                return (False, 'No modifications are registered to save.')
            divider = '=' * 60
            print(f'\n{divider}')
            print('ROM BUILD START')
            print(f'  Source : {self.cache.original_rom_path.name}')
            print(f'  Output : {output_path.name}')
            print(f'  Mods   : {self.cache.get_modification_count()}')
            print(divider)
            if not self.cache._fat_index_map_built:
                _progress(progress_callback, 'Building ROM file index...')
                self.cache.build_file_index(self.cache.original_rom_path)
            mods = self.cache.get_modified_files()
            for mod in mods:
                if not mod.resolved:
                    mod.fat_index = self.cache.resolve_fat_index(mod.file_path)
            resolvable = [m for m in mods if m.resolved]
            unresolvable = [m for m in mods if not m.resolved]
            if unresolvable:
                names = ', '.join((m.file_path.name for m in unresolvable))
                print(f'WARNING: {len(unresolvable)} mod(s) unresolved: {names}')
            if not resolvable:
                return (False, "None of the registered modifications could be matched\nto entries in the ROM's File Allocation Table.\n\nEnsure the ROM was extracted properly and the FNT index\nwas built before saving.")
            _progress(progress_callback, 'Copying original ROM…')
            shutil.copy2(self.cache.original_rom_path, output_path)
            print('Step 1: ROM copied')
            _progress(progress_callback, 'Loading File Allocation Table…')
            fat_entries = self._load_fat()
            if fat_entries is None:
                return (False, 'Failed to read the File Allocation Table.')
            print(f'Step 2: FAT loaded — {len(fat_entries)} entries')
            _progress(progress_callback, f'Applying {len(resolvable)} modification(s)…')
            modified_fat = self._apply_modifications(output_path, fat_entries, resolvable, progress_callback)
            if modified_fat is None:
                return (False, 'Failed to apply modifications to ROM.')
            print('Step 3: Modifications applied')
            _progress(progress_callback, 'Writing updated File Allocation Table…')
            if not self._write_fat(output_path, modified_fat):
                return (False, 'Failed to write updated FAT to ROM.')
            print('Step 4: FAT written')
            _progress(progress_callback, 'Updating ROM header…')
            if not self._update_header(output_path):
                return (False, 'Failed to update ROM header.')
            print('Step 5: Header updated')
            final_size = output_path.stat().st_size
            summary_lines = [f'ROM saved successfully!', f'', f'Modifications applied : {len(resolvable)}', f'Final ROM size        : {final_size:,} bytes']
            if unresolvable:
                summary_lines += [f'', f'NOTE: {len(unresolvable)} modification(s) could not be matched to FAT entries and were skipped:']
                for m in unresolvable:
                    summary_lines.append(f'  • {m.file_path.name}')
            msg = '\n'.join(summary_lines)
            print(f'\n{divider}')
            print('ROM BUILD COMPLETE')
            print(msg)
            print(f'{divider}\n')
            return (True, msg)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return (False, f'ROM build failed with an unexpected error:\n{e}')

    def _load_fat(self) -> Optional[List[FATEntry]]:
        try:
            with open(self.cache.original_rom_path, 'rb') as f:
                f.seek(self.cache.header.fat_addr)
                fat_raw = f.read(self.cache.header.fat_size)
            entries: List[FATEntry] = []
            for i in range(0, len(fat_raw), 8):
                if i + 8 <= len(fat_raw):
                    entries.append(FATEntry.from_bytes(fat_raw[i:i + 8]))
            return entries
        except Exception as e:
            print(f'[ROMBuilder] ERROR loading FAT: {e}')
            return None

    def _apply_modifications(self, rom_path: Path, fat_entries: List[FATEntry], mods: List[ModificationRecord], progress_callback=None) -> Optional[List[FATEntry]]:
        try:
            with open(rom_path, 'r+b') as rom_file:
                modified_fat = list(fat_entries)
                current_rom_end = rom_file.seek(0, 2)
                for i, mod in enumerate(mods):
                    if progress_callback and i % 5 == 0:
                        progress_callback(f'Writing mod {i + 1}/{len(mods)}: {mod.file_path.name}…')
                    idx = mod.fat_index
                    if idx < 0 or idx >= len(modified_fat):
                        print(f'  SKIP: FAT#{idx} out of range for {mod.file_path.name}')
                        continue
                    old_entry = modified_fat[idx]
                    old_size = old_entry.size
                    new_size = mod.size
                    print(f'  [{i + 1}/{len(mods)}] FAT#{idx}  {mod.file_path.name}  {old_size:,} → {new_size:,} bytes')
                    if new_size <= old_size:
                        rom_file.seek(old_entry.start_addr)
                        rom_file.write(mod.new_data)
                        modified_fat[idx] = FATEntry(old_entry.start_addr, old_entry.start_addr + new_size)
                        print(f'    In-place @ 0x{old_entry.start_addr:08X}')
                    else:
                        aligned_end = _align4(current_rom_end)
                        if aligned_end > current_rom_end:
                            rom_file.seek(current_rom_end)
                            rom_file.write(b'\xff' * (aligned_end - current_rom_end))
                        rom_file.seek(aligned_end)
                        rom_file.write(mod.new_data)
                        modified_fat[idx] = FATEntry(aligned_end, aligned_end + new_size)
                        current_rom_end = aligned_end + new_size
                        print(f'    Appended @ 0x{aligned_end:08X}')
            return modified_fat
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f'[ROMBuilder] ERROR applying modifications: {e}')
            return None

    def _write_fat(self, rom_path: Path, fat_entries: List[FATEntry]) -> bool:
        try:
            fat_raw = bytearray()
            for entry in fat_entries:
                fat_raw.extend(entry.to_bytes())
            with open(rom_path, 'r+b') as f:
                f.seek(self.cache.header.fat_addr)
                f.write(fat_raw)
            print(f'[ROMBuilder] FAT written: {len(fat_entries)} entries  ({len(fat_raw):,} bytes)')
            return True
        except Exception as e:
            print(f'[ROMBuilder] ERROR writing FAT: {e}')
            return False

    def _update_header(self, rom_path: Path) -> bool:
        try:
            rom_size = rom_path.stat().st_size
            self.cache.header.rom_size = rom_size
            self.cache.header.update_crc()
            header_bytes = self.cache.header.to_bytes()
            with open(rom_path, 'r+b') as f:
                f.seek(0)
                f.write(header_bytes)
            print(f'[ROMBuilder] Header updated: size={rom_size:,}  CRC=0x{self.cache.header.header_crc16:04X}')
            return True
        except Exception as e:
            print(f'[ROMBuilder] ERROR updating header: {e}')
            return False

def _align4(value: int) -> int:
    return value + 3 & ~3

def _progress(callback, message: str):
    if callback:
        try:
            callback(message)
        except Exception:
            pass
    print(f'  [progress] {message}')

class ROMSaver:

    def __init__(self):
        self.cache = ROMModificationCache()
        self.builder = ROMBuilder(self.cache)
        print('[ROMSaver] Ready')

    def initialize(self, rom_path: Path) -> bool:
        print(f'\n[ROMSaver] Initializing: {rom_path.name}')
        self.cache.set_rom_path(rom_path)
        if not self.cache.load_header(rom_path):
            print('[ROMSaver] FAILED: could not load ROM header')
            return False
        if not self.cache.build_file_index(rom_path):
            print('[ROMSaver] WARNING: FNT index could not be built; FAT resolution will attempt lazy build at save time')
        print('[ROMSaver] Initialization complete\n')
        return True

    def is_initialized(self) -> bool:
        return self.cache.original_rom_path is not None and self.cache.header is not None

    def get_rom_info(self) -> Optional[Dict]:
        if not self.is_initialized():
            return None
        h = self.cache.header
        return {'title': h.game_title_str, 'code': h.game_code_str, 'rom_size': h.rom_size, 'fat_entries': h.fat_entry_count, 'path': str(self.cache.original_rom_path)}

    def register_modification(self, file_path: Path, new_data: bytes, mod_type: str='direct') -> bool:
        return self.cache.tracker.register(file_path, new_data, mod_type)

    def register_file_on_disk(self, file_path: Path, mod_type: str='direct') -> bool:
        return self.cache.tracker.register_from_disk(file_path, mod_type)

    def add_modified_map_files(self, dat_path: Path, tex_path: Path) -> bool:
        return self.cache.tracker.register_map_files(dat_path, tex_path, mod_type='map_modification')

    def has_modifications(self) -> bool:
        return self.cache.has_modifications()

    def get_modification_count(self) -> int:
        return self.cache.get_modification_count()

    def get_layer_swap_count(self) -> int:
        return self.cache.tracker.count_by_type('layer_swap')

    def get_modification_summary(self) -> Dict:
        return self.cache.tracker.get_summary()

    def get_status_lines(self) -> List[str]:
        return self.cache.tracker.get_display_lines()

    def get_layer_swap_files(self) -> List[Dict]:
        mods = self.cache.tracker.get_by_type('layer_swap')
        return [{'name': m.file_path.name, 'path': str(m.file_path), 'size': m.size, 'timestamp': m.timestamp.strftime('%H:%M:%S'), 'resolved': m.resolved, 'fat_index': m.fat_index} for m in mods]

    def save_rom(self, output_path: Path, progress_callback=None) -> Tuple[bool, str]:
        if not self.is_initialized():
            return (False, 'ROM is not initialized.\nLoad a ROM before saving.')
        if not self.has_modifications():
            return (False, 'No modifications are queued to save.')
        return self.builder.build_rom(output_path, progress_callback)

    def clear_modifications(self):
        self.cache.clear()
        print('[ROMSaver] Modifications cleared')

    def remove_modification(self, file_path: Path) -> bool:
        return self.cache.tracker.remove(file_path)

    def reset(self):
        self.cache.clear()
        self.cache.original_rom_path = None
        self.cache.header = None
        self.cache._fat_index_map_built = False
        print('[ROMSaver] Full reset')
