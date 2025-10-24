import sys
import json
import os
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QCheckBox,
    QScrollArea, QFrame, QDialog, QDialogButtonBox,
    QComboBox, QDateTimeEdit, QCalendarWidget,
    QTimeEdit, QMessageBox, QSystemTrayIcon, QMenu, QDateEdit
)
from PySide6.QtCore import QTimer, QTime, QDate, Qt, QPoint, QDateTime, QUrl, QEasingCurve, Property
from PySide6.QtGui import QFont, QIcon, QColor, QPixmap, QPainter, QAction, QPalette
from PySide6.QtMultimedia import QSoundEffect

# --------------------------
# Alarm Notification widget
# --------------------------
class AlarmNotification(QWidget):
    def __init__(self, alarm_data, parent=None):
        super().__init__(parent)
        self.alarm_data = alarm_data
        # Frameless, always on top, tool (no taskbar)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(380, 170)

        # Posicionar en la esquina inferior derecha
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        self.move(screen_geometry.width() - self.width() - 20,
                  screen_geometry.height() - self.height() - 60)

        self.setup_ui()

        # Sonido de alarma
        self.sound_effect = QSoundEffect()
        self.sound_path = self.get_alarm_sound()
        self.sound_timer = None

        if self.sound_path and os.path.exists(self.sound_path):
            try:
                self.sound_effect.setSource(QUrl.fromLocalFile(self.sound_path))
                self.sound_effect.setVolume(0.8)
                # Timer para repetir sonido cada 2s
                self.sound_timer = QTimer(self)
                self.sound_timer.timeout.connect(self.play_alarm_sound)
                self.sound_timer.start(2000)
                self.play_alarm_sound()
                print(f"🔊 Reproduciendo sonido: {self.sound_path}")
            except Exception as e:
                print("⚠️ Error inicializando sonido:", e)
        else:
            print("⚠️ No se encontró archivo de sonido de alarma")

        # Auto-cerrar después de 2 minutos
        self.auto_close_timer = QTimer(self)
        self.auto_close_timer.timeout.connect(self.auto_close)
        self.auto_close_timer.start(120000)

        # Efecto simple: "pulse" visual (cambia la opacidad de un overlay)
        self.pulse_timer = QTimer(self)
        self.pulse_value = 0
        self.pulse_direction = 1
        self.pulse_timer.timeout.connect(self._pulse_step)
        self.pulse_timer.start(120)  # cada 120 ms

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # Marco principal con estilo unificado
        self.background_frame = QFrame()
        self.background_frame.setObjectName("alarm_background")
        
        # Color de fondo basado en prioridad
        color = self.alarm_data.get("color", "green")
        bg_color = self._get_background_color(color)
        
        self.background_frame.setStyleSheet(f"""
            QFrame#alarm_background {{
                background: {bg_color};
                border-radius: 12px;
                border: 1px solid rgba(255,255,255,0.06);
            }}
        """)
        frame_layout = QVBoxLayout(self.background_frame)
        frame_layout.setContentsMargins(14, 12, 14, 12)
        frame_layout.setSpacing(8)

        # Header: icono y title + close
        header = QHBoxLayout()
        icon_label = QLabel()
        icon_label.setText("⏰")
        icon_label.setStyleSheet("font-size: 20px;")
        header.addWidget(icon_label)

        title_label = QLabel("Recordatorio")
        title_label.setStyleSheet("font-size:16px; font-weight:600; color:#FFD966;")
        header.addWidget(title_label)
        header.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setToolTip("Cerrar")
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #ddd;
                border: none;
                font-size: 14px;
            }
            QPushButton:hover { color: white; background: rgba(255,255,255,0.04); border-radius:6px; }
        """)
        close_btn.clicked.connect(self.close_alarm)
        header.addWidget(close_btn)
        frame_layout.addLayout(header)

        # Texto de la tarea en caja destacada
        self.task_label = QLabel(self.alarm_data.get("text", "Tarea"))
        self.task_label.setWordWrap(True)
        self.task_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                padding: 8px;
                border-radius: 8px;
                background: rgba(255,255,255,0.03);
                color: #ffffff;
            }
        """)
        frame_layout.addWidget(self.task_label)

        # Info de fecha/hora y prioridad
        bottom_row = QHBoxLayout()
        alarm_time = QDateTime.fromString(self.alarm_data.get("reminder_time", ""), Qt.ISODate)
        if not alarm_time.isValid():
            # intenta parsear si viene como QDateTime str con otro formato
            try:
                alarm_time = QDateTime.fromString(self.alarm_data.get("reminder_time", ""), "dd/MM/yyyy hh:mm")
            except:
                alarm_time = QDateTime.currentDateTime()

        date_label = QLabel(f"📅 {alarm_time.toString('dd/MM/yyyy')}")
        time_label = QLabel(f"🕒 {alarm_time.toString('HH:mm')}")
        for lbl in (date_label, time_label):
            lbl.setStyleSheet("color: #BFC7C9; font-size: 11px;")
        bottom_row.addWidget(date_label)
        bottom_row.addWidget(time_label)
        bottom_row.addStretch()

        # Prioridad
        color = self.alarm_data.get("color", "green")
        color_name_text = self.alarm_data.get("color_name", "🟢 Normal")
        priority_label = QLabel(f"{color_name_text}")
        priority_label.setStyleSheet(self._priority_style(color))
        bottom_row.addWidget(priority_label)
        frame_layout.addLayout(bottom_row)

        # Separador
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background: rgba(255,255,255,0.03); max-height:1px;")
        frame_layout.addWidget(sep)

        # Botones: Posponer y Completar
        btn_row = QHBoxLayout()
        snooze_btn = QPushButton("Posponer 5 min")
        snooze_btn.setCursor(Qt.PointingHandCursor)
        snooze_btn.setFixedHeight(30)
        snooze_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #ddd;
                border: 1px solid rgba(255,255,255,0.04);
                padding: 6px 12px;
                border-radius: 6px;
            }
            QPushButton:hover { background: rgba(255,255,255,0.02); }
        """)
        snooze_btn.clicked.connect(self.snooze_alarm)

        complete_btn = QPushButton("Completar")
        complete_btn.setCursor(Qt.PointingHandCursor)
        complete_btn.setFixedHeight(30)
        complete_btn.setStyleSheet("""
            QPushButton {
                background: #28a745;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 6px;
                font-weight: 600;
            }
            QPushButton:hover { background: #23903f; }
        """)
        complete_btn.clicked.connect(self.complete_alarm)

        btn_row.addWidget(snooze_btn)
        btn_row.addStretch()
        btn_row.addWidget(complete_btn)
        frame_layout.addLayout(btn_row)

        layout.addWidget(self.background_frame)
        self.setLayout(layout)

    def _get_background_color(self, color):
        """Devuelve el color de fondo basado en la prioridad"""
        colors = {
            "red": "qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #3a2326, stop:1 #2a1518)",
            "yellow": "qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #3a3a26, stop:1 #2a2a18)",
            "blue": "qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #232a3a, stop:1 #151c2a)",
            "green": "qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #2a3a26, stop:1 #1a2a18)",
        }
        return colors.get(color, colors["green"])

    def _priority_style(self, color):
        styles = {
            "red": "color: #FFB6B6; font-size: 12px; font-weight:600;",
            "yellow": "color: #FFD966; font-size: 12px; font-weight:600;",
            "blue": "color: #A6D8FF; font-size: 12px; font-weight:600;",
            "green": "color: #A9F38B; font-size: 12px; font-weight:600;",
        }
        return styles.get(color, styles["green"])

    def get_alarm_sound(self):
        # Primero busca en recursos embebidos
        if hasattr(sys, '_MEIPASS'):
            # Modo compilado
            base_path = Path(sys._MEIPASS)
            embedded_path = base_path / "alarm.wav"
            if embedded_path.exists():
                return str(embedded_path)
        
        # Luego busca en rutas normales
        possible_paths = [
            Path("alarm.wav"),
            Path("sound.wav"),
            Path.home() / "Documents" / "ProductivityApp" / "alarm.wav",
            Path.home() / "Desktop" / "alarm.wav",
            Path.home() / "OneDrive" / "Escritorio" / "alarm.wav",
        ]
        for p in possible_paths:
            if p.exists():
                print("✅ Encontrado archivo de sonido:", p)
                return str(p)
        print("❌ No se encontró ningún archivo de sonido")
        return ""

    def play_alarm_sound(self):
        try:
            if self.sound_effect:
                # Si ya está sonando, reiniciarlo para que se oiga limpio
                self.sound_effect.stop()
                self.sound_effect.play()
        except Exception as e:
            print("Error reproduciendo sonido:", e)

    def snooze_alarm(self):
        new_time = QDateTime.currentDateTime().addSecs(300)  # 5 minutos
        # enviar al padre (ProductivityWidget) en formato ISO string
        alarm_data = {
            "text": self.alarm_data.get("text"),
            "color": self.alarm_data.get("color", "green"),
            "color_name": self.alarm_data.get("color_name", "🟢 Normal"),
            "reminder_time": new_time.toString(Qt.ISODate),
            "created": QDateTime.currentDateTime().toString(Qt.ISODate)
        }
        if self.parent() is not None and hasattr(self.parent(), "save_snoozed_alarm"):
            self.parent().save_snoozed_alarm(alarm_data)
        self.close_alarm()

    def complete_alarm(self):
        if self.parent() is not None and hasattr(self.parent(), "complete_alarm_task"):
            self.parent().complete_alarm_task(self.alarm_data)
        self.close_alarm()

    def close_alarm(self):
        # detener timers y sonidos
        if hasattr(self, "sound_timer") and self.sound_timer:
            self.sound_timer.stop()
        if hasattr(self, "sound_effect") and self.sound_effect:
            try:
                self.sound_effect.stop()
            except:
                pass
        if hasattr(self, "auto_close_timer") and self.auto_close_timer:
            self.auto_close_timer.stop()
        if hasattr(self, "pulse_timer") and self.pulse_timer:
            self.pulse_timer.stop()
        self.close()

    def auto_close(self):
        self.close_alarm()

    def _pulse_step(self):
        # simple pulso para dar vida a la notificación (no usa animaciones avanzadas)
        self.pulse_value += 0.08 * self.pulse_direction
        if self.pulse_value > 1.0:
            self.pulse_value = 1.0
            self.pulse_direction = -1
        elif self.pulse_value < 0.0:
            self.pulse_value = 0.0
            self.pulse_direction = 1
        # Cambiar sutilmente el borde para que "respire"
        alpha = 40 + int(40 * self.pulse_value)
        color = self.alarm_data.get("color", "green")
        bg_color = self._get_background_color(color)
        self.background_frame.setStyleSheet(f"""
            QFrame#alarm_background {{
                background: {bg_color};
                border-radius: 12px;
                border: 1px solid rgba(255,255,255,{alpha/255:.2f});
                box-shadow: 0 6px 18px rgba(0,0,0,0.45);
            }}
        """)

# --------------------------
# Task Dialog
# --------------------------
class TaskDialog(QDialog):
    def __init__(self, parent=None, task_text=""):
        super().__init__(parent)
        self.setWindowTitle("Configurar Tarea")
        self.setModal(True)
        self.setFixedSize(420, 420)
        
        # Aplicar estilo unificado
        self.setStyleSheet("""
            TaskDialog {
                background-color: #1e2021;
                color: white;
            }
            QLabel { 
                color: white; 
                font-size: 13px;
            }
            QLineEdit { 
                background-color: #2a2d2e; 
                border: 1px solid #444; 
                border-radius: 6px; 
                padding: 8px; 
                font-size: 13px; 
                color: white; 
            }
            QComboBox { 
                background-color: #2a2d2e; 
                border: 1px solid #444; 
                border-radius: 6px; 
                padding: 8px; 
                color: white; 
                min-height: 20px;
                font-size: 13px;
            }
            QComboBox::drop-down {
                border: none;
                width: 25px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #888;
                width: 0px;
                height: 0px;
            }
            QComboBox QAbstractItemView {
                background-color: #2a2d2e;
                border: 1px solid #444;
                color: white;
                selection-background-color: #0078D7;
                outline: none;
                padding: 4px;
            }
            QComboBox QAbstractItemView::item {
                padding: 6px 8px;
                border-radius: 3px;
            }
            QDateEdit, QTimeEdit { 
                background-color: #2a2d2e; 
                border: 1px solid #444; 
                border-radius: 6px; 
                padding: 6px; 
                color: white; 
            }
            QDateEdit::drop-down, QTimeEdit::drop-down {
                border: none;
                width: 20px;
            }
            QCheckBox { 
                color: white; 
                font-size: 13px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 3px;
                border: 1px solid #555;
                background: #2a2d2e;
            }
            QCheckBox::indicator:checked {
                background: #0078D7;
                border: 1px solid #0078D7;
            }
            QPushButton {
                background-color: #0078D7;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 600;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #0099FF;
            }
            QPushButton:pressed {
                background-color: #0066B4;
            }
            QDialogButtonBox QPushButton[text="Cancel"] {
                background-color: #6c757d;
            }
            QDialogButtonBox QPushButton[text="Cancel"]:hover {
                background-color: #5a6268;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # Texto de la tarea
        layout.addWidget(QLabel("Tarea:"))
        self.task_input = QLineEdit(task_text)
        self.task_input.setPlaceholderText("Descripción de la tarea...")
        layout.addWidget(self.task_input)

        # Selector de color - ARREGLADO
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("Prioridad:"))
        color_layout.addStretch()

        self.color_combo = QComboBox()
        self.color_combo.addItem("🟢 Normal", "green")
        self.color_combo.addItem("🟡 Media", "yellow")
        self.color_combo.addItem("🔴 Alta", "red")
        self.color_combo.addItem("🔵 Informativa", "blue")
        self.color_combo.setFixedWidth(200)  # Ancho fijo para evitar cortes
        color_layout.addWidget(self.color_combo)
        layout.addLayout(color_layout)

        # Recordatorio
        self.reminder_check = QCheckBox("Agregar recordatorio")
        self.reminder_check.toggled.connect(self.toggle_reminder)
        layout.addWidget(self.reminder_check)

        reminder_layout = QVBoxLayout()
        reminder_layout.setContentsMargins(20, 10, 0, 10)
        reminder_layout.setSpacing(8)

        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("Fecha:"))
        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setEnabled(False)
        self.date_edit.setDisplayFormat("dd/MM/yyyy")
        date_layout.addWidget(self.date_edit)
        date_layout.addStretch()
        reminder_layout.addLayout(date_layout)

        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("Hora:"))
        self.time_edit = QTimeEdit()
        self.time_edit.setTime(QTime.currentTime().addSecs(3600))
        self.time_edit.setEnabled(False)
        self.time_edit.setDisplayFormat("hh:mm")
        time_layout.addWidget(self.time_edit)
        time_layout.addStretch()
        reminder_layout.addLayout(time_layout)

        layout.addLayout(reminder_layout)

        info_label = QLabel("💡 La alarma sonará en el momento programado")
        info_label.setStyleSheet("color: #888; font-size: 11px; font-style: italic;")
        layout.addWidget(info_label)

        layout.addStretch()

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def toggle_reminder(self, checked):
        self.date_edit.setEnabled(checked)
        self.time_edit.setEnabled(checked)

    def get_task_data(self):
        reminder_time = None
        if self.reminder_check.isChecked():
            reminder_time = QDateTime(self.date_edit.date(), self.time_edit.time())
        return {
            "text": self.task_input.text().strip(),
            "color": self.color_combo.currentData(),
            "color_name": self.color_combo.currentText(),
            "has_reminder": self.reminder_check.isChecked(),
            "reminder_time": reminder_time  # QDateTime or None
        }

# --------------------------
# Productivity main widget
# --------------------------
class ProductivityWidget(QWidget):
    def __init__(self):
        super().__init__()

        # Ventana principal flotante
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.is_expanded = False
        self.drag_pos = QPoint()

        # Alarmas pendientes
        self.pending_alarms = []
        self.alarm_timer = QTimer(self)
        self.alarm_timer.timeout.connect(self.check_alarms)
        self.alarm_timer.start(1000)

        # Carpetas y archivos
        documents_dir = Path.home() / "Documents" / "ProductivityApp"
        documents_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = documents_dir / "historial.json"
        self.alarms_file = documents_dir / "alarms.json"

        # Widgets
        self.date_label = QLabel()
        self.date_label.setAlignment(Qt.AlignCenter)
        self.date_label.setObjectName("date_label")

        self.time_label = QLabel()
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setObjectName("time_label")

        # Checklist
        self.checklist_container = QWidget()
        self.input_layout = QHBoxLayout()
        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText("Nueva tarea pendiente...")

        self.quick_add_button = QPushButton("+")
        self.quick_add_button.setFixedSize(30, 30)
        self.quick_add_button.setToolTip("Agregar tarea rápida")

        self.detailed_add_button = QPushButton("⋯")
        self.detailed_add_button.setFixedSize(30, 30)
        self.detailed_add_button.setToolTip("Agregar tarea con detalles")

        self.input_layout.addWidget(self.task_input)
        self.input_layout.addWidget(self.quick_add_button)
        self.input_layout.addWidget(self.detailed_add_button)

        
        self.scroll_area = QScrollArea()
        self.scroll_widget = QWidget()
        self.scroll_widget.setObjectName("scroll_widget")
        self.task_list_layout = QVBoxLayout()
        self.task_list_layout.setAlignment(Qt.AlignTop)
        self.scroll_widget.setLayout(self.task_list_layout)
        self.scroll_area.setWidget(self.scroll_widget)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollArea #scroll_widget {
                background: rgba(255,255,255,0.02);
                border-radius: 6px;
            }
        """)
        self.checklist_layout = QVBoxLayout()
        self.checklist_layout.addLayout(self.input_layout)
        self.checklist_layout.addWidget(self.scroll_area)
        self.checklist_container.setLayout(self.checklist_layout)
        self.checklist_container.setVisible(False)

        # Historial
        self.history_toggle_button = QPushButton("Historial (...")
        self.history_toggle_button.setObjectName("history_button")
        self.history_toggle_button.setCheckable(True)
        self.history_toggle_button.setVisible(False)
        self.history_container = QWidget()
        self.history_scroll_area = QScrollArea()
        self.history_scroll_widget = QWidget()
        self.history_scroll_widget.setObjectName("history_scroll_widget")
        self.history_list_layout = QVBoxLayout()
        self.history_list_layout.setAlignment(Qt.AlignTop)
        self.history_scroll_widget.setLayout(self.history_list_layout)
        self.history_scroll_area.setWidget(self.history_scroll_widget)
        self.history_scroll_area.setWidgetResizable(True)
        self.history_scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollArea #history_scroll_widget {
                background: rgba(255,255,255,0.02);
                border-radius: 6px;
            }
        """)
        self.history_layout = QVBoxLayout()
        self.history_layout.addWidget(self.history_scroll_area)
        self.history_container.setLayout(self.history_layout)
        self.history_container.setVisible(False)

        # Fondo con estilo unificado
        self.background_frame = QFrame()
        self.background_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 #2a2d2e, stop:1 #1e2021);
                border-radius: 12px;
                border: 1px solid rgba(255,255,255,0.06);
            }
        """)
        frame_layout = QVBoxLayout(self.background_frame)
        frame_layout.setContentsMargins(12, 12, 12, 12)
        frame_layout.setSpacing(8)

        frame_layout.addWidget(self.date_label)
        frame_layout.addWidget(self.time_label)
        frame_layout.addWidget(self.checklist_container)
        frame_layout.addWidget(self.history_toggle_button)
        frame_layout.addWidget(self.history_container)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.background_frame)

        # Estilos unificados
        self.setStyleSheet("""
            QLabel { color: white; }
            #date_label { 
                font-size: 13px; 
                color: #CCCCCC; 
                padding-top: 5px; 
            }
            #time_label { 
                font-size: 30px; 
                font-weight: 600; 
                padding-bottom: 5px; 
            }

            QLineEdit { 
                background-color: #2a2d2e; 
                border: 1px solid #444; 
                border-radius: 6px; 
                padding: 8px; 
                font-size: 13px; 
                color: white; 
            }
            QPushButton { 
                background-color: #0078D7; 
                color: white; 
                font-size: 14px; 
                font-weight: 600; 
                border-radius: 6px; 
                min-width: 26px; 
                min-height:26px; 
                border: none;
            }
            QPushButton:hover { 
                background-color: #0099FF; 
            }
            QPushButton:pressed {
                background-color: #0066B4;
            }

            QScrollArea { 
                border: none; 
                background: transparent; 
            }
            
            /* Estilos para checkboxes con colores */
            QCheckBox { 
                font-size: 13px; 
                padding: 8px 6px; 
                border-radius: 4px; 
                margin: 2px; 
                color: white;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 3px;
                border: 1px solid #555;
                background: #2a2d2e;
            }
            QCheckBox::indicator:checked {
                background: #28a745;
                border: 1px solid #28a745;
            }
            QCheckBox:checked { 
                text-decoration: line-through; 
                color: #888;
            }
            
            /* Colores para tareas normales (checkboxes) */
            QCheckBox.task_red {
                background: rgba(255, 100, 100, 0.15);
                border-left: 3px solid #ff4444;
                color: #ffb4b4;
            }
            QCheckBox.task_yellow {
                background: rgba(255, 255, 100, 0.15);
                border-left: 3px solid #ffff44;
                color: #ffffb4;
            }
            QCheckBox.task_blue {
                background: rgba(100, 100, 255, 0.15);
                border-left: 3px solid #4444ff;
                color: #b4b4ff;
            }
            QCheckBox.task_green {
                background: rgba(100, 255, 100, 0.15);
                border-left: 3px solid #44ff44;
                color: #b4ffb4;
            }

            #history_button { 
                font-size: 12px; 
                font-weight: bold; 
                color: #888; 
                background: transparent; 
                border: none; 
                max-height: 24px; 
                border-radius: 5px; 
                text-align: left; 
                padding: 2px 5px; 
            }
            #history_button:hover { 
                color: white; 
                background-color: rgba(255,255,255,0.05); 
            }
            #history_button:checked { 
                color: white; 
                background-color: rgba(255,255,255,0.08); 
            }

            QLabel#history_item { 
                color: #777; 
                text-decoration: line-through; 
                font-size: 13px; 
                padding: 2px 8px; 
                background: transparent; 
            }
            
            /* Estilos para alertas sin check */
            QLabel.alert_item {
                font-size: 13px;
                padding: 8px 6px;
                border-radius: 4px;
                margin: 2px;
            }
            QLabel.alert_red {
                background: rgba(255, 100, 100, 0.15);
                border-left: 3px solid #ff4444;
                color: #ffb4b4;
            }
            QLabel.alert_yellow {
                background: rgba(255, 255, 100, 0.15);
                border-left: 3px solid #ffff44;
                color: #ffffb4;
            }
            QLabel.alert_blue {
                background: rgba(100, 100, 255, 0.15);
                border-left: 3px solid #4444ff;
                color: #b4b4ff;
            }
            QLabel.alert_green {
                background: rgba(100, 255, 100, 0.15);
                border-left: 3px solid #44ff44;
                color: #b4ffb4;
            }
        """)

        self.scroll_widget.setObjectName("scroll_widget")
        self.history_scroll_widget.setObjectName("history_scroll_widget")

        # Timer de fecha/hora
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_datetime)
        self.timer.start(1000)
        self.update_datetime()

        # Conexiones
        self.quick_add_button.clicked.connect(self.add_quick_task)
        self.detailed_add_button.clicked.connect(self.show_task_dialog)
        self.task_input.returnPressed.connect(self.add_quick_task)
        self.history_toggle_button.clicked.connect(self.toggle_history)

        self.setFixedSize(260, 120)

        # Cargar historial y alarmas
        self.load_history()
        self.load_alarms()

    # Fecha / Hora
    def update_datetime(self):
        current_date = QDate.currentDate().toString("dddd, d 'de' MMMM")
        self.date_label.setText(current_date.capitalize())
        current_time = QTime.currentTime().toString("hh:mm:ss")
        self.time_label.setText(current_time)

    # Tareas
    def add_quick_task(self):
        task_text = self.task_input.text().strip()
        if task_text:
            task_data = {
                "text": task_text,
                "color": "green",
                "color_name": "🟢 Normal",
                "has_reminder": False,
                "reminder_time": None
            }
            self.create_task_widget(task_data)
            self.task_input.clear()
            # opcional: persistir tareas activas si lo deseas

    def show_task_dialog(self):
        task_text = self.task_input.text().strip()
        dialog = TaskDialog(self, task_text)
        if dialog.exec() == QDialog.Accepted:
            task_data = dialog.get_task_data()
            if task_data["text"]:
                # Si reminder_time es QDateTime, convertirlo a QDateTime antes de guardarlo en widget
                self.create_task_widget(task_data)
                self.task_input.clear()

                if task_data["has_reminder"] and task_data["reminder_time"]:
                    # Si es QDateTime, convertir a ISO para guardar en alarms
                    dt = task_data["reminder_time"]
                    if isinstance(dt, QDateTime):
                        task_data["reminder_time"] = dt  # keep as QDateTime for local widget
                    self.schedule_alarm(task_data)

    def create_task_widget(self, task_data):
        # Si tiene recordatorio, crear una alerta (sin checkbox)
        # Si no tiene recordatorio, crear una tarea normal (con checkbox)
        
        if task_data.get("has_reminder"):
            # Crear alerta (sin checkbox)
            alert_widget = QLabel(task_data["text"])
            alert_widget.setWordWrap(True)
            alert_widget.setObjectName(f"alert_{task_data['color']}")
            alert_widget.setProperty("class", "alert_item")
            alert_widget.task_data = task_data
            
            # Tooltip con información de la alarma
            rt = task_data.get("reminder_time")
            if rt:
                if isinstance(rt, QDateTime):
                    r_str = rt.toString("dd/MM/yyyy HH:mm")
                elif isinstance(rt, str):
                    try:
                        dt = QDateTime.fromString(rt, Qt.ISODate)
                        r_str = dt.toString("dd/MM/yyyy HH:mm") if dt.isValid() else rt
                    except:
                        r_str = str(rt)
                else:
                    r_str = str(rt)
                alert_widget.setToolTip(f"Alarma: {r_str}")
            
            self.task_list_layout.addWidget(alert_widget)
        else:
            # Crear tarea normal (con checkbox)
            checkbox = QCheckBox(task_data["text"])
            # Establecer objectName por color para estilos
            checkbox.setObjectName(f"task_{task_data['color']}")
            # Aplicar clase CSS para el color
            checkbox.setProperty("class", f"task_{task_data['color']}")
            # Guardar datos
            checkbox.task_data = task_data

            checkbox.toggled.connect(lambda checked, cb=checkbox: self.complete_task(cb, checked))
            self.task_list_layout.addWidget(checkbox)

        # Reordenar tareas: alertas rojas primero
        self.reorder_tasks()

    def reorder_tasks(self):
        """Reordena las tareas: alertas rojas primero, luego otras alertas, luego tareas normales"""
        # Obtener todos los widgets del layout
        widgets = []
        for i in range(self.task_list_layout.count()):
            item = self.task_list_layout.itemAt(i)
            if item.widget():
                widgets.append(item.widget())
        
        # Remover todos los widgets del layout
        for widget in widgets:
            self.task_list_layout.removeWidget(widget)
        
        # Ordenar widgets: primero alertas rojas, luego otras alertas, luego checkboxes
        def get_widget_priority(widget):
            if isinstance(widget, QLabel) and hasattr(widget, 'task_data'):
                # Es una alerta
                color = widget.task_data.get('color', 'green')
                if color == 'red':
                    return 0  # Máxima prioridad
                else:
                    return 1  # Alta prioridad
            else:
                # Es un checkbox (tarea normal)
                return 2  # Baja prioridad
        
        widgets.sort(key=get_widget_priority)
        
        # Agregar widgets ordenados de vuelta al layout
        for widget in widgets:
            self.task_list_layout.addWidget(widget)

    def complete_task(self, checkbox, checked):
        if checked:
            # Mostrar diálogo de confirmación
            reply = QMessageBox.question(self, 'Confirmar Completado', 
                                        f'¿Terminaste la tarea: "{checkbox.text()}"?', 
                                        QMessageBox.Yes | QMessageBox.No, 
                                        QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                task_data = checkbox.task_data
                current_date = QDate.currentDate().toString("yyyy-MM-dd")
                self.save_task_to_history(current_date, task_data)
                QTimer.singleShot(500, lambda: self.remove_task(checkbox))
            else:
                # Si el usuario dice que no, desmarcar el checkbox
                checkbox.setChecked(False)

    def remove_task(self, checkbox):
        for i in range(self.task_list_layout.count()):
            item = self.task_list_layout.itemAt(i)
            if item.widget() == checkbox:
                checkbox.deleteLater()
                break

    # Alarmas
    def schedule_alarm(self, task_data):
        # Asegura que reminder_time se guarde en ISO string
        rt = task_data.get("reminder_time")
        if isinstance(rt, QDateTime):
            reminder_iso = rt.toString(Qt.ISODate)
        elif isinstance(rt, str):
            reminder_iso = rt
        else:
            reminder_iso = None

        alarm_data = {
            "text": task_data["text"],
            "color": task_data.get("color", "green"),
            "color_name": task_data.get("color_name", "🟢 Normal"),
            "reminder_time": reminder_iso,
            "created": QDateTime.currentDateTime().toString(Qt.ISODate)
        }
        if reminder_iso:
            self.pending_alarms.append(alarm_data)
            self.save_alarms()
            reminder_time = QDateTime.fromString(reminder_iso, Qt.ISODate)
            print(f"Alarma programada: {task_data['text']} para {reminder_time.toString('dd/MM/yyyy hh:mm')}")
        else:
            print("No se pudo programar alarma: reminder_time inválido")

    def check_alarms(self):
        current_datetime = QDateTime.currentDateTime()
        for alarm in list(self.pending_alarms):
            alarm_time = QDateTime.fromString(alarm.get("reminder_time", ""), Qt.ISODate)
            if not alarm_time.isValid():
                continue
            if current_datetime >= alarm_time:
                print(f"🔔 Activando alarma: {alarm['text']}")
                self.show_alarm_notification(alarm)
                try:
                    self.pending_alarms.remove(alarm)
                except ValueError:
                    pass
                break
        # si cambió la cantidad, guardar
        if len(self.pending_alarms) != getattr(self, "prev_alarm_count", 0):
            self.save_alarms()
            self.prev_alarm_count = len(self.pending_alarms)

    def show_alarm_notification(self, alarm):
        try:
            self.alarm_notification = AlarmNotification(alarm, self)
            self.alarm_notification.show()
            print("✅ Notificación de alarma mostrada")
        except Exception as e:
            print("❌ Error mostrando notificación:", e)

    def save_snoozed_alarm(self, alarm_data):
        # Se espera alarm_data.reminder_time en ISO string
        self.pending_alarms.append(alarm_data)
        self.save_alarms()

    def complete_alarm_task(self, alarm_data):
        # Buscar widget correspondiente y eliminarlo
        for i in range(self.task_list_layout.count()):
            item = self.task_list_layout.itemAt(i)
            widget = item.widget()
            if (isinstance(widget, QLabel) and hasattr(widget, "task_data") and
                widget.task_data.get("text") == alarm_data.get("text")):
                widget.deleteLater()
                break
        # Guardar al historial
        current_date = QDate.currentDate().toString("yyyy-MM-dd")
        self.save_task_to_history(current_date, {
            "text": alarm_data.get("text"),
            "color": alarm_data.get("color", "green"),
            "color_name": alarm_data.get("color_name", "🟢 Normal")
        })

    def save_alarms(self):
        try:
            with open(self.alarms_file, "w", encoding="utf-8") as f:
                json.dump(self.pending_alarms, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print("Error guardando alarmas:", e)

    def load_alarms(self):
        if not os.path.exists(self.alarms_file):
            self.pending_alarms = []
            self.prev_alarm_count = 0
            return
        try:
            with open(self.alarms_file, "r", encoding="utf-8") as f:
                self.pending_alarms = json.load(f)
            self.prev_alarm_count = len(self.pending_alarms)
            # Filtrar alarmas pasadas
            current_datetime = QDateTime.currentDateTime()
            self.pending_alarms = [
                alarm for alarm in self.pending_alarms
                if QDateTime.fromString(alarm.get("reminder_time", ""), Qt.ISODate) > current_datetime
            ]
        except Exception as e:
            print("Error cargando alarmas:", e)
            self.pending_alarms = []
            self.prev_alarm_count = 0

    # Historial
    def save_task_to_history(self, date_str, task_data):
        data = {}
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                data = {}
        if date_str not in data:
            data[date_str] = []
        data[date_str].append({
            "text": task_data.get("text"),
            "color": task_data.get("color", "green"),
            "color_name": task_data.get("color_name", "🟢 Normal"),
            "completed": QDateTime.currentDateTime().toString(Qt.ISODate)
        })
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print("Error guardando historial:", e)

    def load_history(self):
        # limpiar
        for i in reversed(range(self.history_list_layout.count())):
            widget = self.history_list_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        if not os.path.exists(self.history_file):
            return
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            return
        for date_str in sorted(data.keys(), reverse=True):
            date_label = QLabel(f"📅 {QDate.fromString(date_str, 'yyyy-MM-dd').toString('d MMMM yyyy')}")
            date_label.setStyleSheet("font-weight: bold; color: #66CCFF; margin-top: 10px;")
            date_label.setCursor(Qt.PointingHandCursor)
            self.history_list_layout.addWidget(date_label)

            tasks_widget = QWidget()
            tasks_layout = QVBoxLayout()
            tasks_layout.setContentsMargins(15, 0, 0, 0)

            for task_data in data[date_str]:
                if isinstance(task_data, str):
                    task_text = task_data
                    color = "green"
                    color_name = "🟢"
                else:
                    task_text = task_data.get("text", "")
                    color = task_data.get("color", "green")
                    color_name = task_data.get("color_name", "🟢")
                t = QLabel(f"{color_name} {task_text}")
                t.setObjectName("history_item")
                if color == "red":
                    t.setStyleSheet("color: #FFB6C1; text-decoration: line-through; font-size: 13px; padding: 2px 8px;")
                elif color == "yellow":
                    t.setStyleSheet("color: #FFFFE0; text-decoration: line-through; font-size: 13px; padding: 2px 8px;")
                elif color == "blue":
                    t.setStyleSheet("color: #ADD8E6; text-decoration: line-through; font-size: 13px; padding: 2px 8px;")
                else:
                    t.setStyleSheet("color: #90EE90; text-decoration: line-through; font-size: 13px; padding: 2px 8px;")
                tasks_layout.addWidget(t)

            tasks_widget.setLayout(tasks_layout)
            tasks_widget.setVisible(False)
            self.history_list_layout.addWidget(tasks_widget)

            def toggle_tasks(event, widget=tasks_widget):
                widget.setVisible(not widget.isVisible())

            date_label.mousePressEvent = lambda e, w=tasks_widget: toggle_tasks(e, w)

    # Interfaz historial
    def toggle_history(self, checked):
        if checked:
            self.history_container.setVisible(True)
            self.setFixedSize(320, 550)
            self.history_toggle_button.setText("Historial )…")
            self.load_history()
        else:
            self.history_container.setVisible(False)
            # si está expandido, dejar tamaño de expanded, si no el pequeño
            if self.is_expanded:
                self.setFixedSize(320, 400)
            else:
                self.setFixedSize(260, 120)
            self.history_toggle_button.setText("Historial (...")

    # Movimiento
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.pos()
            event.accept()

    def mouseDoubleClickEvent(self, event):
        click_pos = event.pos()
        is_on_header = self.date_label.geometry().contains(click_pos) or self.time_label.geometry().contains(click_pos)

        if is_on_header:
            if not self.is_expanded:
                self.is_expanded = True
                self.checklist_container.setVisible(True)
                self.history_toggle_button.setVisible(True)
                self.setFixedSize(320, 400)
            else:
                self.is_expanded = False
                self.checklist_container.setVisible(False)
                self.history_toggle_button.setVisible(False)
                self.history_container.setVisible(False)
                self.history_toggle_button.setChecked(False)
                self.history_toggle_button.setText("Historial (...")
                self.setFixedSize(260, 120)

            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()


# --------------------------
# Ejecutar aplicación
# --------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    font = QFont()
    font.setPointSize(QApplication.font().pointSize())
    app.setFont(font)

    widget = ProductivityWidget()
    widget.show()

    sys.exit(app.exec())