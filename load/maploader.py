from pathlib import Path
from typing import Optional, Dict, List
from load.datparser import parse_dat_map
from load.texparser import parse_tex_map

class MapData:

    def __init__(self, map_name: str):
        self.map_name = map_name
        self.dat_data = None
        self.tex_data = None
        self.loaded = False

    def is_loaded(self):
        return self.loaded and self.dat_data is not None and (self.tex_data is not None)

    def get_tileset_count(self) -> int:
        if self.tex_data:
            return self.tex_data.get('tileset_count', 0)
        return 0

    def get_layer_count(self) -> int:
        if self.dat_data:
            return len(self.dat_data.get('layers', []))
        return 0

    def has_mpif(self) -> bool:
        return self.dat_data is not None and self.dat_data.get('mpif') is not None

    def has_txif(self) -> bool:
        return self.dat_data is not None and self.dat_data.get('txif') is not None

    def has_cta(self) -> bool:
        return self.dat_data is not None and self.dat_data.get('cta') is not None

class MapLoader:

    def __init__(self):
        self.current_map = None
        self.on_map_loaded = None

    def load_map(self, dat_path: Path, tex_path: Path, map_name: str) -> Optional[MapData]:
        try:
            print(f'\n=== Loading Map: {map_name} ===')
            map_data = MapData(map_name)
            print(f'Parsing DAT file: {dat_path.name}')
            dat_result = parse_dat_map(str(dat_path))
            if dat_result:
                map_data.dat_data = dat_result
                print(f"  - MPIF: {('Found' if dat_result.get('mpif') else 'Missing')}")
                print(f"  - TXIF: {('Found' if dat_result.get('txif') else 'Missing')}")
                print(f"  - Layers: {len(dat_result.get('layers', []))}")
                print(f"  - CTA: {('Found' if dat_result.get('cta') else 'Missing')}")
            else:
                print('  - ERROR: Failed to parse DAT file')
                return None
            print(f'Parsing TEX file: {tex_path.name}')
            tex_result = parse_tex_map(str(tex_path))
            if tex_result:
                map_data.tex_data = tex_result
                tileset_count = tex_result.get('tileset_count', 0)
                print(f'  - Tilesets: {tileset_count}')
                for ts in tex_result.get('tilesets', []):
                    idx = ts.get('index', -1)
                    has_rgcn = 'Yes' if ts.get('RGCN') else 'No'
                    has_rlcn = 'Yes' if ts.get('RLCN') else 'No'
                    print(f'    Tileset {idx}: RGCN={has_rgcn}, RLCN={has_rlcn}')
                    if 'error' in ts:
                        print(f"      ERROR: {ts['error']}")
                    elif 'warning' in ts:
                        print(f"      WARNING: {ts['warning']}")
            else:
                print('  - ERROR: Failed to parse TEX file')
                return None
            map_data.loaded = True
            self.current_map = map_data
            print(f'=== Map Loaded Successfully ===\n')
            if self.on_map_loaded:
                self.on_map_loaded(map_data)
            return map_data
        except Exception as e:
            print(f'ERROR loading map: {e}')
            import traceback
            traceback.print_exc()
            return None

    def get_current_map(self) -> Optional[MapData]:
        return self.current_map

    def get_layers(self) -> List[Dict]:
        if self.current_map and self.current_map.dat_data:
            return self.current_map.dat_data.get('layers', [])
        return []

    def get_tilesets(self) -> List[Dict]:
        if self.current_map and self.current_map.tex_data:
            return self.current_map.tex_data.get('tilesets', [])
        return []

    def get_tileset(self, index: int) -> Optional[Dict]:
        tilesets = self.get_tilesets()
        if 0 <= index < len(tilesets):
            return tilesets[index]
        return None

    def get_tileset_for_rendering(self, index: int) -> Optional[Dict]:
        tileset = self.get_tileset(index)
        if not tileset:
            return None
        rgcn = tileset.get('RGCN') or tileset.get('NCGR')
        rlcn = tileset.get('RLCN') or tileset.get('NCLR')
        render_data = {'index': index, 'RGCN': rgcn, 'RLCN': rlcn, 'NCGR': rgcn, 'NCLR': rlcn, 'has_graphics': rgcn is not None and len(rgcn) > 0, 'has_palette': rlcn is not None and len(rlcn) > 0}
        if 'error' in tileset:
            render_data['error'] = tileset['error']
        if 'warning' in tileset:
            render_data['warning'] = tileset['warning']
        return render_data

    def get_all_tilesets_for_rendering(self) -> List[Dict]:
        tilesets = self.get_tilesets()
        render_tilesets = []
        for i, ts in enumerate(tilesets):
            render_data = self.get_tileset_for_rendering(i)
            if render_data:
                render_tilesets.append(render_data)
        return render_tilesets

    def get_layer(self, layer_type: int) -> Optional[Dict]:
        layers = self.get_layers()
        for layer in layers:
            if layer.get('type') == layer_type:
                return layer
        return None

    def get_layer_data(self, layer_type: int) -> Optional[bytes]:
        layer = self.get_layer(layer_type)
        if layer:
            return layer.get('data')
        return None

    def clear(self):
        self.current_map = None
        print('MapLoader: Cleared current map data')
