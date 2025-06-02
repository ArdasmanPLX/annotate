import os
import json
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QTextEdit, QLabel, QFileDialog, QMessageBox,
                             QListWidget, QListWidgetItem, QProgressBar, QGroupBox, QComboBox, QDialog,
                             QRadioButton, QButtonGroup, QLineEdit, QFormLayout)
from PyQt5.QtGui import QPixmap, QColor, QDragEnterEvent, QDropEvent
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from database import DatabaseManager
from annotation import AnnotationManager, available_models
from config import DEFAULT_PROMPT, COMFY_DEFAULTS
from comfy_client import ComfyUIClient

SETTINGS_FILE = "comfy_settings.json"


def load_generation_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return COMFY_DEFAULTS.copy()


def save_generation_settings(settings: dict):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=4)

#DragDrop
class DragDropLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setText("\n\n Drag & Drop Image or Folder Here \n\n")
        self.setStyleSheet('''
            QLabel{
                border: 2px dashed #aaa;
                border-radius: 5px;
            }
        ''')
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.DropAction.CopyAction)
            file_path = event.mimeData().urls()[0].toLocalFile()
            if os.path.isdir(file_path):
                self.window().process_dropped_folder(file_path)
            else:
                self.window().load_image(file_path)
            event.accept()
        else:
            event.ignore()

#Promt Dialog
class PromptDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Annotation Prompt")
        self.setGeometry(200, 200, 400, 300)

        layout = QVBoxLayout()

        self.prompt_type_group = QButtonGroup(self)
        self.custom_prompt_radio = QRadioButton("Custom Prompt")
        self.file_prompt_radio = QRadioButton("Load Prompt from File")
        self.prompt_type_group.addButton(self.custom_prompt_radio)
        self.prompt_type_group.addButton(self.file_prompt_radio)

        layout.addWidget(self.custom_prompt_radio)
        layout.addWidget(self.file_prompt_radio)

        self.prompt_text = QTextEdit()
        self.prompt_text.setPlainText(DEFAULT_PROMPT)
        layout.addWidget(self.prompt_text)

        self.file_path_input = QLineEdit()
        self.file_path_input.setReadOnly(True)
        layout.addWidget(self.file_path_input)

        self.load_file_button = QPushButton("Load File")
        self.load_file_button.clicked.connect(self.load_prompt_file)
        layout.addWidget(self.load_file_button)

        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        layout.addWidget(self.ok_button)

        self.setLayout(layout)

        self.custom_prompt_radio.toggled.connect(self.toggle_input_fields)
        self.file_prompt_radio.toggled.connect(self.toggle_input_fields)
        self.custom_prompt_radio.setChecked(True)
        self.toggle_input_fields()

    def toggle_input_fields(self):
        is_custom = self.custom_prompt_radio.isChecked()
        self.prompt_text.setEnabled(is_custom)
        self.file_path_input.setEnabled(not is_custom)
        self.load_file_button.setEnabled(not is_custom)

    def load_prompt_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Prompt File", "", "Text Files (*.txt)")
        if file_path:
            self.file_path_input.setText(file_path)
            with open(file_path, 'r', encoding='utf-8') as file:
                self.prompt_text.setPlainText(file.read())

    def get_prompt(self):
        if self.custom_prompt_radio.isChecked():
            return self.prompt_text.toPlainText()
        else:
            return self.prompt_text.toPlainText() if self.file_path_input.text() else DEFAULT_PROMPT


class GenerationSettingsDialog(QDialog):
    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Generation Settings")
        self.setGeometry(200, 200, 400, 300)

        layout = QVBoxLayout()
        form = QFormLayout()

        self.server_edit = QLineEdit(settings.get("server", ""))
        self.model_edit = QLineEdit(settings.get("model", ""))
        self.width_edit = QLineEdit(str(settings.get("width", 512)))
        self.height_edit = QLineEdit(str(settings.get("height", 512)))
        self.steps_edit = QLineEdit(str(settings.get("steps", 20)))

        form.addRow("Server", self.server_edit)
        form.addRow("Model", self.model_edit)
        form.addRow("Width", self.width_edit)
        form.addRow("Height", self.height_edit)
        form.addRow("Steps", self.steps_edit)

        layout.addLayout(form)
        layout.addWidget(QLabel("Workflow JSON:"))
        self.workflow_edit = QTextEdit()
        self.workflow_edit.setPlainText(settings.get("workflow", ""))
        layout.addWidget(self.workflow_edit)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def get_settings(self) -> dict:
        return {
            "server": self.server_edit.text(),
            "model": self.model_edit.text(),
            "width": int(self.width_edit.text() or 0),
            "height": int(self.height_edit.text() or 0),
            "steps": int(self.steps_edit.text() or 0),
            "workflow": self.workflow_edit.toPlainText(),
        }


class GenerateImageThread(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, client: ComfyUIClient, prompt: str, settings: dict):
        super().__init__()
        self.client = client
        self.prompt = prompt
        self.settings = settings

    def run(self):
        try:
            path = self.client.generate_image(
                self.prompt,
                self.settings.get("model", ""),
                self.settings.get("width", 512),
                self.settings.get("height", 512),
                self.settings.get("steps", 20),
                self.settings.get("workflow", ""),
            )
            self.finished.emit(path)
        except Exception as e:
            self.error.emit(str(e))

class SingleAnnotationThread(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, annotation_manager, image_path, prompt, model):
        super().__init__()
        self.annotation_manager = annotation_manager
        self.image_path = image_path
        self.prompt = prompt
        self.model = model

    def run(self):
        try:
            annotation = self.annotation_manager.generate_annotation(self.image_path, self.prompt, self.model)
            self.finished.emit(annotation)
        except Exception as e:
            self.error.emit(str(e))

class AnnotationThread(QThread):
    progress = pyqtSignal(int, int, int)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, folder_path, prompt, model, db_manager, annotation_manager):
        super().__init__()
        self.folder_path = folder_path
        self.prompt = prompt
        self.model = model
        self.db_manager = db_manager
        self.annotation_manager = annotation_manager

    def run(self):
        image_files = [f for f in os.listdir(self.folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))]
        total_files = len(image_files)

        for i, image_file in enumerate(image_files, start=1):
            try:
                image_path = os.path.join(self.folder_path, image_file)
                annotation = self.annotation_manager.generate_annotation(image_path, self.prompt, self.model)
                # Используем правильный метод для вставки аннотации
                self.db_manager.insert_or_update_annotation(image_path, annotation)
                self.progress.emit(i, total_files, int((i / total_files) * 100))
            except Exception as e:
                self.error.emit(f"Error annotating {image_file}: {str(e)}")

        self.finished.emit()

#Functional
class ImageAnnotationApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.annotation_manager = AnnotationManager()
        self.generation_settings = load_generation_settings()
        self.comfy_client = ComfyUIClient(self.generation_settings.get("server", ""))
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Image Annotation App BY Alexey Astapov")
        self.setGeometry(100, 100, 1200, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # LLM Model selection
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("LLM Model:"))
        self.model_combo = QComboBox()
        models = available_models() or ["gpt-4-turbo"]
        self.model_combo.addItems(models)
        self.model_combo.setFixedWidth(200)
        model_layout.addWidget(self.model_combo)
        model_layout.addStretch()
        main_layout.addLayout(model_layout)

        # Button groups
        button_layout = QHBoxLayout()
        manual_group = QGroupBox("Manual Annotation")
        llm_group = QGroupBox("LLM Annotation")
        generate_group = QGroupBox("Image Generation")
        database_group = QGroupBox("Image Data Base")

        manual_layout = QHBoxLayout()
        llm_layout = QHBoxLayout()
        generate_layout = QHBoxLayout()
        database_layout = QHBoxLayout()

        self.load_button = QPushButton("Load Image")
        self.load_button.clicked.connect(self.load_image_dialog)
        manual_layout.addWidget(self.load_button)

        self.save_button = QPushButton("Save Annotation")
        self.save_button.clicked.connect(self.save_annotation)
        manual_layout.addWidget(self.save_button)

        self.auto_annotate_button = QPushButton("Annotate Image")
        self.auto_annotate_button.clicked.connect(self.auto_annotate)
        llm_layout.addWidget(self.auto_annotate_button)

        self.folder_annotate_button = QPushButton("Annotate Folder")
        self.folder_annotate_button.clicked.connect(self.annotate_folder)
        llm_layout.addWidget(self.folder_annotate_button)

        self.generate_button = QPushButton("Generate")
        self.generate_button.clicked.connect(self.generate_image)
        generate_layout.addWidget(self.generate_button)

        self.gen_settings_button = QPushButton("Generation Settings")
        self.gen_settings_button.clicked.connect(self.open_generation_settings)
        generate_layout.addWidget(self.gen_settings_button)

        self.clear_db_button = QPushButton("Clear Database")
        self.clear_db_button.clicked.connect(self.clear_database)
        database_layout.addWidget(self.clear_db_button)

        self.delete_annotation_button = QPushButton("Delete Annotation")
        self.delete_annotation_button.clicked.connect(self.delete_annotation)
        database_layout.addWidget(self.delete_annotation_button)

        # Добавляем кнопку для очистки предпросмотра
        self.clear_preview_button = QPushButton("Clear Preview")
        self.clear_preview_button.clicked.connect(self.clear_preview)

        # Добавляем кнопку для генерации текстовых файлов
        self.generate_text_files_button = QPushButton("Generate Text Files")
        self.generate_text_files_button.clicked.connect(self.generate_text_files)
        database_layout.addWidget(self.generate_text_files_button)

        # Добавляем кнопки для экспорта и импорта базы данных
        self.export_db_button = QPushButton("Export Database")
        self.export_db_button.clicked.connect(self.export_database)
        self.import_db_button = QPushButton("Import Database")
        self.import_db_button.clicked.connect(self.import_database)
        database_layout.addWidget(self.export_db_button)
        database_layout.addWidget(self.import_db_button)

        manual_group.setLayout(manual_layout)
        llm_group.setLayout(llm_layout)
        generate_group.setLayout(generate_layout)
        database_group.setLayout(database_layout)

        button_layout.addWidget(manual_group)
        button_layout.addWidget(llm_group)
        button_layout.addWidget(generate_group)
        button_layout.addWidget(database_group)

        main_layout.addLayout(button_layout)

        # Content area
        content_layout = QHBoxLayout()

        left_layout = QVBoxLayout()
        image_preview_label = QLabel("Image Preview:")
        image_preview_label.setObjectName("section_title")
        left_layout.addWidget(image_preview_label)

        # Добавляем новый QLabel для отображения имени файла
        self.file_name_label = QLabel()
        self.file_name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.file_name_label.setStyleSheet("font-weight: bold;")
        left_layout.addWidget(self.file_name_label)

        self.image_label = DragDropLabel(self)
        left_layout.addWidget(self.image_label)

        # Добавляем кнопку для очистки предпросмотра в layout
        preview_controls = QHBoxLayout()
        preview_controls.addWidget(self.clear_preview_button)
        left_layout.addLayout(preview_controls)

        image_annotation_label = QLabel("Image Annotation")
        image_annotation_label.setObjectName("section_title")
        left_layout.addWidget(image_annotation_label)

        self.annotation_text = QTextEdit()
        left_layout.addWidget(self.annotation_text)

        approve_save_layout = QHBoxLayout()
        self.approve_button = QPushButton("Approve")
        self.approve_button.clicked.connect(self.approve_annotation)
        approve_save_layout.addWidget(self.approve_button)

        self.approve_all_button = QPushButton("Approve All")
        self.approve_all_button.clicked.connect(self.approve_all_annotations)
        approve_save_layout.addWidget(self.approve_all_button)

        self.not_approve_button = QPushButton("Not Approved")
        self.not_approve_button.clicked.connect(self.not_approve_annotation)
        approve_save_layout.addWidget(self.not_approve_button)

        self.save_changes_button = QPushButton("Save")
        self.save_changes_button.clicked.connect(self.save_changes)
        approve_save_layout.addWidget(self.save_changes_button)

        left_layout.addLayout(approve_save_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        left_layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("In progress...")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_label.setVisible(False)
        left_layout.addWidget(self.progress_label)

        content_layout.addLayout(left_layout, 2)

        right_layout = QVBoxLayout()
        self.annotation_list = QListWidget()
        self.annotation_list.itemClicked.connect(self.load_selected_annotation)
        right_layout.addWidget(QLabel("Saved Annotations:"))
        right_layout.addWidget(self.annotation_list)

        content_layout.addLayout(right_layout, 1)

        main_layout.addLayout(content_layout)

        self.load_annotations()

        self.set_dark_theme()

    def set_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QGroupBox {
                border: 1px solid #555555;
                margin-top: 0.5em;
                padding-top: 0.5em;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
            }
            QListWidget, QTextEdit {
                background-color: #333333;
                color: #ffffff;
                border: 1px solid #555555;
            }
            QListWidget::item:selected {
                background-color: #4a4a4a;
            }
            QPushButton {
                background-color: #3a3a3a;
                color: #ffffff;
                border: 1px solid #555555;
                padding: 5px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QProgressBar {
                border: 1px solid #555555;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #3a3a3a;
            }
            QLabel#section_title {
                color: #ffffff;
                font-size: 16px;
                font-weight: bold;
                margin-top: 10px;
                margin-bottom: 5px;
            }
        """)
        self.approve_button.setObjectName("approve_button")
        self.not_approve_button.setObjectName("not_approve_button")
        self.save_changes_button.setObjectName("save_changes_button")

    def approve_all_annotations(self):
        reply = QMessageBox.question(
            self, 'Approve All',
            "Are you sure you want to approve all annotations?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.db_manager.approve_all_annotations()
                self.load_annotations()  # Обновляем список аннотаций
                QMessageBox.information(self, "Success", "All annotations have been approved!")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to approve all annotations: {str(e)}")

    def load_image(self, file_path):
        if file_path and os.path.exists(file_path):
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                self.image_label.setPixmap(pixmap.scaled(400, 300, Qt.AspectRatioMode.KeepAspectRatio))
                self.current_image = file_path
                self.file_name_label.setText(os.path.basename(file_path))
            else:
                QMessageBox.warning(self, "Error", f"Failed to load image: {file_path}")
        elif file_path:
            QMessageBox.warning(self, "Error", f"File does not exist: {file_path}")

    def load_image_dialog(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Image File", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if file_name:
            self.load_image(file_name)

    def locate_image_manually(self, image_name, annotation, is_approved):
        file_path, _ = QFileDialog.getOpenFileName(self, f"Locate {image_name}", "",
                                                   "Image Files (*.png *.jpg *.jpeg *.bmp)")
        if file_path:
            self.db_manager.update_image_path(image_name, file_path)
            self.current_image = file_path
            self.display_image_and_annotation(file_path, annotation, is_approved)
        else:
            self.display_annotation_without_image(annotation, is_approved)

    def locate_image_manually(self, image_name):
        file_path, _ = QFileDialog.getOpenFileName(self, f"Locate {image_name}", "", "Image Files (*.png *.jpg *.bmp)")
        if file_path:
            # Обновляем путь в базе данных
            self.db_manager.update_image_path(image_name, file_path)
            # Загружаем изображение
            self.load_image(file_path)

    def find_image_path(self, image_name):
        # Пробуем несколько вариантов поиска изображения
        possible_paths = [
            os.path.join(os.path.dirname(__file__), image_name),  # В той же директории, что и приложение
            os.path.join(os.path.expanduser("~"), "Downloads", image_name),  # В папке загрузок
            os.path.join(os.path.expanduser("~"), "Pictures", image_name),  # В папке изображений
        ]

        # Добавим путь из базы данных
        db_path = self.db_manager.get_image_path(image_name)
        if db_path:
            possible_paths.insert(0, db_path)  # Добавляем в начало списка

        for path in possible_paths:
            if os.path.exists(path):
                return path

        return None

    def update_approval_buttons(self, is_approved):
        self.approve_button.setEnabled(not is_approved)
        self.not_approve_button.setEnabled(is_approved)
        self.approve_button.setText("Approved" if is_approved else "Approve")
        self.not_approve_button.setText("Not Approved" if not is_approved else "Mark as Not Approved")

    def generate_text_files(self):
        approved_annotations = self.db_manager.get_approved_annotations()
        if not approved_annotations:
            QMessageBox.information(self, "Info", "No approved annotations found.")
            return

        success_count = 0
        for image_path, annotation in approved_annotations:
            try:
                text_file_path = os.path.splitext(image_path)[0] + '.txt'
                with open(text_file_path, 'w', encoding='utf-8') as f:
                    f.write(annotation)
                success_count += 1
            except Exception as e:
                print(f"Error creating text file for {image_path}: {str(e)}")

        QMessageBox.information(self, "Success", f"Created {success_count} text files for approved annotations.")

    def approve_annotation(self):
        if hasattr(self, 'current_image'):
            self.db_manager.update_annotation_status(self.current_image, True)
            self.load_annotations()
            self.update_approval_buttons(True)
            QMessageBox.information(self, "Success", "Annotation approved successfully!")
        else:
            QMessageBox.warning(self, "Error", "Please load an image first.")

    def update_approval_buttons(self, is_approved):
        self.approve_button.setEnabled(not is_approved)
        self.not_approve_button.setEnabled(is_approved)
        self.approve_button.setText("Approved" if is_approved else "Approve")
        self.not_approve_button.setText("Not Approved" if not is_approved else "Mark as Not Approved")

    def not_approve_annotation(self):
        if hasattr(self, 'current_image'):
            self.db_manager.update_annotation_status(self.current_image, False)
            self.load_annotations()
            self.update_approval_buttons(False)
            QMessageBox.information(self, "Success", "Annotation marked as not approved!")
        else:
            QMessageBox.warning(self, "Error", "Please load an image first.")

    def load_annotations(self):
        self.annotation_list.clear()
        annotations = self.db_manager.get_all_annotations()
        for row in annotations:
            image_path, annotation, is_new, is_approved = row
            item = QListWidgetItem(os.path.basename(image_path))
            if is_approved:
                item.setBackground(QColor(0, 100, 0))
                item.setForeground(QColor(255, 255, 255))
            elif is_new:
                item.setBackground(QColor(100, 100, 0))
                item.setForeground(QColor(255, 255, 255))
            else:
                item.setBackground(QColor(40, 40, 40))
                item.setForeground(QColor(200, 200, 200))

            status = " [Approved]" if is_approved else " [Not Approved]" if not is_new else " [New]"
            item.setText(os.path.basename(image_path) + status)

            self.annotation_list.addItem(item)

    def load_selected_annotation(self, item):
        image_name = item.text().split(" [")[0]  # Получаем имя файла без статуса
        result = self.db_manager.get_annotation_by_filename(image_name)
        if result:
            annotation, is_approved, image_path = result
            if os.path.exists(image_path):
                self.load_image(image_path)
                self.annotation_text.setText(annotation)
                self.update_approval_buttons(is_approved)
            else:
                QMessageBox.warning(self, "Error", f"Image file not found: {image_path}")
        else:
            QMessageBox.warning(self, "Error", f"No annotation found for image: {image_name}")

    def display_image_and_annotation(self, image_path, annotation, is_approved):
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            self.image_label.setPixmap(pixmap.scaled(400, 300, Qt.AspectRatioMode.KeepAspectRatio))
            self.file_name_label.setText(os.path.basename(image_path))  # Обновляем отображение имени файла
            self.annotation_text.setText(annotation)
            self.update_approval_buttons(is_approved)
        else:
            QMessageBox.warning(self, "Error", f"Failed to load image: {image_path}")

    def clear_preview(self):
        self.clear_image_preview()
        self.annotation_text.clear()
        self.current_image = None
        self.update_approval_buttons(False)

    def clear_image_preview(self):
        self.image_label.clear()
        self.image_label.setText("\n\n Drag & Drop Image or Folder Here \n\n")
        self.file_name_label.setText("")

    def display_annotation_without_image(self, annotation, is_approved):
        self.clear_image_preview()
        self.annotation_text.setText(annotation)
        self.update_approval_buttons(is_approved)

    def save_changes(self):
        if hasattr(self, 'current_image'):
            new_annotation = self.annotation_text.toPlainText()
            success = self.db_manager.update_annotation(self.current_image, new_annotation)
            if success:
                self.load_annotations()
                QMessageBox.information(self, "Success", "Changes saved successfully!")
            else:
                QMessageBox.warning(self, "Error", "Failed to save changes. Please try again.")
        else:
            QMessageBox.warning(self, "Error", "Please load an image first.")

    def save_annotation(self):
        if hasattr(self, 'current_image'):
            annotation = self.annotation_text.toPlainText()
            success = self.db_manager.insert_or_update_annotation(self.current_image, annotation)
            if success:
                self.load_annotations()
                QMessageBox.information(self, "Success", "Annotation saved successfully!")
            else:
                QMessageBox.warning(self, "Error", "Failed to save annotation. Please try again.")
        else:
            QMessageBox.warning(self, "Error", "Please load an image first.")

    def load_existing_annotation(self):
        if hasattr(self, 'current_image'):
            result = self.db_manager.get_annotation(self.current_image)
            if result:
                annotation, is_approved = result
                self.annotation_text.setText(annotation)
                self.update_approval_buttons(is_approved)
            else:
                self.annotation_text.clear()
                self.update_approval_buttons(False)

    def auto_annotate(self):
        if hasattr(self, 'current_image'):
            prompt_dialog = PromptDialog(self)
            if prompt_dialog.exec():
                prompt = prompt_dialog.get_prompt()
                if not prompt:
                    prompt = DEFAULT_PROMPT

                model = self.model_combo.currentText()

                self.progress_bar.setVisible(True)
                self.progress_label.setVisible(True)
                self.progress_bar.setRange(0, 0)  # Бесконечный прогресс-бар
                self.progress_label.setText("Generating annotation...")
                self.auto_annotate_button.setEnabled(False)

                self.annotation_thread = SingleAnnotationThread(self.annotation_manager, self.current_image, prompt,
                                                                model)
                self.annotation_thread.finished.connect(self.annotation_finished)
                self.annotation_thread.error.connect(self.annotation_error)
                self.annotation_thread.start()
        else:
            QMessageBox.warning(self, "Error", "Please load an image first.")

    def annotation_finished(self, annotation):
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.auto_annotate_button.setEnabled(True)
        self.annotation_text.setText(annotation)
        self.save_annotation()
        QMessageBox.information(self, "Success", "Auto-annotation completed!")

    def annotation_error(self, error_message):
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.auto_annotate_button.setEnabled(True)
        QMessageBox.warning(self, "Error", f"An error occurred during auto-annotation: {error_message}")

    def process_dropped_folder(self, folder_path):
        response = QMessageBox.question(self, "Process Folder",
                                        f"Do you want to annotate all images in the folder:\n{folder_path}?",
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if response == QMessageBox.StandardButton.Yes:
            self.annotate_folder(folder_path)
        else:
            QMessageBox.information(self, "Cancelled", "Folder annotation cancelled.")

    def annotate_folder(self, folder_path=None):
        if not folder_path:
            folder_path = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder_path:
            prompt_dialog = PromptDialog(self)
            if prompt_dialog.exec():
                prompt = prompt_dialog.get_prompt()
                if not prompt:
                    prompt = DEFAULT_PROMPT

                self.progress_bar.setVisible(True)
                self.progress_label.setVisible(True)
                self.folder_annotate_button.setEnabled(False)
                self.progress_bar.setValue(0)
                self.progress_label.setText("Preparing to annotate...")

                self.annotation_thread = AnnotationThread(
                    folder_path,
                    prompt,
                    self.model_combo.currentText(),
                    self.db_manager,
                    self.annotation_manager
                )
                self.annotation_thread.progress.connect(self.update_progress)
                self.annotation_thread.finished.connect(self.folder_annotation_finished)
                self.annotation_thread.error.connect(self.folder_annotation_error)
                self.annotation_thread.start()

    def update_progress(self, current, total, percentage):
        self.progress_bar.setValue(percentage)
        self.progress_label.setText(f"Annotating image {current} of {total}")

    def folder_annotation_finished(self):
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.folder_annotate_button.setEnabled(True)
        self.load_annotations()
        QMessageBox.information(self, "Success", "Folder annotation completed!")

    def folder_annotation_error(self, error_message):
        print(f"Annotation error: {error_message}")  # Для отладки
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.folder_annotate_button.setEnabled(True)
        QMessageBox.warning(self, "Error", error_message)

    def clear_database(self):
        reply = QMessageBox.question(self, 'Clear Database',
                                     "Are you sure you want to clear all annotations from the database?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            self.db_manager.clear_database()
            self.load_annotations()
            self.annotation_text.clear()
            if hasattr(self, 'current_image'):
                del self.current_image
            self.image_label.clear()
            QMessageBox.information(self, "Success", "Database cleared successfully!")

    def export_database(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Database", "", "JSON Files (*.json)")
        if file_path:
            try:
                data = self.db_manager.get_all_annotations()
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump([list(item) for item in data], f, ensure_ascii=False, indent=4)
                QMessageBox.information(self, "Success", "Database exported successfully!")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to export database: {str(e)}")

    def import_database(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Import Database", "", "JSON Files (*.json)")
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.db_manager.import_annotations(data)
                self.load_annotations()  # Обновляем список аннотаций в интерфейсе
                QMessageBox.information(self, "Success", "Database imported successfully!")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to import database: {str(e)}")

    def delete_annotation(self):
        if hasattr(self, 'current_image'):
            reply = QMessageBox.question(self, 'Delete Annotation',
                                         "Are you sure you want to delete this annotation?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.No)

            if reply == QMessageBox.StandardButton.Yes:
                self.db_manager.delete_annotation(self.current_image)
                self.load_annotations()
                self.annotation_text.clear()
                QMessageBox.information(self, "Success", "Annotation deleted successfully!")
        else:
            QMessageBox.warning(self, "Error", "Please load an image first.")

    def update_progress(self, current, total, percentage):
        self.progress_bar.setValue(percentage)
        self.progress_label.setText(f"In progress {current}/{total}")
        if not self.progress_label.isVisible():
            self.progress_label.setVisible(True)
        if current == total:
            self.progress_label.setVisible(False)

    def open_generation_settings(self):
        dialog = GenerationSettingsDialog(self.generation_settings, self)
        if dialog.exec():
            self.generation_settings = dialog.get_settings()
            save_generation_settings(self.generation_settings)
            self.comfy_client.set_server(self.generation_settings.get("server", ""))

    def generate_image(self):
        prompt = self.annotation_text.toPlainText().strip()
        if not prompt:
            QMessageBox.warning(self, "Error", "No annotation text to generate.")
            return

        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.progress_label.setText("Generating image...")
        self.generate_button.setEnabled(False)

        self.gen_thread = GenerateImageThread(self.comfy_client, prompt, self.generation_settings)
        self.gen_thread.finished.connect(self.show_generated_image)
        self.gen_thread.error.connect(self.generate_error)
        self.gen_thread.start()

    def show_generated_image(self, path: str):
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.generate_button.setEnabled(True)
        dlg = QDialog(self)
        dlg.setWindowTitle("Generated Image")
        layout = QVBoxLayout(dlg)
        label = QLabel()
        pix = QPixmap(path)
        label.setPixmap(pix.scaled(512, 512, Qt.AspectRatioMode.KeepAspectRatio))
        layout.addWidget(label)
        dlg.exec()

    def generate_error(self, msg: str):
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.generate_button.setEnabled(True)
        QMessageBox.warning(self, "Error", f"Failed to generate image: {msg}")

