import struct
import traceback
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from PyQt6.QtWidgets import QWidget, QFrame, QLabel, QPushButton, QHBoxLayout, QVBoxLayout, QSizePolicy, QMessageBox, QFileDialog
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
LAYER_TYPE_INFO: Dict[int, Tuple[str, str]] = {1: ('0x01', 'PRIORITY / BASE'), 2: ('0x02', 'COMBINED TILEMAP'), 3: ('0x03', 'COLLISION'), 4: ('0x04', 'OBJECTS'), 5: ('0x05', 'STATIC ALT TILEMAP'), 6: ('0x06', 'ATTRIBUTES'), 7: ('0x07', 'TRIGGERS'), 8: ('0x08', 'NPCs'), 9: ('0x09', 'POKEMON SPAWNS'), 10: ('0x0A', 'MULTI-SCROLL'), 11: ('0x0B', 'UV SCROLL'), 12: ('0x0C', 'COLOR ANIMATION'), 13: ('0x0D', 'SHADOW / OVERLAY'), 14: ('0x0E', 'CHARACTER TRANSFORM')}
COLOR_BG_MAIN = '#182d55'
COLOR_ELEMENT_BG = '#26395e'
COLOR_ACCENT = '#6d86a8'
COLOR_HOVER = '#354a75'
COLOR_TEXT = '#FFFFFF'
COLOR_MODIFIED = '#FFD700'
COLOR_INFO = '#a8c4e0'
COLOR_TYPE_BADGE = '#1e4d7a'
COLOR_ROOT = '#1a3a6e'
COLOR_SECTION = '#26395e'
COLOR_LEAF = '#2d4470'

def _make_frame(color: str, border: bool=False, radius: int=5, parent: QWidget=None) -> QFrame:
    frame = QFrame(parent)
    border_css = f"border: {('2px' if border else '1px')} solid {COLOR_ACCENT};" if border else ''
    frame.setStyleSheet(f'\n        QFrame {{\n            background-color: {color};\n            border-radius: {radius}px;\n            {border_css}\n        }}\n    ')
    return frame

def _make_label(text: str, color: str=COLOR_TEXT, bold: bool=False, size: int=10, parent: QWidget=None) -> QLabel:
    lbl = QLabel(text, parent)
    weight = QFont.Weight.Bold if bold else QFont.Weight.Normal
    lbl.setFont(QFont('Arial', size, weight))
    lbl.setStyleSheet(f'color: {color}; background: transparent; border: none;')
    return lbl

def _make_button(text: str, width: int=80, height: int=25, size: int=9, parent: QWidget=None) -> QPushButton:
    btn = QPushButton(text, parent)
    btn.setFont(QFont('Arial', size))
    btn.setFixedSize(width, height)
    btn.setStyleSheet(f'\n        QPushButton {{\n            background-color: {COLOR_ELEMENT_BG};\n            color: {COLOR_TEXT};\n            border: 1px solid {COLOR_ACCENT};\n            border-radius: 5px;\n        }}\n        QPushButton:hover {{\n            background-color: {COLOR_HOVER};\n        }}\n    ')
    return btn

def _make_expand_btn(text: str, level: int, parent: QWidget=None) -> QPushButton:
    size = 30 if level == 0 else 25
    btn = QPushButton(text, parent)
    btn.setFont(QFont('Arial', 14 if level == 0 else 12, QFont.Weight.Bold))
    btn.setFixedSize(size, size)
    btn.setStyleSheet(f'\n        QPushButton {{\n            background-color: {COLOR_ELEMENT_BG};\n            color: {COLOR_TEXT};\n            border: 1px solid {COLOR_ACCENT};\n            border-radius: 5px;\n        }}\n        QPushButton:hover {{\n            background-color: {COLOR_HOVER};\n        }}\n    ')
    return btn

def _read_mpif_info(data: bytes) -> str:
    if not data or len(data) < 12:
        return 'no data'
    if data[:4] != b'MPIF':
        return 'invalid MPIF'
    try:
        width, height = struct.unpack_from('<II', data, 4)
        return f'{width} x {height} px  ({width // 16} x {height // 16} tiles)'
    except Exception:
        return 'parse error'

def _read_txif_info(data: bytes) -> str:
    if not data or len(data) < 8:
        return 'no data'
    if data[:4] != b'TXIF':
        return 'invalid TXIF'
    try:
        count = struct.unpack_from('<H', data, 4)[0]
        return f"{count} tileset {('entry' if count == 1 else 'entries')}"
    except Exception:
        return 'parse error'

def _read_layer_entry_info(layer_type: int, data: bytes) -> str:
    if not data or len(data) < 8:
        return ''
    try:
        if layer_type == 9:
            count = struct.unpack_from('<I', data, 4)[0]
            if count <= 50:
                return f"{count} spawn{('s' if count != 1 else '')}"
        elif layer_type == 8:
            count = struct.unpack_from('<I', data, 4)[0]
            if count <= 50:
                return f"{count} NPC{('s' if count != 1 else '')}"
        elif layer_type == 7:
            count = struct.unpack_from('<I', data, 4)[0]
            if count <= 200:
                return f"{count} trigger{('s' if count != 1 else '')}"
        elif layer_type == 3:
            if len(data) >= 20:
                gw, gh = struct.unpack_from('<II', data, 12)
                if 0 < gw < 2000 and 0 < gh < 2000:
                    return f'grid {gw} x {gh}'
    except Exception:
        pass
    return ''

def _detect_tileset_type(rgcn: Optional[bytes], rlcn: Optional[bytes]) -> str:
    if not rgcn or not rlcn:
        return 'INCOMPLETE'
    if len(rlcn) >= 44:
        try:
            c0 = struct.unpack_from('<H', rlcn, 40)[0]
            c1 = struct.unpack_from('<H', rlcn, 42)[0]
            if c0 == 14233 and c1 == 30720:
                return 'SHADOW'
        except Exception:
            pass
    RGCN_DATA_OFFSET = 48
    if len(rgcn) > RGCN_DATA_OFFSET + 32:
        sample = rgcn[RGCN_DATA_OFFSET:RGCN_DATA_OFFSET + 64]
        unique = len(set(sample))
        if unique <= 2:
            return 'COLOR FILL'
        if unique <= 8:
            return 'PATTERN FILL'
    return 'NORMAL'

class LayerNode:

    def __init__(self, name: str, data: bytes=None, node_type: str='layer', parent=None, level: int=0):
        self.name = name
        self.data = data
        self.node_type = node_type
        self.parent = parent
        self.children: List['LayerNode'] = []
        self.is_expanded = False
        self.level = level
        self.frame: Optional[QFrame] = None
        self.children_container: Optional[QWidget] = None
        self.expand_button: Optional[QPushButton] = None
        self.name_label: Optional[QLabel] = None
        self.info_label: Optional[QLabel] = None
        self.swap_button: Optional[QPushButton] = None
        self.export_button: Optional[QPushButton] = None
        self.layer_index: Optional[int] = None
        self.layer_type: Optional[int] = None
        self.tileset_index: Optional[int] = None
        self.component: Optional[str] = None
        self.info_text: str = ''

    def add_child(self, child: 'LayerNode'):
        child.parent = self
        child.level = self.level + 1
        self.children.append(child)

    def can_expand(self) -> bool:
        return len(self.children) > 0

    def get_path(self) -> str:
        parts, node = ([], self)
        while node:
            parts.insert(0, node.name)
            node = node.parent
        return ' > '.join(parts)

    def get_bg_color(self) -> str:
        if self.level == 0:
            return COLOR_ROOT
        if self.level == 1:
            return COLOR_SECTION
        return COLOR_LEAF

class LayerSwap:

    def __init__(self):
        self.root_nodes: List[LayerNode] = []
        self.current_map_name: Optional[str] = None
        self.modified_layers: Dict[str, bytes] = {}
        self._map_data = None
        self._dat_path: Optional[Path] = None
        self._tex_path: Optional[Path] = None
        self._rom_saver = None
        self.map_selector = None
        self.on_layer_modified = None
        self._parent_widget: Optional[QWidget] = None

    def set_rom_saver(self, rom_saver):
        self._rom_saver = rom_saver
        print('[LayerSwap] ROMSaver wired')

    def set_map_paths(self, dat_path: Path, tex_path: Path):
        self._dat_path = Path(dat_path)
        self._tex_path = Path(tex_path)
        print(f'[LayerSwap] Map paths: {self._dat_path.name}, {self._tex_path.name}')

    def set_map_data(self, map_data):
        self._map_data = map_data

    def set_map_selector(self, map_selector):
        self.map_selector = map_selector

    def populate_layers(self, map_data, parent_frame):
        self._parent_widget = parent_frame
        self._clear_tree(parent_frame)
        self.root_nodes = []
        self.current_map_name = map_data.map_name
        self._map_data = map_data
        print(f'\n=== Populating Layer Tree for {map_data.map_name} ===')
        self._build_dat_tree(map_data)
        self._build_tex_tree(map_data)
        self._render_tree(parent_frame)
        print(f'Layer tree: {len(self.root_nodes)} root nodes')

    def _build_dat_tree(self, map_data):
        dat_root = LayerNode('DAT MAP', node_type='root', level=0)
        if map_data.has_mpif():
            mpif_data = map_data.dat_data.get('mpif')
            info = _read_mpif_info(mpif_data)
            size = len(mpif_data) if mpif_data else 0
            node = LayerNode('MPIF', data=mpif_data, node_type='section', parent=dat_root, level=1)
            node.info_text = f'{info}  •  {size} bytes'
            dat_root.add_child(node)
            print(f'  MPIF: {size} bytes  [{info}]')
        if map_data.has_txif():
            txif_data = map_data.dat_data.get('txif')
            info = _read_txif_info(txif_data)
            size = len(txif_data) if txif_data else 0
            node = LayerNode('TXIF', data=txif_data, node_type='section', parent=dat_root, level=1)
            node.info_text = f'{info}  •  {size} bytes'
            dat_root.add_child(node)
            print(f'  TXIF: {size} bytes  [{info}]')
        layers = map_data.dat_data.get('layers', [])
        if layers:
            lyr_root = LayerNode('LYR', node_type='section', parent=dat_root, level=1)
            lyr_root.info_text = f"{len(layers)} layer{('s' if len(layers) != 1 else '')}"
            for i, layer in enumerate(layers):
                raw_type = layer.get('type', -1)
                layer_data = layer.get('data', b'')
                label, desc = LAYER_TYPE_INFO.get(raw_type, (f'0x{raw_type:02X}', 'UNKNOWN'))
                display_name = f'{label} — {desc}'
                entry_info = _read_layer_entry_info(raw_type, layer_data)
                size = len(layer_data) if layer_data else 0
                info_parts = [p for p in (entry_info, f'{size:,} bytes') if p]
                child = LayerNode(display_name, data=layer_data, node_type='layer', parent=lyr_root, level=2)
                child.layer_index = i
                child.layer_type = raw_type
                child.info_text = '  •  '.join(info_parts)
                lyr_root.add_child(child)
            dat_root.add_child(lyr_root)
            print(f'  LYR: {len(layers)} layers')
        if map_data.has_cta():
            cta_data = map_data.dat_data.get('cta')
            size = len(cta_data) if cta_data else 0
            node = LayerNode('CTA', data=cta_data, node_type='section', parent=dat_root, level=1)
            node.info_text = f'tile animations  •  {size} bytes'
            dat_root.add_child(node)
            print(f'  CTA: {size} bytes')
        self.root_nodes.append(dat_root)

    def _build_tex_tree(self, map_data):
        tex_root = LayerNode('TEX MAP', node_type='root', level=0)
        if self.map_selector:
            tilesets = self.map_selector.get_tilesets()
        elif map_data.tex_data:
            tilesets = map_data.tex_data.get('tilesets', [])
        else:
            tilesets = []
        tex_root.info_text = f"{len(tilesets)} tileset{('s' if len(tilesets) != 1 else '')}"
        for i, tileset in enumerate(tilesets):
            rgcn_data = tileset.get('RGCN') or tileset.get('NCGR')
            rlcn_data = tileset.get('RLCN') or tileset.get('NCLR')
            ts_type = _detect_tileset_type(rgcn_data, rlcn_data)
            ts_node = LayerNode(f'TILESET {i}', node_type='tileset', parent=tex_root, level=1)
            ts_node.tileset_index = i
            ts_node.info_text = ts_type
            if rgcn_data:
                size = len(rgcn_data)
                rgcn_node = LayerNode('RGCN', data=rgcn_data, node_type='component', parent=ts_node, level=2)
                rgcn_node.tileset_index = i
                rgcn_node.component = 'RGCN'
                rgcn_node.info_text = f'graphics  •  {size:,} bytes'
                ts_node.add_child(rgcn_node)
            if rlcn_data:
                size = len(rlcn_data)
                rlcn_node = LayerNode('RLCN', data=rlcn_data, node_type='component', parent=ts_node, level=2)
                rlcn_node.tileset_index = i
                rlcn_node.component = 'RLCN'
                rlcn_node.info_text = f'palette  •  {size:,} bytes'
                ts_node.add_child(rlcn_node)
            tex_root.add_child(ts_node)
            print(f'  TILESET {i} [{ts_type}]: {len(ts_node.children)} components')
        self.root_nodes.append(tex_root)

    def _render_tree(self, parent_frame):
        for i, node in enumerate(self.root_nodes):
            if i > 0:
                sep = QFrame()
                sep.setFixedHeight(2)
                sep.setStyleSheet(f'background-color: {COLOR_ACCENT}; border: none;')
                parent_frame.add_widget(sep)
            self._render_node(node, parent_frame)

    def _render_node(self, node: LayerNode, parent_frame):
        if node.level == 0:
            left_pad, vpad = (10, 3)
            border = True
            radius = 5
        elif node.level == 1:
            left_pad, vpad = (30, 2)
            border = False
            radius = 3
        else:
            left_pad, vpad = (50, 2)
            border = False
            radius = 3
        node.frame = QFrame()
        outer_vbox = QVBoxLayout(node.frame)
        outer_vbox.setContentsMargins(0, vpad, 0, vpad)
        outer_vbox.setSpacing(0)
        border_css = f'border: 2px solid {COLOR_ACCENT};' if border else 'border: none;'
        node.frame.setStyleSheet(f'\n            QFrame {{\n                background-color: {node.get_bg_color()};\n                border-radius: {radius}px;\n                {border_css}\n            }}\n        ')
        inner_widget = QWidget()
        inner_widget.setStyleSheet('background: transparent; border: none;')
        inner_hbox = QHBoxLayout(inner_widget)
        inner_hbox.setContentsMargins(left_pad, 4 if node.level == 0 else 3, 10, 4 if node.level == 0 else 3)
        inner_hbox.setSpacing(6)
        spacer_size = 30 if node.level == 0 else 25
        if node.can_expand():
            node.expand_button = _make_expand_btn('+', node.level)
            node.expand_button.clicked.connect(lambda checked, n=node: self._toggle_expand(n))
            inner_hbox.addWidget(node.expand_button)
        else:
            spacer = QWidget()
            spacer.setFixedSize(spacer_size, spacer_size)
            spacer.setStyleSheet('background: transparent; border: none;')
            inner_hbox.addWidget(spacer)
        name_size = 12 if node.level == 0 else 10 if node.level == 1 else 10
        node.name_label = _make_label(node.name, COLOR_TEXT, bold=node.level <= 1, size=name_size)
        inner_hbox.addWidget(node.name_label)
        if node.info_text:
            node.info_label = _make_label(node.info_text, COLOR_INFO, size=8)
            node.info_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            inner_hbox.addWidget(node.info_label, stretch=1)
        else:
            inner_hbox.addStretch(1)
        node.export_button = _make_button('EXPORT')
        node.export_button.clicked.connect(lambda checked, n=node: self._export_layer(n))
        inner_hbox.addWidget(node.export_button)
        node.swap_button = _make_button('SWAP')
        node.swap_button.clicked.connect(lambda checked, n=node: self._swap_layer(n))
        inner_hbox.addWidget(node.swap_button)
        outer_vbox.addWidget(inner_widget)
        node.children_container = QWidget()
        node.children_container.setStyleSheet('background: transparent; border: none;')
        children_vbox = QVBoxLayout(node.children_container)
        children_vbox.setContentsMargins(0, 0, 0, 0)
        children_vbox.setSpacing(0)
        node.children_container.hide()
        outer_vbox.addWidget(node.children_container)
        parent_frame.add_widget(node.frame)

    def _toggle_expand(self, node: LayerNode):
        node.is_expanded = not node.is_expanded
        if node.is_expanded:
            node.expand_button.setText('−')
            layout = node.children_container.layout()
            if layout.count() == 0:
                _ChildProxy(layout)
                for child in node.children:
                    self._render_node_into_layout(child, layout)
            node.children_container.show()
            print(f'Expanded {node.name}: {len(node.children)} children')
        else:
            node.expand_button.setText('+')
            node.children_container.hide()
            print(f'Collapsed {node.name}')

    def _render_node_into_layout(self, node: LayerNode, layout: QVBoxLayout):
        if node.level == 0:
            left_pad, vpad, border, radius = (10, 3, True, 5)
        elif node.level == 1:
            left_pad, vpad, border, radius = (30, 2, False, 3)
        else:
            left_pad, vpad, border, radius = (50, 2, False, 3)
        node.frame = QFrame()
        outer_vbox = QVBoxLayout(node.frame)
        outer_vbox.setContentsMargins(0, vpad, 0, vpad)
        outer_vbox.setSpacing(0)
        border_css = f'border: 2px solid {COLOR_ACCENT};' if border else 'border: none;'
        node.frame.setStyleSheet(f'\n            QFrame {{\n                background-color: {node.get_bg_color()};\n                border-radius: {radius}px;\n                {border_css}\n            }}\n        ')
        inner_widget = QWidget()
        inner_widget.setStyleSheet('background: transparent; border: none;')
        inner_hbox = QHBoxLayout(inner_widget)
        inner_hbox.setContentsMargins(left_pad, 3, 10, 3)
        inner_hbox.setSpacing(6)
        spacer_size = 30 if node.level == 0 else 25
        if node.can_expand():
            node.expand_button = _make_expand_btn('+', node.level)
            node.expand_button.clicked.connect(lambda checked, n=node: self._toggle_expand(n))
            inner_hbox.addWidget(node.expand_button)
        else:
            sp = QWidget()
            sp.setFixedSize(spacer_size, spacer_size)
            sp.setStyleSheet('background: transparent; border: none;')
            inner_hbox.addWidget(sp)
        name_size = 12 if node.level == 0 else 10
        node.name_label = _make_label(node.name, COLOR_TEXT, bold=node.level <= 1, size=name_size)
        inner_hbox.addWidget(node.name_label)
        if node.info_text:
            node.info_label = _make_label(node.info_text, COLOR_INFO, size=8)
            node.info_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            inner_hbox.addWidget(node.info_label, stretch=1)
        else:
            inner_hbox.addStretch(1)
        node.export_button = _make_button('EXPORT')
        node.export_button.clicked.connect(lambda checked, n=node: self._export_layer(n))
        inner_hbox.addWidget(node.export_button)
        node.swap_button = _make_button('SWAP')
        node.swap_button.clicked.connect(lambda checked, n=node: self._swap_layer(n))
        inner_hbox.addWidget(node.swap_button)
        outer_vbox.addWidget(inner_widget)
        node.children_container = QWidget()
        node.children_container.setStyleSheet('background: transparent; border: none;')
        cc_layout = QVBoxLayout(node.children_container)
        cc_layout.setContentsMargins(0, 0, 0, 0)
        cc_layout.setSpacing(0)
        node.children_container.hide()
        outer_vbox.addWidget(node.children_container)
        layout.addWidget(node.frame)

    def _swap_layer(self, node: LayerNode):
        print(f'\n=== Swap: {node.get_path()} ===')
        parent = self._parent_widget
        if not self._rom_saver:
            QMessageBox.critical(parent, 'Not Ready', 'ROMSaver is not connected.\nLoad a ROM before swapping layers.')
            return
        if not self._map_data:
            QMessageBox.critical(parent, 'Not Ready', 'No map is loaded.\nSelect a map first.')
            return
        file_path, _ = QFileDialog.getOpenFileName(parent, f"Select Binary File to Replace '{node.name}'", '', 'Binary files (*.bin);;All files (*.*)')
        if not file_path:
            print('Swap cancelled')
            return
        try:
            new_data = Path(file_path).read_bytes()
        except Exception as e:
            QMessageBox.critical(parent, 'Read Error', f'Could not read file:\n{e}')
            return
        old_size = len(node.data) if node.data else 0
        print(f'  Replacement: {len(new_data):,} bytes  (was {old_size:,})')
        if node.node_type == 'layer' and node.layer_type is not None:
            ok, msg = self._validate_layer_magic(node.layer_type, new_data)
            if not ok:
                QMessageBox.critical(parent, 'Invalid Layer File', f'The selected file does not match layer type {node.name}.\n\n{msg}\n\nMake sure you are replacing with the correct layer type.')
                return
        if node.node_type == 'component':
            ok, msg = self._validate_component_magic(node.component, new_data)
            if not ok:
                QMessageBox.critical(parent, 'Invalid Component File', f'The file does not appear to be a valid {node.component}.\n\n{msg}')
                return
        root_name = self._get_root_name(node)
        success = False
        if root_name == 'DAT MAP':
            success = self._apply_dat_swap(node, new_data)
        elif root_name == 'TEX MAP':
            success = self._apply_tex_swap(node, new_data)
        else:
            QMessageBox.critical(parent, 'Swap Error', f"Cannot determine file type for node '{node.get_path()}'")
            return
        if not success:
            return
        node.data = new_data
        self.modified_layers[node.get_path()] = new_data
        if node.name_label:
            node.name_label.setText(f'{node.name} [MODIFIED]')
            node.name_label.setStyleSheet(f'color: {COLOR_MODIFIED}; background: transparent; border: none;')
        if node.info_label:
            new_size_str = f'{len(new_data):,} bytes'
            base = node.info_text.split('•')[0].strip() if '•' in node.info_text else ''
            node.info_label.setText(f'{base}  •  {new_size_str}' if base else new_size_str)
            node.info_label.setStyleSheet(f'color: {COLOR_MODIFIED}; background: transparent; border: none;')
        if self.on_layer_modified:
            self.on_layer_modified(node.get_path(), new_data)
        QMessageBox.information(parent, 'Swap Successful', f"'{node.name}' swapped and queued for ROM save.\n\nOld: {old_size:,} bytes\nNew: {len(new_data):,} bytes")
        print(f'  Swap complete: {node.get_path()}')

    def _validate_layer_magic(self, layer_type: int, data: bytes) -> Tuple[bool, str]:
        if len(data) < 4:
            return (False, 'File is too small (< 4 bytes) to be a valid layer.')
        found_type = struct.unpack_from('<I', data, 0)[0]
        if found_type != layer_type:
            label, desc = LAYER_TYPE_INFO.get(layer_type, (f'0x{layer_type:02X}', 'UNKNOWN'))
            fl, fd = LAYER_TYPE_INFO.get(found_type, (f'0x{found_type:02X}', 'UNKNOWN'))
            return (False, f"Expected layer type {label} ({desc})\nFound type {fl} ({fd})\n(first 4 bytes: {data[:4].hex(' ')})")
        return (True, 'OK')

    def _validate_component_magic(self, component: str, data: bytes) -> Tuple[bool, str]:
        if len(data) < 4:
            return (False, 'File is too small (< 4 bytes).')
        expected = {'RGCN': b'RGCN', 'RLCN': b'RLCN'}.get(component)
        if not expected:
            return (True, 'OK')
        if data[:4] != expected:
            found = data[:4]
            return (False, f"Expected magic '{expected.decode('ascii')}' (hex: {expected.hex(' ')})\nFound: {found.hex(' ')} ('{found.decode('ascii', errors='replace')}')")
        return (True, 'OK')

    def _apply_dat_swap(self, node: LayerNode, new_data: bytes) -> bool:
        parent = self._parent_widget
        if not self._dat_path:
            QMessageBox.critical(parent, 'Swap Error', 'DAT file path not set.\nCall set_map_paths() before swapping.')
            return False
        dat_data = self._map_data.dat_data
        node_name = node.name.upper()
        if node_name == 'MPIF':
            dat_data['mpif'] = new_data
        elif node_name == 'TXIF':
            dat_data['txif'] = new_data
        elif node_name == 'CTA':
            dat_data['cta'] = new_data
        elif node.layer_index is not None:
            layers = dat_data.get('layers', [])
            if node.layer_index >= len(layers):
                QMessageBox.critical(parent, 'Swap Error', f'Layer index {node.layer_index} out of range ({len(layers)} layers).')
                return False
            layers[node.layer_index]['data'] = new_data
            print(f'  Updated layer[{node.layer_index}] in MapData')
        else:
            QMessageBox.critical(parent, 'Swap Error', f"Unknown DAT node type for '{node.name}'.\nNode type: {node.node_type}")
            return False
        rebuilt = self._rebuild_dat(dat_data)
        if rebuilt is None:
            QMessageBox.critical(parent, 'Rebuild Error', 'Failed to rebuild DAT file.\nCheck console for details.')
            return False
        try:
            self._dat_path.write_bytes(rebuilt)
            print(f'  DAT written: {self._dat_path.name}  ({len(rebuilt):,} bytes)')
        except Exception as e:
            QMessageBox.critical(parent, 'Write Error', f'Could not write DAT to disk:\n{e}')
            return False
        ok = self._rom_saver.register_modification(self._dat_path, rebuilt, 'layer_swap')
        if not ok:
            QMessageBox.warning(parent, 'Registration Warning', 'File written but ROMSaver registration failed.\nThe change may not appear in the saved ROM.')
            return False
        print(f'  Registered with ROMSaver: {self._dat_path.name}')
        return True

    def _rebuild_dat(self, dat_data: dict) -> Optional[bytes]:
        try:
            from load.narcutil import build_narc
            from load.lz10util import compress_lz10
            layers = dat_data.get('layers', [])
            layer_blobs = [l['data'] for l in layers if l.get('data')]
            lyr_blob = None
            if layer_blobs:
                inner_narc = build_narc(layer_blobs)
                outer_narc = build_narc([inner_narc])
                lyr_blob = b'LYR\x00' + outer_narc
            outer_sections = []
            mpif = dat_data.get('mpif')
            txif = dat_data.get('txif')
            cta = dat_data.get('cta')
            if mpif:
                outer_sections.append(mpif)
            if txif:
                outer_sections.append(txif)
            if lyr_blob:
                outer_sections.append(lyr_blob)
            if cta:
                outer_sections.append(cta)
            if not outer_sections:
                print('[LayerSwap] ERROR: no sections to rebuild DAT')
                return None
            outer_narc_final = build_narc(outer_sections)
            compressed = compress_lz10(outer_narc_final)
            print(f'  [rebuild_dat] sections={len(outer_sections)} layers={len(layer_blobs)} uncompressed={len(outer_narc_final):,} compressed={len(compressed):,}')
            return compressed
        except Exception as e:
            traceback.print_exc()
            print(f'[LayerSwap] ERROR rebuilding DAT: {e}')
            return None

    def _apply_tex_swap(self, node: LayerNode, new_data: bytes) -> bool:
        parent = self._parent_widget
        if not self._tex_path:
            QMessageBox.critical(parent, 'Swap Error', 'TEX file path not set.\nCall set_map_paths() before swapping.')
            return False
        if node.tileset_index is None or node.component is None:
            QMessageBox.critical(parent, 'Swap Error', f"Node '{node.name}' is missing tileset_index or component tag.")
            return False
        tex_data = self._map_data.tex_data
        tilesets = tex_data.get('tilesets', [])
        if node.tileset_index >= len(tilesets):
            QMessageBox.critical(parent, 'Swap Error', f'Tileset index {node.tileset_index} out of range ({len(tilesets)} tilesets).')
            return False
        tileset = tilesets[node.tileset_index]
        if node.component == 'RGCN':
            tileset['RGCN'] = new_data
            tileset['NCGR'] = new_data
        elif node.component == 'RLCN':
            tileset['RLCN'] = new_data
            tileset['NCLR'] = new_data
        else:
            QMessageBox.critical(parent, 'Swap Error', f"Unknown component '{node.component}'.")
            return False
        rebuilt = self._rebuild_tex(tex_data)
        if rebuilt is None:
            QMessageBox.critical(parent, 'Rebuild Error', 'Failed to rebuild TEX file.\nCheck console for details.')
            return False
        try:
            self._tex_path.write_bytes(rebuilt)
            print(f'  TEX written: {self._tex_path.name}  ({len(rebuilt):,} bytes)')
        except Exception as e:
            QMessageBox.critical(parent, 'Write Error', f'Could not write TEX to disk:\n{e}')
            return False
        ok = self._rom_saver.register_modification(self._tex_path, rebuilt, 'layer_swap')
        if not ok:
            QMessageBox.warning(parent, 'Registration Warning', 'File written but ROMSaver registration failed.\nThe change may not appear in the saved ROM.')
            return False
        print(f'  Registered with ROMSaver: {self._tex_path.name}')
        return True

    def _rebuild_tex(self, tex_data: dict) -> Optional[bytes]:
        try:
            from load.narcutil import build_narc
            from load.lz10util import compress_lz10
            tilesets = tex_data.get('tilesets', [])
            outer_blobs = []
            for i, ts in enumerate(tilesets):
                rgcn = ts.get('RGCN') or ts.get('NCGR')
                rlcn = ts.get('RLCN') or ts.get('NCLR')
                components = [c for c in (rgcn, rlcn) if c]
                if not components:
                    print(f'  [rebuild_tex] WARNING: tileset {i} empty, skipping')
                    continue
                inner_narc = build_narc(components)
                outer_blobs.append(inner_narc)
            if not outer_blobs:
                print('[LayerSwap] ERROR: no tilesets to rebuild TEX')
                return None
            outer_narc = build_narc(outer_blobs)
            tex_body = b'TEX\x00' + outer_narc
            compressed = compress_lz10(tex_body)
            print(f'  [rebuild_tex] tilesets={len(outer_blobs)} uncompressed={len(outer_narc):,} compressed={len(compressed):,}')
            return compressed
        except Exception as e:
            traceback.print_exc()
            print(f'[LayerSwap] ERROR rebuilding TEX: {e}')
            return None

    def _export_layer(self, node: LayerNode):
        print(f'\n=== Export: {node.get_path()} ===')
        parent = self._parent_widget
        if not node.data:
            QMessageBox.warning(parent, 'No Data', f"'{node.name}' has no data to export.")
            return
        safe_name = node.name.replace(' ', '_').replace('/', '_').replace('>', '').replace('—', '-').replace('0x', '').strip('_')
        default_file = f'{self.current_map_name}_{safe_name}.bin'
        file_path, _ = QFileDialog.getSaveFileName(parent, f'Export {node.name}', default_file, 'Binary files (*.bin);;All files (*.*)')
        if not file_path:
            print('Export cancelled')
            return
        try:
            Path(file_path).write_bytes(node.data)
            print(f'  Exported {len(node.data):,} bytes → {file_path}')
            QMessageBox.information(parent, 'Export Successful', f"'{node.name}' exported.\n\nFile: {Path(file_path).name}\nSize: {len(node.data):,} bytes")
        except Exception as e:
            print(f'  Export error: {e}')
            QMessageBox.critical(parent, 'Export Failed', f"Could not export '{node.name}':\n{e}")

    def _get_root_name(self, node: LayerNode) -> Optional[str]:
        cur = node
        while cur.parent:
            cur = cur.parent
        return cur.name

    def _clear_tree(self, parent_frame):
        parent_frame.clear_items()
        self.root_nodes = []
        self.modified_layers = {}

    def has_modifications(self) -> bool:
        return len(self.modified_layers) > 0

    def get_modified_layers(self) -> Dict[str, bytes]:
        return self.modified_layers.copy()

    def get_modification_count(self) -> int:
        return len(self.modified_layers)

    def clear_modifications(self):
        self.modified_layers = {}
        print('[LayerSwap] Modifications cleared')

    def get_layer_data(self, node_path: str) -> Optional[bytes]:
        for root in self.root_nodes:
            result = self._find_node_by_path(root, node_path)
            if result is not None:
                return result
        return None

    def _find_node_by_path(self, node: LayerNode, target: str) -> Optional[bytes]:
        if node.get_path() == target:
            return node.data
        for child in node.children:
            r = self._find_node_by_path(child, target)
            if r is not None:
                return r
        return None

    def clear(self):
        self.root_nodes = []
        self.current_map_name = None
        self.modified_layers = {}
        self._map_data = None
        self._dat_path = None
        self._tex_path = None
        print('[LayerSwap] Cleared')

class _ChildProxy:

    def __init__(self, layout: QVBoxLayout):
        self._layout = layout

    def add_widget(self, widget: QWidget):
        self._layout.addWidget(widget)
