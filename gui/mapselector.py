from pathlib import Path
from tkinter import messagebox
from load.maploader import MapLoader, MapData

class MapPair:

    def __init__(self, name, dat_path=None, tex_path=None):
        self.name = name
        self.dat_path = dat_path
        self.tex_path = tex_path

    def is_complete(self):
        return self.dat_path is not None and self.tex_path is not None

    def __str__(self):
        status = 'Ã¢Å“â€œ' if self.is_complete() else 'Ã¢Å¡ '
        return f'{status} {self.name}'

    def __repr__(self):
        return f"MapPair(name='{self.name}', dat={self.dat_path is not None}, tex={self.tex_path is not None})"

class MapSelector:

    def __init__(self):
        self.map_pairs = []
        self.selected_map = None
        self.map_loader = MapLoader()
        self.on_maps_loaded = None
        self.on_map_selected = None
        self.on_map_data_loaded = None
        self.map_loader.on_map_loaded = self._on_map_data_loaded

    def pair_map_files(self, dat_files, tex_files):
        self.map_pairs = []
        maps_dict = {}
        for dat_file in dat_files:
            map_name = self._extract_map_name(dat_file.name, '.map.dat')
            if map_name:
                if map_name not in maps_dict:
                    maps_dict[map_name] = MapPair(map_name)
                maps_dict[map_name].dat_path = dat_file
        for tex_file in tex_files:
            map_name = self._extract_map_name(tex_file.name, '.map.tex')
            if map_name:
                if map_name not in maps_dict:
                    maps_dict[map_name] = MapPair(map_name)
                maps_dict[map_name].tex_path = tex_file
        self.map_pairs = sorted(maps_dict.values(), key=lambda x: x.name)
        complete_maps = sum((1 for m in self.map_pairs if m.is_complete()))
        incomplete_maps = len(self.map_pairs) - complete_maps
        print(f'\n=== Map Pairing Results ===')
        print(f'Total maps found: {len(self.map_pairs)}')
        print(f'Complete pairs (DAT + TEX): {complete_maps}')
        print(f'Incomplete pairs: {incomplete_maps}')
        if incomplete_maps > 0:
            print('\nWarning: Incomplete map pairs found:')
            for map_pair in self.map_pairs:
                if not map_pair.is_complete():
                    missing = []
                    if map_pair.dat_path is None:
                        missing.append('DAT')
                    if map_pair.tex_path is None:
                        missing.append('TEX')
                    print(f"  - {map_pair.name}: Missing {', '.join(missing)}")
        print('===========================\n')
        if self.on_maps_loaded:
            self.on_maps_loaded(self.map_pairs)
        return self.map_pairs

    def _extract_map_name(self, filename, suffix):
        filename_lower = filename.lower()
        suffix_lower = suffix.lower()
        if filename_lower.endswith('.lz'):
            filename_lower = filename_lower[:-3]
            filename = filename[:-3]
        if suffix_lower in filename_lower:
            idx = filename_lower.find(suffix_lower)
            map_name = filename[:idx]
            return map_name
        return None

    def get_map_pairs(self):
        return self.map_pairs

    def get_complete_maps(self):
        return [m for m in self.map_pairs if m.is_complete()]

    def get_incomplete_maps(self):
        return [m for m in self.map_pairs if not m.is_complete()]

    def select_map(self, map_name):
        for map_pair in self.map_pairs:
            if map_pair.name == map_name:
                self.selected_map = map_pair
                print(f'\nMap selected: {map_name}')
                print(f'  DAT file: {map_pair.dat_path}')
                print(f'  TEX file: {map_pair.tex_path}')
                if self.on_map_selected:
                    self.on_map_selected(map_pair)
                if map_pair.is_complete():
                    self.map_loader.load_map(map_pair.dat_path, map_pair.tex_path, map_pair.name)
                else:
                    print(f"Warning: Cannot load incomplete map '{map_name}'")
                return map_pair
        print(f"Warning: Map '{map_name}' not found")
        return None

    def select_map_by_index(self, index):
        if 0 <= index < len(self.map_pairs):
            map_pair = self.map_pairs[index]
            return self.select_map(map_pair.name)
        print(f'Warning: Invalid map index {index}')
        return None

    def get_selected_map(self):
        return self.selected_map

    def get_loaded_map_data(self) -> MapData:
        return self.map_loader.get_current_map()

    def get_map_count(self):
        return len(self.map_pairs)

    def get_map_names(self):
        return [m.name for m in self.map_pairs]

    def get_complete_map_names(self):
        return [m.name for m in self.map_pairs if m.is_complete()]

    def get_layers(self):
        return self.map_loader.get_layers()

    def get_tilesets(self):
        return self.map_loader.get_tilesets()

    def get_tileset(self, index: int):
        return self.map_loader.get_tileset(index)

    def get_tileset_for_rendering(self, index: int):
        return self.map_loader.get_tileset_for_rendering(index)

    def get_all_tilesets_for_rendering(self):
        return self.map_loader.get_all_tilesets_for_rendering()

    def _on_map_data_loaded(self, map_data: MapData):
        print(f'Map data loaded callback triggered for: {map_data.map_name}')
        if self.on_map_data_loaded:
            self.on_map_data_loaded(map_data)

    def read_map_files(self, map_pair):
        if not map_pair.is_complete():
            print(f"Error: Cannot read incomplete map '{map_pair.name}'")
            return (None, None)
        try:
            with open(map_pair.dat_path, 'rb') as f:
                dat_data = f.read()
            with open(map_pair.tex_path, 'rb') as f:
                tex_data = f.read()
            print(f"Read map '{map_pair.name}': DAT={len(dat_data)} bytes, TEX={len(tex_data)} bytes")
            return (dat_data, tex_data)
        except Exception as e:
            print(f'Error reading map files: {e}')
            messagebox.showerror('Error', f'Failed to read map files: {str(e)}')
            return (None, None)
