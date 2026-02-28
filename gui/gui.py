import sys
import os
import io
import traceback
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QFrame, QLabel, QPushButton, QScrollArea, QVBoxLayout, QHBoxLayout, QSizePolicy, QMessageBox, QFileDialog, QDialog, QStatusBar
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QFont, QColor
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gui.romselector import ROMSelector
from gui.mapselector import MapSelector
from gui.tilesetrender import TilesetRenderer
from gui.layerswap import LayerSwap
from load.importtileset import import_tileset_auto_detect, get_file_info
from load.pngtilesettransfer import transfer_png_to_map, get_png_info
from load.saverom import ROMSaver
COLOR_BG_MAIN = '#182d55'
COLOR_ELEMENT_BG = '#26395e'
COLOR_ACCENT = '#6d86a8'
COLOR_HOVER = '#354a75'
COLOR_TEXT = '#FFFFFF'
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
SCALE_STEPS = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0]
GLOBAL_STYLE = f'\n    QMainWindow, QWidget {{\n        background-color: {COLOR_BG_MAIN};\n        color: {COLOR_TEXT};\n        font-family: Arial;\n    }}\n\n    QPushButton.primary {{\n        background-color: {COLOR_ELEMENT_BG};\n        color: {COLOR_TEXT};\n        border: 2px solid {COLOR_ACCENT};\n        border-radius: 10px;\n        font-size: 12px;\n        font-weight: bold;\n        min-height: 40px;\n        padding: 4px 12px;\n    }}\n    QPushButton.primary:hover {{\n        background-color: {COLOR_HOVER};\n    }}\n    QPushButton.primary:disabled {{\n        color: #5a6070;\n        border-color: #3a4560;\n        background-color: {COLOR_ELEMENT_BG};\n    }}\n\n    QPushButton.small {{\n        background-color: {COLOR_ELEMENT_BG};\n        color: {COLOR_TEXT};\n        border: 1px solid {COLOR_ACCENT};\n        border-radius: 5px;\n        font-size: 10px;\n        min-height: 30px;\n        padding: 2px 8px;\n        text-align: left;\n    }}\n    QPushButton.small:hover {{\n        background-color: {COLOR_HOVER};\n    }}\n    QPushButton.small:disabled {{\n        color: #5a6070;\n        border-color: #3a4560;\n    }}\n\n    QPushButton.scale {{\n        background-color: {COLOR_ELEMENT_BG};\n        color: {COLOR_TEXT};\n        border: 1px solid {COLOR_ACCENT};\n        border-radius: 6px;\n        font-size: 13px;\n        font-weight: bold;\n        min-width: 44px;\n        max-width: 44px;\n        min-height: 28px;\n        max-height: 28px;\n    }}\n    QPushButton.scale:hover {{\n        background-color: {COLOR_HOVER};\n    }}\n\n    QFrame.panel {{\n        background-color: {COLOR_ELEMENT_BG};\n        border: 2px solid {COLOR_ACCENT};\n        border-radius: 10px;\n    }}\n\n    QScrollArea {{\n        background-color: {COLOR_ELEMENT_BG};\n        border: 1px solid {COLOR_ACCENT};\n        border-radius: 5px;\n    }}\n    QScrollArea > QWidget > QWidget {{\n        background-color: {COLOR_ELEMENT_BG};\n    }}\n    QScrollBar:vertical {{\n        background: {COLOR_BG_MAIN};\n        width: 10px;\n        border-radius: 5px;\n    }}\n    QScrollBar::handle:vertical {{\n        background: {COLOR_ACCENT};\n        border-radius: 5px;\n        min-height: 20px;\n    }}\n    QScrollBar::handle:vertical:hover {{\n        background: {COLOR_HOVER};\n    }}\n    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{\n        height: 0px;\n    }}\n\n    QStatusBar {{\n        background-color: {COLOR_ELEMENT_BG};\n        color: {COLOR_TEXT};\n        font-size: 11px;\n        padding: 0px 20px;\n        min-height: 30px;\n    }}\n\n    QLabel {{\n        background-color: transparent;\n        color: {COLOR_TEXT};\n        font-size: 11px;\n    }}\n\n    QDialog {{\n        background-color: {COLOR_BG_MAIN};\n    }}\n    QMessageBox {{\n        background-color: {COLOR_BG_MAIN};\n        color: {COLOR_TEXT};\n    }}\n    QMessageBox QLabel {{\n        color: {COLOR_TEXT};\n    }}\n    QMessageBox QPushButton {{\n        background-color: {COLOR_ELEMENT_BG};\n        color: {COLOR_TEXT};\n        border: 1px solid {COLOR_ACCENT};\n        border-radius: 6px;\n        min-width: 80px;\n        min-height: 28px;\n        padding: 4px 12px;\n        font-size: 11px;\n    }}\n    QMessageBox QPushButton:hover {{\n        background-color: {COLOR_HOVER};\n    }}\n'

def _primary_btn(text: str, parent: QWidget=None) -> QPushButton:
    btn = QPushButton(text, parent)
    btn.setProperty('class', 'primary')
    btn.setFont(QFont('Arial', 12, QFont.Weight.Bold))
    btn.setMinimumHeight(40)
    return btn

def _small_btn(text: str, parent: QWidget=None) -> QPushButton:
    btn = QPushButton(text, parent)
    btn.setProperty('class', 'small')
    btn.setFont(QFont('Arial', 10))
    btn.setMinimumHeight(30)
    return btn

def _scale_btn(text: str, parent: QWidget=None) -> QPushButton:
    btn = QPushButton(text, parent)
    btn.setProperty('class', 'scale')
    btn.setFont(QFont('Arial', 13, QFont.Weight.Bold))
    btn.setFixedSize(44, 28)
    return btn

def _panel_frame(parent: QWidget=None) -> QFrame:
    frame = QFrame(parent)
    frame.setObjectName('panel')
    frame.setProperty('class', 'panel')
    return frame

def _pil_to_qpixmap(image: Image.Image) -> QPixmap:
    buf = io.BytesIO()
    image.save(buf, format='PNG')
    buf.seek(0)
    pm = QPixmap()
    pm.loadFromData(buf.read())
    return pm

class ScrollContainer(QScrollArea):

    def __init__(self, parent: QWidget=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._inner = QWidget()
        self._inner.setStyleSheet(f'background-color: {COLOR_ELEMENT_BG};')
        self._layout = QVBoxLayout(self._inner)
        self._layout.setContentsMargins(5, 5, 5, 5)
        self._layout.setSpacing(2)
        self._layout.addStretch()
        self.setWidget(self._inner)

    def inner_widget(self) -> QWidget:
        return self._inner

    def inner_layout(self) -> QVBoxLayout:
        return self._layout

    def add_widget(self, widget: QWidget):
        self._layout.insertWidget(self._layout.count() - 1, widget)

    def clear_items(self):
        while self._layout.count() > 1:
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def winfo_children(self):
        children = []
        for i in range(self._layout.count()):
            item = self._layout.itemAt(i)
            if item and item.widget():
                children.append(item.widget())
        return children

class TilesetCanvas(QLabel):

    def __init__(self, parent: QWidget=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(f'background-color: {COLOR_ELEMENT_BG}; border: none;')
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(200, 100)
        self._current_pixmap: QPixmap | None = None

    def display_image(self, pixmap: QPixmap):
        self._current_pixmap = pixmap
        self.setPixmap(pixmap)
        self.resize(pixmap.width(), pixmap.height())

    def clear_image(self):
        self._current_pixmap = None
        self.clear()

class ProgressDialog(QDialog):

    def __init__(self, parent: QWidget, title: str, message: str):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(400, 160)
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        self._msg_label = QLabel(message)
        self._msg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._msg_label.setFont(QFont('Arial', 12))
        self._msg_label.setWordWrap(True)
        self._msg_label.setStyleSheet(f'color: {COLOR_TEXT};')
        layout.addWidget(self._msg_label)
        self._status_label = QLabel('Initializing...')
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setFont(QFont('Arial', 10))
        self._status_label.setStyleSheet(f'color: {COLOR_ACCENT};')
        layout.addWidget(self._status_label)
        if parent:
            pg = parent.geometry()
            self.move(pg.x() + (pg.width() - self.width()) // 2, pg.y() + (pg.height() - self.height()) // 2)

    def set_status(self, text: str):
        self._status_label.setText(text)
        QApplication.processEvents()

class RomToolGUI(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle('Pokemon Ranger: Shadows of Almia - ROM Manager')
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setStyleSheet(GLOBAL_STYLE)
        self.rom_selector = ROMSelector()
        self.map_selector = MapSelector()
        self.tileset_renderer = TilesetRenderer()
        self.layer_swap = LayerSwap()
        self.rom_saver = ROMSaver()
        self.layer_swap.set_map_selector(self.map_selector)
        self.layer_swap.set_rom_saver(self.rom_saver)
        self._tileset_scale = 1.0
        self._current_pil_image: Image.Image | None = None
        self.map_selector.on_maps_loaded = self._handle_maps_loaded
        self.map_selector.on_map_selected = self._handle_map_selected
        self.map_selector.on_map_data_loaded = self._handle_map_data_loaded
        self.tileset_renderer.on_tileset_rendered = self._handle_tileset_rendered
        self._build_ui()
        self._reset_ui_state()

    def _build_ui(self):
        PAD = 20
        PAD_IN = 10
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(PAD, PAD, PAD, PAD)
        main_layout.setSpacing(PAD_IN)
        self._build_left_sidebar(main_layout)
        self._build_middle_section(main_layout)
        self._build_right_sidebar(main_layout)
        self._status_lbl = QLabel('Ready')
        self._status_lbl.setFont(QFont('Arial', 11))
        self.statusBar().addWidget(self._status_lbl, 1)

    def _build_left_sidebar(self, parent_layout: QHBoxLayout):
        left = QWidget()
        left.setFixedWidth(220)
        vbox = QVBoxLayout(left)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(10)
        self.btn_rom = _primary_btn('ROM SELECTOR')
        self.btn_rom.clicked.connect(self._on_rom_selector_clicked)
        vbox.addWidget(self.btn_rom)
        self.btn_map = _primary_btn('MAP SELECT')
        self.btn_map.setEnabled(False)
        vbox.addWidget(self.btn_map)
        map_panel = _panel_frame()
        map_panel_vbox = QVBoxLayout(map_panel)
        map_panel_vbox.setContentsMargins(5, 5, 5, 5)
        self.map_list_scroll = ScrollContainer()
        map_panel_vbox.addWidget(self.map_list_scroll)
        vbox.addWidget(map_panel, stretch=3)
        self.btn_tileset = _primary_btn('TILESET SELECTOR')
        self.btn_tileset.setEnabled(False)
        vbox.addWidget(self.btn_tileset)
        ts_panel = _panel_frame()
        ts_panel_vbox = QVBoxLayout(ts_panel)
        ts_panel_vbox.setContentsMargins(5, 5, 5, 5)
        self.tileset_list_scroll = ScrollContainer()
        ts_panel_vbox.addWidget(self.tileset_list_scroll)
        vbox.addWidget(ts_panel, stretch=2)
        self.map_buttons: list[QPushButton] = []
        self.tileset_buttons: list[QPushButton] = []
        parent_layout.addWidget(left)

    def _build_middle_section(self, parent_layout: QHBoxLayout):
        mid = QWidget()
        vbox = QVBoxLayout(mid)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(10)
        rgcn_panel = _panel_frame()
        rgcn_vbox = QVBoxLayout(rgcn_panel)
        rgcn_vbox.setContentsMargins(8, 8, 8, 8)
        rgcn_vbox.setSpacing(4)
        scale_strip = QWidget()
        scale_strip.setFixedHeight(38)
        scale_strip.setStyleSheet(f'\n            QWidget {{\n                background-color: {COLOR_BG_MAIN};\n                border-radius: 6px;\n            }}\n        ')
        scale_hbox = QHBoxLayout(scale_strip)
        scale_hbox.setContentsMargins(6, 4, 6, 4)
        scale_hbox.setSpacing(4)
        self.btn_scale_down = _scale_btn('  —  ')
        self.btn_scale_down.clicked.connect(self._on_scale_decrease)
        scale_hbox.addWidget(self.btn_scale_down)
        self.lbl_scale = QLabel('SCALE  1.0x')
        self.lbl_scale.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_scale.setFont(QFont('Arial', 11, QFont.Weight.Bold))
        scale_hbox.addWidget(self.lbl_scale, stretch=1)
        self.btn_scale_up = _scale_btn('  +  ')
        self.btn_scale_up.clicked.connect(self._on_scale_increase)
        scale_hbox.addWidget(self.btn_scale_up)
        rgcn_vbox.addWidget(scale_strip)
        self.canvas_scroll = QScrollArea()
        self.canvas_scroll.setWidgetResizable(True)
        self.canvas_scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.canvas_scroll.setStyleSheet(f'\n            QScrollArea {{\n                background-color: {COLOR_ELEMENT_BG};\n                border: none;\n            }}\n            QScrollArea > QWidget > QWidget {{\n                background-color: {COLOR_ELEMENT_BG};\n            }}\n        ')
        self.canvas_rgcn = TilesetCanvas()
        self.canvas_scroll.setWidget(self.canvas_rgcn)
        self.label_rgcn_placeholder = QLabel('Select a tileset to render')
        self.label_rgcn_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_rgcn_placeholder.setFont(QFont('Arial', 11))
        self.label_rgcn_placeholder.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        rgcn_vbox.addWidget(self.label_rgcn_placeholder, stretch=1)
        rgcn_vbox.addWidget(self.canvas_scroll, stretch=1)
        self.canvas_scroll.hide()
        vbox.addWidget(rgcn_panel, stretch=1)
        layer_panel = _panel_frame()
        layer_vbox = QVBoxLayout(layer_panel)
        layer_vbox.setContentsMargins(5, 5, 5, 5)
        self.layer_scroll = ScrollContainer()
        layer_vbox.addWidget(self.layer_scroll)
        vbox.addWidget(layer_panel, stretch=1)
        parent_layout.addWidget(mid, stretch=1)

    def _build_right_sidebar(self, parent_layout: QHBoxLayout):
        right = QWidget()
        right.setFixedWidth(220)
        vbox = QVBoxLayout(right)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(10)
        actions = [('SAVE ROM', self._on_save_rom), ('PNG EXPORT', self._on_png_export), ('IMPORT TILESET', self._on_import_tileset), ('PNG TILESET TRANSFER', self._on_png_transfer), ('EXPORT MAP FILES', self._on_export_map_files), ('EXPORT TILESET', self._on_export_tileset)]
        self.action_buttons: dict[str, QPushButton] = {}
        for text, handler in actions:
            btn = _primary_btn(text)
            btn.setEnabled(False)
            btn.clicked.connect(handler)
            vbox.addWidget(btn)
            self.action_buttons[text.lower().replace(' ', '_')] = btn
        vbox.addStretch()
        parent_layout.addWidget(right)

    def _set_status(self, message: str):
        self._status_lbl.setText(message)
        QApplication.processEvents()
        print(f'Status: {message}')

    def _on_scale_increase(self):
        current = self._tileset_scale
        for step in SCALE_STEPS:
            if step > current + 0.01:
                self._tileset_scale = step
                break
        else:
            self._tileset_scale = SCALE_STEPS[-1]
        self._update_scale_label()
        self._redisplay_tileset()

    def _on_scale_decrease(self):
        current = self._tileset_scale
        for step in reversed(SCALE_STEPS):
            if step < current - 0.01:
                self._tileset_scale = step
                break
        else:
            self._tileset_scale = SCALE_STEPS[0]
        self._update_scale_label()
        self._redisplay_tileset()

    def _update_scale_label(self):
        scale = self._tileset_scale
        text = f'SCALE  {int(scale)}x' if scale == int(scale) else f'SCALE  {scale}x'
        self.lbl_scale.setText(text)

    def _redisplay_tileset(self):
        image = self.tileset_renderer.get_rendered_image()
        if image is not None:
            self._display_image_on_canvas(image)

    def _reset_ui_state(self):
        self.btn_map.setEnabled(False)
        self.btn_tileset.setEnabled(False)
        for btn in self.action_buttons.values():
            btn.setEnabled(False)
        self._clear_map_list()
        self._clear_tileset_list()
        self._clear_canvas()
        self._clear_layer_info()
        self._set_status('Ready')

    def _on_rom_selector_clicked(self):
        self._set_status('Opening ROM selector...')
        if not self.rom_selector.browse_rom():
            self._set_status('Ready')
            return
        self._set_status('Extracting ROM...')
        if self.rom_selector.extract_rom(callback=self._set_status):
            dat_files, tex_files = self.rom_selector.get_map_files()
            self.map_selector.pair_map_files(dat_files, tex_files)
            rom_path = Path(self.rom_selector.rom_path)
            if self.rom_saver.initialize(rom_path):
                print('ROM Saver initialized successfully')
            else:
                print('Warning: ROM Saver initialization failed')
            self.btn_map.setEnabled(True)
            map_count = len(self.map_selector.get_map_pairs())
            self._set_status(f'ROM loaded! Found {map_count} maps')
            QMessageBox.information(self, 'Success', f'ROM loaded successfully!\n\nFound {map_count} map pairs')
        else:
            self._set_status('ROM extraction failed')
            QMessageBox.critical(self, 'Error', 'Failed to extract ROM')

    def _handle_maps_loaded(self, map_pairs):
        self._set_status(f'Loading {len(map_pairs)} maps...')
        self._clear_map_list()
        for i, map_pair in enumerate(map_pairs):
            if map_pair.is_complete():
                text = f'[OK] {map_pair.name}'
                enabled = True
            else:
                text = f'[!]  {map_pair.name}'
                enabled = False
            btn = _small_btn(text)
            btn.setEnabled(enabled)
            btn.clicked.connect(lambda checked, idx=i: self._on_map_clicked(idx))
            self.map_list_scroll.add_widget(btn)
            self.map_buttons.append(btn)
        self._set_status(f'Loaded {len(map_pairs)} maps')

    def _on_map_clicked(self, index: int):
        map_pair = self.map_selector.select_map_by_index(index)
        if map_pair:
            self._set_status(f'Selected: {map_pair.name}')

    def _handle_map_selected(self, map_pair):
        self._set_status(f'Loading map: {map_pair.name}...')
        self.layer_scroll.clear_items()
        loading = QLabel(f'Loading map data...\n\n{map_pair.name}\n\nBuilding layer tree...')
        loading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading.setFont(QFont('Arial', 11))
        self.layer_scroll.add_widget(loading)

    def _handle_map_data_loaded(self, map_data):
        self._set_status(f'Map data loaded: {map_data.map_name}')
        tilesets = self.map_selector.get_all_tilesets_for_rendering()
        print(f'\n=== Loading {len(tilesets)} tilesets into renderer ===')
        self.tileset_renderer.load_tilesets(tilesets)
        self._populate_tileset_list(tilesets)
        selected_map = self.map_selector.get_selected_map()
        if selected_map and selected_map.dat_path and selected_map.tex_path:
            self.layer_swap.set_map_paths(selected_map.dat_path, selected_map.tex_path)
        self.layer_swap.populate_layers(map_data, self.layer_scroll)
        self.btn_tileset.setEnabled(True)
        self.action_buttons['save_rom'].setEnabled(True)
        self.action_buttons['import_tileset'].setEnabled(True)
        self.action_buttons['export_map_files'].setEnabled(True)
        self._set_status(f'Ready - {map_data.map_name} ({len(tilesets)} tilesets)')

    def _clear_map_list(self):
        for btn in self.map_buttons:
            btn.deleteLater()
        self.map_buttons.clear()
        self.map_list_scroll.clear_items()

    def _populate_tileset_list(self, tilesets):
        self._clear_tileset_list()
        print(f'Creating {len(tilesets)} tileset buttons...')
        for i, tileset in enumerate(tilesets):
            has_gfx = tileset.get('has_graphics', False)
            has_pal = tileset.get('has_palette', False)
            if has_gfx and has_pal:
                icon = '[OK]'
                enabled = True
            elif has_gfx or has_pal:
                icon = '[~] '
                enabled = True
            else:
                icon = '[X] '
                enabled = False
            text = f'{icon} Tileset {i}'
            if 'error' in tileset:
                text += ' [ERR]'
            elif 'warning' in tileset:
                text += ' [WARN]'
            btn = _small_btn(text)
            btn.setEnabled(enabled)
            btn.clicked.connect(lambda checked, idx=i: self._on_tileset_clicked(idx))
            self.tileset_list_scroll.add_widget(btn)
            self.tileset_buttons.append(btn)
        print(f'Created {len(self.tileset_buttons)} tileset buttons')

    def _on_tileset_clicked(self, index: int):
        print(f'\n=== Tileset {index} clicked ===')
        self._set_status(f'Rendering tileset {index}...')
        if self.tileset_renderer.select_tileset(index):
            self.action_buttons['png_export'].setEnabled(True)
            self.action_buttons['import_tileset'].setEnabled(True)
            self.action_buttons['png_tileset_transfer'].setEnabled(True)
            self.action_buttons['export_tileset'].setEnabled(True)
            self._set_status(f'Tileset {index} rendered')
        else:
            self._set_status(f'Failed to render tileset {index}')
            QMessageBox.critical(self, 'Render Error', f'Failed to render tileset {index}')

    def _handle_tileset_rendered(self, image: Image.Image):
        print(f'Displaying tileset: {image.size}')
        self.label_rgcn_placeholder.hide()
        self.canvas_scroll.show()
        self._display_image_on_canvas(image)

    def _display_image_on_canvas(self, image: Image.Image):
        self._current_pil_image = image
        canvas_w = self.canvas_scroll.width()
        canvas_h = self.canvas_scroll.height()
        if canvas_w <= 1:
            canvas_w = 700
        if canvas_h <= 1:
            canvas_h = 350
        img_w, img_h = image.size
        target_w = int(img_w * self._tileset_scale)
        target_h = int(img_h * self._tileset_scale)
        max_w = int(canvas_w * 0.95)
        max_h = int(canvas_h * 0.95)
        if target_w > max_w or target_h > max_h:
            fit_scale = min(max_w / max(target_w, 1), max_h / max(target_h, 1))
            target_w = max(1, int(target_w * fit_scale))
            target_h = max(1, int(target_h * fit_scale))
        scaled_img = image.resize((target_w, target_h), Image.NEAREST)
        pixmap = _pil_to_qpixmap(scaled_img)
        self.canvas_rgcn.display_image(pixmap)
        print(f'Image displayed: {target_w}x{target_h} (scale {self._tileset_scale}x)')

    def _clear_tileset_list(self):
        for btn in self.tileset_buttons:
            btn.deleteLater()
        self.tileset_buttons.clear()
        self.tileset_list_scroll.clear_items()

    def _clear_canvas(self):
        self.canvas_rgcn.clear_image()
        self.canvas_scroll.hide()
        self.label_rgcn_placeholder.show()
        self._current_pil_image = None

    def _clear_layer_info(self):
        self.layer_swap.clear()
        self.layer_scroll.clear_items()
        placeholder = QLabel('Select a map to view layer tree')
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setFont(QFont('Arial', 11))
        self.layer_scroll.add_widget(placeholder)

    def _on_save_rom(self):
        if not self.rom_selector.rom_path:
            QMessageBox.warning(self, 'No ROM Loaded', 'Please load a ROM before saving')
            return
        if not self.rom_saver.cache.has_modifications():
            QMessageBox.information(self, 'No Changes', 'No modifications have been made to the ROM.\n\nMake some changes (import tilesets, swap layers, etc.) before saving.')
            return
        summary = self.rom_saver.get_modification_summary()
        summary_msg = f"Save ROM with modifications?\n\nTotal modifications: {summary['total_count']}\nTotal modified data: {summary['total_size']:,} bytes\n\nModification types:\n"
        for mod_type, count in summary['by_type'].items():
            summary_msg += f'  - {mod_type}: {count}\n'
        summary_msg += '\n\nWhere would you like to save the modified ROM?'
        if QMessageBox.question(self, 'Confirm Save', summary_msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            self._set_status('Save cancelled')
            return
        default_name = Path(self.rom_selector.rom_path).stem + '_modified.nds'
        save_path, _ = QFileDialog.getSaveFileName(self, 'Save Modified ROM', default_name, 'NDS ROM files (*.nds);;All files (*.*)')
        if not save_path:
            self._set_status('Save cancelled')
            return
        dlg = ProgressDialog(self, 'Saving ROM...', 'Saving ROM...\n\nThis may take a moment.')
        dlg.show()
        QApplication.processEvents()
        self._set_status('Saving ROM...')
        try:
            success, message = self.rom_saver.save_rom(Path(save_path), progress_callback=dlg.set_status)
            dlg.close()
            if success:
                self._set_status(f'ROM saved successfully to {Path(save_path).name}')
                QMessageBox.information(self, 'Save Complete', f"ROM Saved Successfully!\n\nLocation: {save_path}\n\nModifications applied: {summary['total_count']}\nFile size: {Path(save_path).stat().st_size:,} bytes\n\nYour modified ROM is ready to use!")
                if QMessageBox.question(self, 'Clear Modifications?', 'ROM saved successfully!\n\nWould you like to clear the modification cache?\n\n(This will reset modification tracking, but your saved ROM is safe)', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                    self.rom_saver.clear_modifications()
                    self._set_status('Modifications cleared - ROM saved')
            else:
                self._set_status('ROM save failed')
                QMessageBox.critical(self, 'Save Failed', f'Failed to save ROM:\n\n{message}')
        except Exception as e:
            dlg.close()
            QMessageBox.critical(self, 'Save Error', f'ROM save operation failed:\n\n{str(e)}')
            self._set_status('ROM save failed')
            print('\n=== ROM SAVE ERROR ===')
            traceback.print_exc()
            print('======================\n')

    def _on_png_export(self):
        if not self.tileset_renderer.get_rendered_image():
            QMessageBox.warning(self, 'No Tileset', 'No tileset rendered to export')
            return
        filepath, _ = QFileDialog.getSaveFileName(self, 'Export Tileset as PNG', '', 'PNG files (*.png);;All files (*.*)')
        if filepath:
            self._set_status('Exporting PNG...')
            if self.tileset_renderer.export_png(filepath):
                self._set_status('PNG exported successfully')
                QMessageBox.information(self, 'Success', f'Tileset exported to:\n{filepath}')
            else:
                self._set_status('PNG export failed')
                QMessageBox.critical(self, 'Error', 'Failed to export PNG')
        else:
            self._set_status('Ready')

    def _on_import_tileset(self):
        if not self.map_selector.get_selected_map():
            QMessageBox.warning(self, 'No Map Selected', 'Please select a map before importing a tileset')
            return
        selected_map = self.map_selector.get_selected_map()
        dat_path = str(selected_map.dat_path)
        tex_path = str(selected_map.tex_path)
        self._set_status('Select tileset files to import...')
        file1_path, _ = QFileDialog.getOpenFileName(self, 'Select First Tileset File (RGCN or RLCN)', '', 'RGCN Graphics (*.rgcn *.ncgr);;RLCN Palette (*.rlcn *.nclr);;Binary files (*.bin);;All files (*.*)')
        if not file1_path:
            self._set_status('Ready')
            return
        file2_path, _ = QFileDialog.getOpenFileName(self, 'Select Second Tileset File (RGCN or RLCN)', '', 'RGCN Graphics (*.rgcn *.ncgr);;RLCN Palette (*.rlcn *.nclr);;Binary files (*.bin);;All files (*.*)')
        if not file2_path:
            self._set_status('Ready')
            return
        self._set_status('Analyzing files...')
        try:
            file1_info = get_file_info(file1_path)
            file2_info = get_file_info(file2_path)
            confirm_msg = f"Import these files?\n\nFile 1: {file1_info['name']}\n  Type: {file1_info['type']} ({file1_info['format']})\n  Size: {file1_info['size']:,} bytes\n\nFile 2: {file2_info['name']}\n  Type: {file2_info['type']} ({file2_info['format']})\n  Size: {file2_info['size']:,} bytes\n\nTarget Map: {selected_map.name}"
            if QMessageBox.question(self, 'Confirm Import', confirm_msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
                self._set_status('Ready')
                return
        except Exception as e:
            QMessageBox.critical(self, 'File Analysis Error', f'Failed to analyze files:\n{str(e)}')
            self._set_status('Ready')
            return
        self._set_status('Importing tileset (this may take a moment)...')
        try:
            success, message = import_tileset_auto_detect(dat_path=dat_path, tex_path=tex_path, file1_path=file1_path, file2_path=file2_path)
            if success:
                print('Tracking modifications in ROM saver...')
                self.rom_saver.add_modified_map_files(Path(dat_path), Path(tex_path))
                QMessageBox.information(self, 'Import Successful', message)
                self._set_status('Reloading map with new tileset...')
                self.map_selector.select_map(selected_map.name)
                self._set_status(f'Tileset imported successfully into {selected_map.name}')
            else:
                QMessageBox.critical(self, 'Import Failed', message)
                self._set_status('Import failed')
        except Exception as e:
            QMessageBox.critical(self, 'Import Error', f'Import operation failed:\n\n{str(e)}')
            self._set_status('Import failed')
            print('\n=== IMPORT ERROR ===')
            traceback.print_exc()
            print('====================\n')

    def _on_png_transfer(self):
        if not self.map_selector.get_selected_map():
            QMessageBox.warning(self, 'No Map Selected', 'Please select a map before transferring a PNG tileset')
            return
        selected_map = self.map_selector.get_selected_map()
        dat_path = str(selected_map.dat_path)
        tex_path = str(selected_map.tex_path)
        self._set_status('Select PNG image to convert...')
        png_path, _ = QFileDialog.getOpenFileName(self, 'Select PNG Image for Tileset', '', 'PNG Images (*.png);;All files (*.*)')
        if not png_path:
            self._set_status('Ready')
            return
        self._set_status('Analyzing PNG image...')
        try:
            png_info = get_png_info(png_path)
            if 'error' in png_info:
                QMessageBox.critical(self, 'PNG Error', f"Failed to read PNG file:\n{png_info['error']}")
                self._set_status('Ready')
                return
            unique_colors = png_info.get('unique_colors', 256)
            if unique_colors <= 16:
                auto_mode = 'Tile Banking Mode (15 colors + transparency)'
                mode_desc = 'Optimal for Pokemon Ranger - Best compatibility'
            else:
                auto_mode = 'Standard Mode (256 colors)'
                mode_desc = 'More colors, good compatibility'
            info_msg = f"PNG Image Information:\n\nFile: {png_info['name']}\nSize: {png_info['width']}x{png_info['height']} pixels\nColors: {unique_colors} unique colors\nTransparency: {('Yes' if png_info['has_transparency'] else 'No')}\nFile size: {png_info['file_size']:,} bytes\n\nAuto-Selected Mode: {auto_mode}\n{mode_desc}\n\n"
            if unique_colors > 256:
                info_msg += 'WARNING: >256 colors detected!\nImage will be quantized, quality may be reduced.\n\n'
            info_msg += 'Proceed with conversion?'
            if QMessageBox.question(self, 'PNG Image Info', info_msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
                self._set_status('Ready')
                return
        except Exception as e:
            QMessageBox.critical(self, 'Analysis Error', f'Failed to analyze PNG:\n{str(e)}')
            self._set_status('Ready')
            return
        self._set_status('Converting PNG (auto-detecting best mode)...')
        dlg = ProgressDialog(self, 'Converting...', 'Converting and integrating PNG tileset...\n\nMode: Auto-Detecting\nPlease wait...')
        dlg.show()
        QApplication.processEvents()
        try:
            success, message = transfer_png_to_map(png_path=png_path, dat_path=dat_path, tex_path=tex_path, use_tile_banks=None)
            dlg.close()
            if success:
                print('Tracking modifications in ROM saver...')
                self.rom_saver.add_modified_map_files(Path(dat_path), Path(tex_path))
                QMessageBox.information(self, 'Success', f'PNG Tileset Transfer Complete!\n\n{message}\n\nMap: {selected_map.name}\n\nThe map will now reload to display the new tileset.')
                self._set_status('Reloading map with new tileset...')
                self.map_selector.select_map(selected_map.name)
                self._set_status(f'PNG tileset successfully integrated into {selected_map.name}')
            else:
                QMessageBox.critical(self, 'Transfer Failed', f'Failed to transfer PNG tileset:\n\n{message}')
                self._set_status('PNG transfer failed')
        except Exception as e:
            dlg.close()
            QMessageBox.critical(self, 'Transfer Error', f'PNG transfer operation failed:\n\n{str(e)}')
            self._set_status('PNG transfer failed')
            print('\n=== PNG TRANSFER ERROR ===')
            traceback.print_exc()
            print('==========================\n')

    def _on_export_map_files(self):
        selected_map = self.map_selector.get_selected_map()
        if not selected_map:
            QMessageBox.warning(self, 'No Map Selected', 'Please select a map first.')
            return
        msg = f'Export map binary files for: {selected_map.name}\n\nWhich files would you like to export?\n\n  DAT - Compressed map data (.map.dat)\n  TEX - Compressed tileset data (.map.tex)\n\nFiles are exported as-is (LZ10 compressed).'
        export_dialog = _ExportMapDialog(self, selected_map.name)
        export_dialog.exec()
        choices = export_dialog.get_choices()
        if not choices:
            self._set_status('Export cancelled')
            return
        out_dir = QFileDialog.getExistingDirectory(self, 'Select Export Folder', '')
        if not out_dir:
            self._set_status('Export cancelled')
            return
        out_path = Path(out_dir)
        exported = []
        failed = []
        if choices.get('dat') and selected_map.dat_path:
            try:
                src = Path(selected_map.dat_path)
                dst = out_path / src.name
                dst.write_bytes(src.read_bytes())
                exported.append(src.name)
                print(f'Exported DAT: {dst}')
            except Exception as e:
                failed.append(f'DAT: {e}')
        if choices.get('tex') and selected_map.tex_path:
            try:
                src = Path(selected_map.tex_path)
                dst = out_path / src.name
                dst.write_bytes(src.read_bytes())
                exported.append(src.name)
                print(f'Exported TEX: {dst}')
            except Exception as e:
                failed.append(f'TEX: {e}')
        if exported:
            msg = f'Exported {len(exported)} file(s) to:\n{out_dir}\n\n'
            msg += '\n'.join((f'  {f}' for f in exported))
            if failed:
                msg += f'\n\nFailed:\n' + '\n'.join((f'  {f}' for f in failed))
            self._set_status(f'Exported {len(exported)} map file(s)')
            QMessageBox.information(self, 'Export Complete', msg)
        else:
            err_msg = '\n'.join(failed) if failed else 'No files were selected.'
            QMessageBox.critical(self, 'Export Failed', f'No files exported.\n\n{err_msg}')
            self._set_status('Export failed')

    def _on_export_tileset(self):
        idx = self.tileset_renderer.selected_tileset_index
        if idx is None:
            QMessageBox.warning(self, 'No Tileset Selected', 'Please select and render a tileset first.')
            return
        tilesets = self.tileset_renderer.get_tilesets()
        if idx >= len(tilesets):
            QMessageBox.warning(self, 'Error', 'Selected tileset index is out of range.')
            return
        tileset = tilesets[idx]
        rgcn_data = tileset.get('RGCN') or tileset.get('NCGR')
        rlcn_data = tileset.get('RLCN') or tileset.get('NCLR')
        if not rgcn_data and (not rlcn_data):
            QMessageBox.warning(self, 'No Data', f'Tileset {idx} has no RGCN or RLCN data to export.')
            return
        selected_map = self.map_selector.get_selected_map()
        map_name = selected_map.name if selected_map else 'map'
        export_dialog = _ExportTilesetDialog(self, idx, bool(rgcn_data), bool(rlcn_data))
        export_dialog.exec()
        choices = export_dialog.get_choices()
        if not choices:
            self._set_status('Export cancelled')
            return
        out_dir = QFileDialog.getExistingDirectory(self, 'Select Export Folder', '')
        if not out_dir:
            self._set_status('Export cancelled')
            return
        out_path = Path(out_dir)
        exported = []
        failed = []
        if choices.get('rgcn') and rgcn_data:
            try:
                filename = f'{map_name}_tileset{idx}_RGCN.bin'
                dst = out_path / filename
                dst.write_bytes(rgcn_data)
                exported.append(filename)
                print(f'Exported RGCN: {dst} ({len(rgcn_data):,} bytes)')
            except Exception as e:
                failed.append(f'RGCN: {e}')
        if choices.get('rlcn') and rlcn_data:
            try:
                filename = f'{map_name}_tileset{idx}_RLCN.bin'
                dst = out_path / filename
                dst.write_bytes(rlcn_data)
                exported.append(filename)
                print(f'Exported RLCN: {dst} ({len(rlcn_data):,} bytes)')
            except Exception as e:
                failed.append(f'RLCN: {e}')
        if exported:
            msg = f'Exported {len(exported)} file(s) to:\n{out_dir}\n\n'
            msg += '\n'.join((f'  {f}' for f in exported))
            if failed:
                msg += f'\n\nFailed:\n' + '\n'.join((f'  {f}' for f in failed))
            self._set_status(f'Exported tileset {idx} ({len(exported)} file(s))')
            QMessageBox.information(self, 'Export Complete', msg)
        else:
            err_msg = '\n'.join(failed) if failed else 'No files were selected.'
            QMessageBox.critical(self, 'Export Failed', f'No files exported.\n\n{err_msg}')
            self._set_status('Export failed')

class _ExportMapDialog(QDialog):

    def __init__(self, parent: QWidget, map_name: str):
        super().__init__(parent)
        self.setWindowTitle('Export Map Files')
        self.setFixedSize(340, 220)
        self.setModal(True)
        self._choices = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        title = QLabel(f'Export binary files for:\n{map_name}')
        title.setFont(QFont('Arial', 11, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f'color: {COLOR_TEXT};')
        layout.addWidget(title)
        from PyQt6.QtWidgets import QCheckBox
        self._chk_dat = QCheckBox('  DAT file  (LZ10 compressed map data)')
        self._chk_dat.setChecked(True)
        self._chk_dat.setStyleSheet(f'color: {COLOR_TEXT}; font-size: 11px;')
        layout.addWidget(self._chk_dat)
        self._chk_tex = QCheckBox('  TEX file  (LZ10 compressed tileset data)')
        self._chk_tex.setChecked(True)
        self._chk_tex.setStyleSheet(f'color: {COLOR_TEXT}; font-size: 11px;')
        layout.addWidget(self._chk_tex)
        layout.addStretch()
        btn_row = QHBoxLayout()
        btn_ok = _primary_btn('Export')
        btn_ok.setFixedHeight(36)
        btn_ok.clicked.connect(self._on_ok)
        btn_cancel = _primary_btn('Cancel')
        btn_cancel.setFixedHeight(36)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)

    def _on_ok(self):
        self._choices = {'dat': self._chk_dat.isChecked(), 'tex': self._chk_tex.isChecked()}
        self.accept()

    def get_choices(self):
        if self.result() != QDialog.DialogCode.Accepted:
            return {}
        return self._choices

class _ExportTilesetDialog(QDialog):

    def __init__(self, parent: QWidget, tileset_idx: int, has_rgcn: bool, has_rlcn: bool):
        super().__init__(parent)
        self.setWindowTitle('Export Tileset Files')
        self.setFixedSize(340, 220)
        self.setModal(True)
        self._choices = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        title = QLabel(f'Export binary files for:\nTileset {tileset_idx}')
        title.setFont(QFont('Arial', 11, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f'color: {COLOR_TEXT};')
        layout.addWidget(title)
        from PyQt6.QtWidgets import QCheckBox
        rgcn_label = '  RGCN  (graphics / tile data)' + ('' if has_rgcn else '  [unavailable]')
        self._chk_rgcn = QCheckBox(rgcn_label)
        self._chk_rgcn.setChecked(has_rgcn)
        self._chk_rgcn.setEnabled(has_rgcn)
        self._chk_rgcn.setStyleSheet(f'color: {COLOR_TEXT}; font-size: 11px;')
        layout.addWidget(self._chk_rgcn)
        rlcn_label = '  RLCN  (palette data)' + ('' if has_rlcn else '  [unavailable]')
        self._chk_rlcn = QCheckBox(rlcn_label)
        self._chk_rlcn.setChecked(has_rlcn)
        self._chk_rlcn.setEnabled(has_rlcn)
        self._chk_rlcn.setStyleSheet(f'color: {COLOR_TEXT}; font-size: 11px;')
        layout.addWidget(self._chk_rlcn)
        layout.addStretch()
        btn_row = QHBoxLayout()
        btn_ok = _primary_btn('Export')
        btn_ok.setFixedHeight(36)
        btn_ok.clicked.connect(self._on_ok)
        btn_cancel = _primary_btn('Cancel')
        btn_cancel.setFixedHeight(36)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)

    def _on_ok(self):
        self._choices = {'rgcn': self._chk_rgcn.isChecked(), 'rlcn': self._chk_rlcn.isChecked()}
        self.accept()

    def get_choices(self):
        if self.result() != QDialog.DialogCode.Accepted:
            return {}
        return self._choices
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = RomToolGUI()
    window.show()
    sys.exit(app.exec())
