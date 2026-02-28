import os
import struct
from pathlib import Path
from tkinter import filedialog, messagebox
import shutil
import mmap

class NDSHeader:

    def __init__(self, data):
        self.game_title = data[0:12].decode('ascii', errors='ignore').strip('\x00')
        self.game_code = data[12:16].decode('ascii', errors='ignore').strip('\x00')
        self.maker_code = data[16:18]
        self.arm9_rom_addr = struct.unpack('<I', data[32:36])[0]
        self.arm9_entry_addr = struct.unpack('<I', data[36:40])[0]
        self.arm9_ram_addr = struct.unpack('<I', data[40:44])[0]
        self.arm9_size = struct.unpack('<I', data[44:48])[0]
        self.arm7_rom_addr = struct.unpack('<I', data[48:52])[0]
        self.arm7_entry_addr = struct.unpack('<I', data[52:56])[0]
        self.arm7_ram_addr = struct.unpack('<I', data[56:60])[0]
        self.arm7_size = struct.unpack('<I', data[60:64])[0]
        self.filename_table_addr = struct.unpack('<I', data[64:68])[0]
        self.filename_size = struct.unpack('<I', data[68:72])[0]
        self.fat_addr = struct.unpack('<I', data[72:76])[0]
        self.fat_size = struct.unpack('<I', data[76:80])[0]
        self.rom_size = struct.unpack('<I', data[128:132])[0]
        self.header_size = struct.unpack('<I', data[132:136])[0]

class FatRange:

    def __init__(self, start_addr, end_addr):
        self.start_addr = start_addr
        self.end_addr = end_addr

    @property
    def size(self):
        return self.end_addr - self.start_addr

class FileIndexEntry:

    def __init__(self, path, fat_index):
        self.path = path
        self.fat_index = fat_index

    def __repr__(self):
        return f"FileIndexEntry(path='{self.path}', fat_index={self.fat_index})"

class ROMSelector:

    def __init__(self):
        self.rom_path = None
        self.extracted_path = None
        self.map_folder_path = None
        self.dat_files = []
        self.tex_files = []
        self._cancel_extraction = False

    def browse_rom(self):
        file_path = filedialog.askopenfilename(title='Select Pokemon Ranger: Shadows of Almia ROM', filetypes=[('NDS ROM files', '*.nds'), ('All files', '*.*')])
        if file_path:
            self.rom_path = file_path
            print(f'ROM selected: {self.rom_path}')
            return True
        return False

    def extract_rom(self, callback=None):
        if not self.rom_path:
            messagebox.showerror('Error', 'No ROM file selected!')
            return False
        self._cancel_extraction = False
        try:
            rom_name = Path(self.rom_path).stem
            self.extracted_path = Path(self.rom_path).parent / f'{rom_name}_extracted'
            if callback:
                callback('Reading ROM header...')
            header = self._parse_nds_header()
            if not header:
                messagebox.showerror('Error', 'Invalid NDS ROM file!')
                return False
            print(f'\n=== ROM Information ===')
            print(f'Game Title: {header.game_title}')
            print(f'Game Code: {header.game_code}')
            print(f'FAT Address: 0x{header.fat_addr:08X}, Size: {header.fat_size}')
            print(f'FNT Address: 0x{header.filename_table_addr:08X}, Size: {header.filename_size}')
            print(f'======================\n')
            if callback:
                callback('Building file index...')
            success = self._extract_map_files_targeted(header, callback)
            if not success or self._cancel_extraction:
                if self._cancel_extraction:
                    print('ROM extraction cancelled')
                else:
                    messagebox.showerror('Error', 'Failed to extract map files!')
                return False
            if callback:
                callback(f'Found {len(self.dat_files)} .map.dat files and {len(self.tex_files)} .map.tex files')
            print(f'\nExtraction complete. Found {len(self.dat_files)} DAT maps and {len(self.tex_files)} TEX maps')
            return True
        except Exception as e:
            messagebox.showerror('Error', f'ROM extraction failed: {str(e)}')
            print(f'Error during extraction: {e}')
            import traceback
            traceback.print_exc()
            return False

    def cancel_extraction(self):
        self._cancel_extraction = True

    def _parse_nds_header(self):
        try:
            with open(self.rom_path, 'rb') as f:
                header_data = f.read(512)
                if len(header_data) < 512:
                    return None
                return NDSHeader(header_data)
        except Exception as e:
            print(f'Error reading ROM header: {e}')
            return None

    def _extract_map_files_targeted(self, header, callback=None):
        try:
            if self.extracted_path.exists():
                shutil.rmtree(self.extracted_path)
            self.extracted_path.mkdir(parents=True, exist_ok=True)
            self.map_folder_path = self.extracted_path / 'data' / 'field' / 'map'
            with open(self.rom_path, 'rb') as rom_file:
                with mmap.mmap(rom_file.fileno(), 0, access=mmap.ACCESS_READ) as rom_data:
                    if callback:
                        callback('Loading FAT entries...')
                    fat_data = rom_data[header.fat_addr:header.fat_addr + header.fat_size]
                    fat_entries = []
                    for i in range(0, len(fat_data), 8):
                        if i + 8 <= len(fat_data):
                            start_addr = struct.unpack('<I', fat_data[i:i + 4])[0]
                            end_addr = struct.unpack('<I', fat_data[i + 4:i + 8])[0]
                            fat_entries.append(FatRange(start_addr, end_addr))
                    print(f'Loaded {len(fat_entries)} FAT entries')
                    if callback:
                        callback('Reading file name table...')
                    fnt_data = rom_data[header.filename_table_addr:header.filename_table_addr + header.filename_size]
                    if callback:
                        callback('Building file index...')
                    file_index = self._build_file_index(fnt_data)
                    print(f'Built index of {len(file_index)} files')
                    if callback:
                        callback('Filtering for map files...')
                    map_files = self._filter_map_files(file_index)
                    print(f'Found {len(map_files)} map files to extract')
                    if len(map_files) == 0:
                        print('Warning: No map files found in ROM!')
                        return False
                    if callback:
                        callback('Extracting map files...')
                    success = self._extract_filtered_files(rom_data, fat_entries, map_files, callback)
                    if not success:
                        return False
                    self._scan_map_files()
                    return True
        except Exception as e:
            print(f'Error in targeted extraction: {e}')
            import traceback
            traceback.print_exc()
            return False

    def _build_file_index(self, fnt_data):
        file_index = []
        try:
            self._index_directory(fnt_data, 61440, '', file_index)
        except Exception as e:
            print(f'Error building file index: {e}')
        return file_index

    def _index_directory(self, fnt_data, folder_id, current_path, file_index, fat_offset=[0]):
        try:
            current_offset = 8 * (folder_id & 4095)
            if current_offset + 8 > len(fnt_data):
                return
            entry_offset = struct.unpack('<I', fnt_data[current_offset:current_offset + 4])[0]
            first_file_id = struct.unpack('<H', fnt_data[current_offset + 4:current_offset + 6])[0]
            if isinstance(fat_offset, list) and len(fat_offset) == 1 and (fat_offset[0] == 0):
                fat_offset[0] = first_file_id
            offset = entry_offset
            while offset < len(fnt_data):
                control_byte = fnt_data[offset]
                if control_byte == 0:
                    break
                offset += 1
                name_length = control_byte & 127
                is_directory = bool(control_byte & 128)
                if offset + name_length > len(fnt_data):
                    break
                name = fnt_data[offset:offset + name_length].decode('utf-8', errors='replace')
                offset += name_length
                if current_path:
                    new_path = f'{current_path}/{name}'
                else:
                    new_path = name
                if is_directory:
                    if offset + 2 > len(fnt_data):
                        break
                    sub_folder_id = struct.unpack('<H', fnt_data[offset:offset + 2])[0]
                    offset += 2
                    self._index_directory(fnt_data, sub_folder_id, new_path, file_index, fat_offset)
                else:
                    file_index.append(FileIndexEntry(new_path, fat_offset[0]))
                    fat_offset[0] += 1
        except Exception as e:
            print(f'Error indexing directory: {e}')

    def _filter_map_files(self, file_index):
        map_files = []
        for entry in file_index:
            path_lower = entry.path.lower()
            if 'data/field/map/' in path_lower or 'data/field/map\\' in path_lower:
                if '.map.dat' in path_lower or '.map.tex' in path_lower:
                    map_files.append(entry)
                    print(f'  Map file: {entry.path} (FAT index: {entry.fat_index})')
        return map_files

    def _extract_filtered_files(self, rom_data, fat_entries, filtered_files, callback=None):
        try:
            self.map_folder_path.mkdir(parents=True, exist_ok=True)
            total_files = len(filtered_files)
            for i, file_entry in enumerate(filtered_files):
                if self._cancel_extraction:
                    return False
                if file_entry.fat_index >= len(fat_entries):
                    print(f'Warning: FAT index {file_entry.fat_index} out of range for {file_entry.path}')
                    continue
                fat_entry = fat_entries[file_entry.fat_index]
                if fat_entry.size <= 0:
                    continue
                filename = Path(file_entry.path).name
                output_path = self.map_folder_path / filename
                file_data = rom_data[fat_entry.start_addr:fat_entry.end_addr]
                try:
                    with open(output_path, 'wb') as f:
                        f.write(file_data)
                    if callback and (i % 10 == 0 or i == total_files - 1):
                        callback(f'Extracted {i + 1}/{total_files} map files...')
                except Exception as e:
                    print(f'Error writing file {output_path}: {e}')
            print(f'Extracted {total_files} map files to {self.map_folder_path}')
            return True
        except Exception as e:
            print(f'Error extracting filtered files: {e}')
            import traceback
            traceback.print_exc()
            return False

    def _scan_map_files(self):
        self.dat_files = []
        self.tex_files = []
        if not self.map_folder_path or not self.map_folder_path.exists():
            return
        print(f'\nScanning map folder: {self.map_folder_path}')
        file_count = 0
        for file_path in self.map_folder_path.iterdir():
            if file_path.is_file():
                file_name = file_path.name.lower()
                file_count += 1
                if '.map.dat' in file_name:
                    self.dat_files.append(file_path)
                elif '.map.tex' in file_name:
                    self.tex_files.append(file_path)
        self.dat_files.sort(key=lambda x: x.name)
        self.tex_files.sort(key=lambda x: x.name)
        print(f'Scan complete: {len(self.dat_files)} DAT files, {len(self.tex_files)} TEX files')

    def get_map_files(self):
        return (self.dat_files, self.tex_files)

    def get_map_folder(self):
        return self.map_folder_path
