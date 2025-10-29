"""
Desktop GUI application for OCR proofreading.

PyQt6-based application with image display, clickable bounding boxes,
and proofreading interface.
"""

import sys
import os
from typing import List, Optional, Tuple
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QTextEdit, QRadioButton,
    QLineEdit, QCheckBox, QGroupBox, QScrollArea, QMessageBox,
    QButtonGroup, QSplitter, QColorDialog, QSpinBox
)
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor, QImage
from PIL import Image, ImageDraw
import logging

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from ocr_proofread.core.config import get_config
from ocr_proofread.core.loader import FileLoader
from ocr_proofread.core.validator import Validator, ValidationMessage
from ocr_proofread.core.models import ProofreadSession, HocrWord
from ocr_proofread.core.exporter import HocrExporter
from ocr_proofread.core.image_handler import ImageHandler


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ClickableImageLabel(QLabel):
    """
    QLabel that displays an image with clickable bounding boxes.
    
    Signals:
    bbox_clicked: Emitted when a bounding box is clicked (word_id).
    """
    
    bbox_clicked = pyqtSignal(str)
    
    def __init__(self, parent=None):
        """Initialize clickable image label."""
        super().__init__(parent)
        self.setMouseTracking(True)
        self.bboxes: List[Tuple[str, QRect]] = []
        self.selected_word_id: Optional[str] = None
        self.matching_color = QColor(0, 255, 0)  # Green
        self.unverified_color = QColor(255, 255, 0)  # Yellow
        self.matching_word_ids: set = set()
        self.zoom_factor: float = 1.0
        self.original_pixmap: Optional[QPixmap] = None
        self.scroll_area: Optional[QScrollArea] = None
    
    def set_image_with_bboxes(
        self,
        image_path: str,
        words: List[HocrWord],
        matching_word_ids: set,
        selected_word_id: Optional[str] = None
    ):
        """
        Load image and draw bounding boxes.
        
        Parameters:
        image_path (str): Path to image file.
        words (List[HocrWord]): List of words with bounding boxes.
        matching_word_ids (set): Set of word IDs that match across all files.
        selected_word_id (str): Currently selected word ID.
        """
        self.matching_word_ids = matching_word_ids
        self.selected_word_id = selected_word_id
        
        # Load image
        img_handler = ImageHandler()
        pil_image = img_handler.load_image(image_path)
        
        # Convert to RGB if needed
        if pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')
        
        # Draw bounding boxes
        draw = ImageDraw.Draw(pil_image, 'RGBA')
        
        config = get_config()
        line_width = config.bbox_line_width
        
        self.bboxes = []
        
        for word in words:
            bbox = word.bbox
            word_id = word.word_id
            
            # Determine color
            if word_id in matching_word_ids:
                color = tuple(list(self.matching_color.getRgb()[:3]))
            else:
                color = tuple(list(self.unverified_color.getRgb()[:3]))
            
            # Draw box
            draw.rectangle(
                [bbox.x1, bbox.y1, bbox.x2, bbox.y2],
                outline=color,
                width=line_width
            )
            
            # Add selection highlight
            if word_id == selected_word_id:
                overlay_color = color + (int(255 * config.bbox_selection_opacity),)
                draw.rectangle(
                    [bbox.x1, bbox.y1, bbox.x2, bbox.y2],
                    fill=overlay_color
                )
            
            # Store bbox for click detection
            self.bboxes.append((word_id, QRect(bbox.x1, bbox.y1, bbox.x2 - bbox.x1, bbox.y2 - bbox.y1)))
        
        # Convert to QPixmap
        img_data = pil_image.tobytes('raw', 'RGB')
        qimage = QImage(
            img_data, pil_image.width, pil_image.height, 
            pil_image.width * 3, QImage.Format.Format_RGB888
        )
        pixmap = QPixmap.fromImage(qimage)
        self.original_pixmap = pixmap
        self._apply_zoom()
    
    def _apply_zoom(self):
        """Apply current zoom factor to the image."""
        if self.original_pixmap:
            if self.zoom_factor != 1.0:
                scaled_pixmap = self.original_pixmap.scaled(
                    int(self.original_pixmap.width() * self.zoom_factor),
                    int(self.original_pixmap.height() * self.zoom_factor),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.setPixmap(scaled_pixmap)
            else:
                self.setPixmap(self.original_pixmap)
            self.adjustSize()
    
    def set_zoom(self, zoom_factor: float):
        """Set zoom factor and update display."""
        self.zoom_factor = max(0.1, min(5.0, zoom_factor))  # Limit zoom between 10% and 500%
        self._apply_zoom()
    
    def zoom_to_width(self):
        """Zoom to fit width of scroll area."""
        if self.original_pixmap and self.scroll_area:
            available_width = self.scroll_area.viewport().width() - 20  # 20px padding
            zoom = available_width / self.original_pixmap.width()
            self.set_zoom(zoom)
            return zoom
        return self.zoom_factor
    
    def zoom_to_height(self):
        """Zoom to fit height of scroll area."""
        if self.original_pixmap and self.scroll_area:
            available_height = self.scroll_area.viewport().height() - 20  # 20px padding
            zoom = available_height / self.original_pixmap.height()
            self.set_zoom(zoom)
            return zoom
        return self.zoom_factor
    
    def mousePressEvent(self, event):
        """Handle mouse clicks to detect bbox selection."""
        pos = event.pos()
        
        # Adjust position for zoom
        adjusted_x = int(pos.x() / self.zoom_factor)
        adjusted_y = int(pos.y() / self.zoom_factor)
        adjusted_pos = QPoint(adjusted_x, adjusted_y)
        
        # Check if click is within any bbox
        for word_id, rect in self.bboxes:
            if rect.contains(adjusted_pos):
                self.bbox_clicked.emit(word_id)
                break
        
        super().mousePressEvent(event)


class ProofreadingPanel(QWidget):
    """
    Panel showing word text from multiple hOCR files for proofreading.
    
    Signals:
    text_changed: Emitted when user changes word text (word_id, new_text).
    """
    
    text_changed = pyqtSignal(str, str)
    
    def __init__(self, parent=None):
        """Initialize proofreading panel."""
        super().__init__(parent)
        self.word_id: Optional[str] = None
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout()
        
        # Title
        self.title_label = QLabel("Word Proofreading")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(self.title_label)
        
        # Scroll area for radio buttons
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(300)
        
        self.options_widget = QWidget()
        self.options_layout = QVBoxLayout(self.options_widget)
        scroll.setWidget(self.options_widget)
        
        layout.addWidget(scroll)
        
        # User edit box
        self.edit_label = QLabel("Custom text:")
        layout.addWidget(self.edit_label)
        
        self.edit_text = QLineEdit()
        self.edit_text.textChanged.connect(self.on_edit_changed)
        layout.addWidget(self.edit_text)
        
        # Warning label
        self.warning_label = QLabel("")
        self.warning_label.setStyleSheet("color: orange;")
        layout.addWidget(self.warning_label)
        
        # Button group for radio buttons
        self.button_group = QButtonGroup()
        
        self.setLayout(layout)
    
    def load_word(
        self,
        word_id: str,
        unit,
        current_text: str = None
    ):
        """
        Load word data from proofreading unit.
        
        Parameters:
        word_id (str): Word ID to load.
        unit: ProofreadingUnit object.
        current_text (str): Current text value (with changes applied).
        """
        self.word_id = word_id
        
        # Clear existing options
        for button in self.button_group.buttons():
            self.button_group.removeButton(button)
            button.deleteLater()
        
        while self.options_layout.count():
            item = self.options_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Get word text from each hOCR file
        word_texts = []
        for doc in unit.hocr_documents:
            word = doc.get_word_by_id(word_id)
            if word:
                word_texts.append((doc.filename, word.text))
        
        # Add radio buttons for each file
        for filename, text in word_texts:
            radio = QRadioButton(f"{filename}: '{text}'")
            radio.toggled.connect(lambda checked, t=text: self.on_radio_selected(checked, t))
            self.button_group.addButton(radio)
            self.options_layout.addWidget(radio)
        
        # Add custom text radio
        self.custom_radio = QRadioButton("Custom:")
        self.button_group.addButton(self.custom_radio)
        self.options_layout.addWidget(self.custom_radio)
        
        # Set current text
        if current_text is None and word_texts:
            current_text = word_texts[0][1]
        
        if current_text:
            self.edit_text.setText(current_text)
            
            # Select appropriate radio button
            found = False
            for idx, (_, text) in enumerate(word_texts):
                if text == current_text:
                    self.button_group.buttons()[idx].setChecked(True)
                    found = True
                    break
            
            if not found:
                self.custom_radio.setChecked(True)
        
        # Store original length for comparison
        if word_texts:
            self.original_length = len(word_texts[0][1])
        else:
            self.original_length = 0
        
        self.check_length_warning()
    
    def on_radio_selected(self, checked: bool, text: str):
        """Handle radio button selection."""
        if checked and self.word_id:
            self.edit_text.setText(text)
            self.text_changed.emit(self.word_id, text)
    
    def on_edit_changed(self, text: str):
        """Handle edit text changes."""
        # Select custom radio when editing
        self.custom_radio.setChecked(True)
        
        if self.word_id:
            self.text_changed.emit(self.word_id, text)
        
        self.check_length_warning()
    
    def check_length_warning(self):
        """Check if text length exceeds original and show warning."""
        current_length = len(self.edit_text.text())
        
        if current_length > self.original_length * 2:
            self.warning_label.setText("⚠ Typed word may extend beyond bounding box!")
        else:
            self.warning_label.setText("")


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        """Initialize main window."""
        super().__init__()
        self.session: Optional[ProofreadSession] = None
        self.current_word_index: int = 0
        self.validator = Validator()
        self.validation_messages: List[ValidationMessage] = []
        self.config = get_config()
        
        self.init_ui()
        self.setWindowTitle("OCR Proofreading Application")
        self.resize(1400, 900)
    
    def init_ui(self):
        """Initialize user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        
        # Top toolbar
        toolbar = self.create_toolbar()
        main_layout.addWidget(toolbar)
        
        # Options panel
        options_panel = self.create_options_panel()
        main_layout.addWidget(options_panel)
        
        # Main content area (splitter)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side - Image and navigation
        left_panel = self.create_image_panel()
        splitter.addWidget(left_panel)
        
        # Right side - Proofreading panel
        self.proofread_panel = ProofreadingPanel()
        self.proofread_panel.text_changed.connect(self.on_word_text_changed)
        splitter.addWidget(self.proofread_panel)
        
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(splitter, stretch=3)
        
        # Bottom - Log area
        log_panel = self.create_log_panel()
        main_layout.addWidget(log_panel, stretch=1)
    
    def create_toolbar(self) -> QWidget:
        """Create top toolbar with file operations."""
        toolbar = QWidget()
        layout = QHBoxLayout(toolbar)
        
        btn_load = QPushButton("Load Files")
        btn_load.clicked.connect(self.load_files)
        layout.addWidget(btn_load)
        
        btn_save_page = QPushButton("Save Current Page")
        btn_save_page.clicked.connect(self.save_current_page)
        layout.addWidget(btn_save_page)
        
        btn_save_all = QPushButton("Save All Changed Pages")
        btn_save_all.clicked.connect(self.save_all_changed)
        layout.addWidget(btn_save_all)
        
        btn_export_merged = QPushButton("Export Merged File")
        btn_export_merged.clicked.connect(self.export_merged)
        layout.addWidget(btn_export_merged)
        
        layout.addStretch()
        
        return toolbar
    
    def create_options_panel(self) -> QWidget:
        """Create options panel."""
        panel = QGroupBox("Options")
        layout = QHBoxLayout(panel)
        
        self.cb_skip_matching = QCheckBox("Skip matching words")
        layout.addWidget(self.cb_skip_matching)
        
        self.cb_skip_all_matching_pages = QCheckBox("Skip pages where all words match")
        layout.addWidget(self.cb_skip_all_matching_pages)
        
        self.cb_prompt_save = QCheckBox("Prompt to save on page change")
        layout.addWidget(self.cb_prompt_save)
        
        btn_matching_color = QPushButton("Matching Color")
        btn_matching_color.clicked.connect(self.change_matching_color)
        layout.addWidget(btn_matching_color)
        
        btn_unverified_color = QPushButton("Unverified Color")
        btn_unverified_color.clicked.connect(self.change_unverified_color)
        layout.addWidget(btn_unverified_color)
        
        layout.addStretch()
        
        return panel
    
    def create_image_panel(self) -> QWidget:
        """Create image display panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Image info and navigation
        nav_layout = QHBoxLayout()
        
        self.btn_prev_page = QPushButton("◀ Previous Page")
        self.btn_prev_page.clicked.connect(self.previous_page)
        nav_layout.addWidget(self.btn_prev_page)
        
        self.label_page_info = QLabel("No file loaded")
        self.label_page_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav_layout.addWidget(self.label_page_info, stretch=1)
        
        self.btn_next_page = QPushButton("Next Page ▶")
        self.btn_next_page.clicked.connect(self.next_page)
        nav_layout.addWidget(self.btn_next_page)
        
        layout.addLayout(nav_layout)
        
        # Zoom controls
        zoom_layout = QHBoxLayout()
        
        self.btn_zoom_out = QPushButton("Zoom Out")
        self.btn_zoom_out.clicked.connect(self.zoom_out)
        zoom_layout.addWidget(self.btn_zoom_out)
        
        self.btn_zoom_in = QPushButton("Zoom In")
        self.btn_zoom_in.clicked.connect(self.zoom_in)
        zoom_layout.addWidget(self.btn_zoom_in)
        
        zoom_layout.addWidget(QLabel("Zoom:"))
        
        self.zoom_spinbox = QSpinBox()
        self.zoom_spinbox.setRange(10, 500)
        self.zoom_spinbox.setValue(100)
        self.zoom_spinbox.setSuffix("%")
        self.zoom_spinbox.valueChanged.connect(self.on_zoom_changed)
        zoom_layout.addWidget(self.zoom_spinbox)
        
        self.btn_zoom_to_width = QPushButton("Zoom to Width")
        self.btn_zoom_to_width.clicked.connect(self.zoom_to_width)
        zoom_layout.addWidget(self.btn_zoom_to_width)
        
        self.btn_zoom_to_height = QPushButton("Zoom to Height")
        self.btn_zoom_to_height.clicked.connect(self.zoom_to_height)
        zoom_layout.addWidget(self.btn_zoom_to_height)
        
        zoom_layout.addStretch()
        
        layout.addLayout(zoom_layout)
        
        # Image display (scrollable)
        self.image_scroll = QScrollArea()
        self.image_scroll.setWidgetResizable(False)  # Changed to False for zoom
        
        self.image_label = ClickableImageLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.image_label.bbox_clicked.connect(self.on_bbox_clicked)
        self.image_label.scroll_area = self.image_scroll
        self.image_scroll.setWidget(self.image_label)
        
        layout.addWidget(self.image_scroll)
        
        # Word navigation
        word_nav_layout = QHBoxLayout()
        
        self.btn_prev_word = QPushButton("◀ Previous Word")
        self.btn_prev_word.clicked.connect(self.previous_word)
        word_nav_layout.addWidget(self.btn_prev_word)
        
        self.label_word_info = QLabel("")
        self.label_word_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        word_nav_layout.addWidget(self.label_word_info, stretch=1)
        
        self.btn_next_word = QPushButton("Next Word ▶")
        self.btn_next_word.clicked.connect(self.next_word)
        word_nav_layout.addWidget(self.btn_next_word)
        
        layout.addLayout(word_nav_layout)
        
        return panel
    
    def create_log_panel(self) -> QWidget:
        """Create log display panel."""
        panel = QGroupBox("Log Messages")
        layout = QVBoxLayout(panel)
        
        # Log filter checkboxes
        filter_layout = QHBoxLayout()
        
        self.cb_show_info = QCheckBox("Info")
        self.cb_show_info.setChecked(True)
        self.cb_show_info.stateChanged.connect(self.update_log_display)
        filter_layout.addWidget(self.cb_show_info)
        
        self.cb_show_warning = QCheckBox("Warning")
        self.cb_show_warning.setChecked(True)
        self.cb_show_warning.stateChanged.connect(self.update_log_display)
        filter_layout.addWidget(self.cb_show_warning)
        
        self.cb_show_critical = QCheckBox("Critical")
        self.cb_show_critical.setChecked(True)
        self.cb_show_critical.stateChanged.connect(self.update_log_display)
        filter_layout.addWidget(self.cb_show_critical)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        layout.addWidget(self.log_text)
        
        return panel
    
    def load_files(self):
        """Load files from directory."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Directory with Images and hOCR Files",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        
        if not directory:
            return
        
        try:
            # Show size limit info
            size_limit_mb = self.config.max_upload_size_mb
            total_size = FileLoader.calculate_total_size(directory)
            total_size_mb = total_size / (1024 * 1024)
            
            self.add_log(
                f"Directory size: {total_size_mb:.2f} MB (limit: {size_limit_mb} MB)",
                "info"
            )
            
            if total_size_mb > size_limit_mb:
                reply = QMessageBox.question(
                    self,
                    "Size Limit Exceeded",
                    f"Directory size ({total_size_mb:.2f} MB) exceeds limit ({size_limit_mb} MB). "
                    "Continue anyway?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    return
            
            # Load files
            self.session = FileLoader.load_files(directory)
            self.add_log(f"Loaded {self.session.total_units} proofreading units", "info")
            
            # Validate
            self.validation_messages = self.validator.validate_all_units(self.session.units)
            for msg in self.validation_messages:
                self.add_log(str(msg), msg.level)
            
            # Display first unit
            self.current_word_index = 0
            self.display_current_unit()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load files: {e}")
            logger.exception("Failed to load files")
    
    def display_current_unit(self):
        """Display current proofreading unit."""
        if not self.session:
            return
        
        unit = self.session.current_unit
        
        # Update page info
        self.label_page_info.setText(
            f"{unit.image_filename} - Page {self.session.current_index + 1} "
            f"of {self.session.total_units}"
        )
        
        # Get all words
        words = unit.primary_document.page.get_all_words()
        
        if not words:
            self.add_log(f"No words found in {unit.image_filename}", "warning")
            return
        
        # Determine which words match
        matching_word_ids = []
        for word in words:
            if Validator.words_match_across_documents(unit, word.word_id):
                matching_word_ids.append(word.word_id)
        
        # Display image with bboxes
        selected_word_id = words[self.current_word_index].word_id if words else None
        self.image_label.set_image_with_bboxes(
            unit.image_path,
            words,
            set(matching_word_ids),
            selected_word_id
        )
        
        # Update word info
        self.label_word_info.setText(f"Word {self.current_word_index + 1} of {len(words)}")
        
        # Load word in proofreading panel
        if selected_word_id:
            current_text = self.session.get_word_text(selected_word_id)
            self.proofread_panel.load_word(selected_word_id, unit, current_text)
    
    def on_bbox_clicked(self, word_id: str):
        """Handle bounding box click."""
        if not self.session:
            return
        
        # Find word index
        words = self.session.current_unit.primary_document.page.get_all_words()
        for idx, word in enumerate(words):
            if word.word_id == word_id:
                self.current_word_index = idx
                self.display_current_unit()
                break
    
    def on_word_text_changed(self, word_id: str, new_text: str):
        """Handle word text change."""
        if self.session:
            self.session.set_word_text(word_id, new_text)
    
    def previous_word(self):
        """Navigate to previous word."""
        if not self.session:
            return
        
        words = self.session.current_unit.primary_document.page.get_all_words()
        skip_matching = self.cb_skip_matching.isChecked()
        
        # Find previous word
        new_index = self.current_word_index
        while True:
            new_index -= 1
            if new_index < 0:
                self.add_log("Already at first word", "info")
                return
            
            # Check if we should skip this word
            if skip_matching:
                word_id = words[new_index].word_id
                if not Validator.words_match_across_documents(
                    self.session.current_unit, word_id
                ):
                    break
            else:
                break
        
        self.current_word_index = new_index
        self.display_current_unit()
    
    def next_word(self):
        """Navigate to next word."""
        if not self.session:
            return
        
        words = self.session.current_unit.primary_document.page.get_all_words()
        skip_matching = self.cb_skip_matching.isChecked()
        
        # Find next word
        new_index = self.current_word_index
        while True:
            new_index += 1
            if new_index >= len(words):
                # Move to next page
                self.next_page()
                return
            
            # Check if we should skip this word
            if skip_matching:
                word_id = words[new_index].word_id
                if not Validator.words_match_across_documents(
                    self.session.current_unit, word_id
                ):
                    break
            else:
                break
        
        self.current_word_index = new_index
        self.display_current_unit()
    
    def previous_page(self):
        """Navigate to previous page."""
        if not self.session:
            return
        
        if self.session.current_index <= 0:
            self.add_log("Already at first page", "info")
            return
        
        # Check if we need to save current page
        if self.cb_prompt_save.isChecked() and self.session.has_changes():
            reply = QMessageBox.question(
                self,
                "Save Changes",
                "Save changes to current page before leaving?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Cancel:
                return
            elif reply == QMessageBox.StandardButton.Yes:
                self.save_current_page()
        
        self.session.current_index -= 1
        self.current_word_index = 0
        
        # Skip pages where all words match if option is set
        if self.cb_skip_all_matching_pages.isChecked():
            while (self.session.current_index >= 0 and
                   Validator.all_words_match_in_unit(self.session.current_unit)):
                self.session.current_index -= 1
        
        if self.session.current_index < 0:
            self.session.current_index = 0
            self.add_log("Already at first page", "info")
        
        self.display_current_unit()
    
    def next_page(self):
        """Navigate to next page."""
        if not self.session:
            return
        
        if self.session.current_index >= self.session.total_units - 1:
            self.add_log("Already at last page", "info")
            return
        
        # Check if we need to save current page
        if self.cb_prompt_save.isChecked() and self.session.has_changes():
            reply = QMessageBox.question(
                self,
                "Save Changes",
                "Save changes to current page before leaving?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Cancel:
                return
            elif reply == QMessageBox.StandardButton.Yes:
                self.save_current_page()
        
        self.session.current_index += 1
        self.current_word_index = 0
        
        # Skip pages where all words match if option is set
        if self.cb_skip_all_matching_pages.isChecked():
            while (self.session.current_index < self.session.total_units and
                   Validator.all_words_match_in_unit(self.session.current_unit)):
                self.session.current_index += 1
        
        if self.session.current_index >= self.session.total_units:
            self.session.current_index = self.session.total_units - 1
            self.add_log("Already at last page", "info")
        
        self.display_current_unit()
    
    def save_current_page(self):
        """Save current page if it has changes."""
        if not self.session:
            QMessageBox.warning(self, "Warning", "No files loaded")
            return
        
        unit_index = self.session.current_index
        if not self.session.has_changes(unit_index):
            QMessageBox.information(self, "Info", "No changes to save")
            return
        
        try:
            unit = self.session.units[unit_index]
            changes = self.session.changes[unit_index]
            output_path = HocrExporter.export_unit(unit, changes)
            self.add_log(f"Saved page to {output_path}", "info")
            QMessageBox.information(self, "Success", f"Saved to:\n{output_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save: {e}")
            logger.exception("Failed to save page")
    
    def save_all_changed(self):
        """Save all changed pages."""
        if not self.session:
            QMessageBox.warning(self, "Warning", "No files loaded")
            return
        
        changed_count = sum(1 for changes in self.session.changes.values() if changes)
        if changed_count == 0:
            QMessageBox.information(self, "Info", "No changes to save")
            return
        
        try:
            exported_files = HocrExporter.export_changed_units(self.session)
            self.add_log(f"Saved {len(exported_files)} changed pages", "info")
            QMessageBox.information(
                self,
                "Success",
                f"Saved {len(exported_files)} changed pages"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save: {e}")
            logger.exception("Failed to save changed pages")
    
    def export_merged(self):
        """Export merged hOCR file."""
        if not self.session:
            QMessageBox.warning(self, "Warning", "No files loaded")
            return
        
        # Get default filename
        default_name = HocrExporter.create_merged_filename(
            self.session.units[0].image_filename
        )
        
        # Ask user for save location
        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Merged hOCR File",
            default_name,
            "hOCR Files (*.hocr);;All Files (*)"
        )
        
        if not output_path:
            return
        
        try:
            HocrExporter.export_merged(self.session, output_path)
            self.add_log(f"Exported merged file to {output_path}", "info")
            QMessageBox.information(
                self,
                "Success",
                f"Exported merged file to:\n{output_path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export: {e}")
            logger.exception("Failed to export merged file")
    
    def change_matching_color(self):
        """Change color for matching words."""
        color = QColorDialog.getColor(self.image_label.matching_color, self)
        if color.isValid():
            self.image_label.matching_color = color
            self.display_current_unit()
    
    def change_unverified_color(self):
        """Change color for unverified words."""
        color = QColorDialog.getColor(self.image_label.unverified_color, self)
        if color.isValid():
            self.image_label.unverified_color = color
            self.display_current_unit()
    
    def zoom_in(self):
        """Zoom in by 25%."""
        new_zoom = self.image_label.zoom_factor * 1.25
        self.image_label.set_zoom(new_zoom)
        self.zoom_spinbox.setValue(int(new_zoom * 100))
    
    def zoom_out(self):
        """Zoom out by 25%."""
        new_zoom = self.image_label.zoom_factor * 0.8
        self.image_label.set_zoom(new_zoom)
        self.zoom_spinbox.setValue(int(new_zoom * 100))
    
    def on_zoom_changed(self, value: int):
        """Handle zoom percentage change from spinbox."""
        zoom = value / 100.0
        self.image_label.set_zoom(zoom)
    
    def zoom_to_width(self):
        """Zoom image to fit width."""
        zoom = self.image_label.zoom_to_width()
        self.zoom_spinbox.setValue(int(zoom * 100))
    
    def zoom_to_height(self):
        """Zoom image to fit height."""
        zoom = self.image_label.zoom_to_height()
        self.zoom_spinbox.setValue(int(zoom * 100))
    
    def add_log(self, message: str, level: str = "info"):
        """Add log message."""
        # Store for filtering
        if not hasattr(self, '_log_messages'):
            self._log_messages = []
        self._log_messages.append((level, message))
        
        self.update_log_display()
    
    def update_log_display(self):
        """Update log display based on filters."""
        if not hasattr(self, '_log_messages'):
            return
        
        show_info = self.cb_show_info.isChecked()
        show_warning = self.cb_show_warning.isChecked()
        show_critical = self.cb_show_critical.isChecked()
        
        filtered_messages = []
        for level, message in self._log_messages:
            if level == "info" and show_info:
                filtered_messages.append(f"[INFO] {message}")
            elif level == "warning" and show_warning:
                filtered_messages.append(f"[WARNING] {message}")
            elif level == "critical" and show_critical:
                filtered_messages.append(f"[CRITICAL] {message}")
        
        self.log_text.setPlainText("\n".join(filtered_messages))
        
        # Scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())


def main():
    """Run the desktop application."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
