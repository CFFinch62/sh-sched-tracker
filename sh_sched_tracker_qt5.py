import sys
import json
import argparse
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QLabel, QSystemTrayIcon, QMenu, QPushButton, 
                            QTimeEdit, QHBoxLayout, QCheckBox, QMenuBar, QSizePolicy, 
                            QMessageBox, QFileDialog, QSpinBox, QDialog, QTableWidget, 
                            QTableWidgetItem, QComboBox, QHeaderView, QInputDialog, QLineEdit, 
                            QColorDialog, QTextEdit, QAction, QActionGroup)
from PyQt5.QtCore import QTimer, Qt, QTime, QSettings, QPoint, QSize
from PyQt5.QtGui import QIcon, QColor
import os

# Directory constants
ICON_DIR = "icons"
TEST_DIR = "testing"

# Create directories if they don't exist
os.makedirs(ICON_DIR, exist_ok=True)
os.makedirs(TEST_DIR, exist_ok=True)

class ColorSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Color Settings")
        self.setMinimumWidth(400)
        layout = QVBoxLayout(self)
        
        # Create color selection buttons
        self.create_color_button("Window Background", "window_bg_color", layout)
        self.create_color_button("Window Text", "window_text_color", layout)
        self.create_color_button("Message Background", "message_bg_color", layout)
        self.create_color_button("Message Text", "message_text_color", layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        reset_btn = QPushButton("Reset to Default")
        
        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        reset_btn.clicked.connect(self.reset_colors)
        
        button_layout.addWidget(reset_btn)
        button_layout.addStretch()
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        self.apply_dialog_style()
    
    def apply_dialog_style(self):
        # Apply dark theme to dialog
        self.setStyleSheet("""
            QDialog {
                background-color: #000000;
            }
            QLabel {
                color: white;
                font-size: 12px;
            }
            QPushButton {
                background-color: #000066;
                color: white;
                border: 1px solid #0000cc;
                padding: 5px 10px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #000099;
            }
            QWidget {
                background-color: #000000;
                color: white;
            }
        """)
    
    def create_color_button(self, label_text, setting_name, layout):
        container = QWidget()
        h_layout = QHBoxLayout(container)
        
        label = QLabel(label_text)
        label.setStyleSheet("color: white;")  # Ensure label is always visible
        button = QPushButton()
        button.setFixedSize(40, 20)
        
        # Get color from settings or use default
        color = QColor(self.parent.settings.value(setting_name, self.parent.default_colors[setting_name]))
        button.setStyleSheet(f"background-color: {color.name()};")
        
        # Store the setting name with the button
        button.setting_name = setting_name
        button.clicked.connect(lambda: self.choose_color(button))
        
        h_layout.addWidget(label)
        h_layout.addWidget(button)
        layout.addWidget(container)
    
    def choose_color(self, button):
        current_color = QColor(button.palette().button().color())
        color = QColorDialog.getColor(current_color, self)
        
        if color.isValid():
            button.setStyleSheet(f"background-color: {color.name()};")
            # Store the color in parent's current colors
            self.parent.current_colors[button.setting_name] = color.name()
            # Reapply dialog style to ensure labels remain visible
            self.apply_dialog_style()
    
    def reset_colors(self):
        for child in self.findChildren(QPushButton):
            if hasattr(child, 'setting_name'):
                default_color = self.parent.default_colors[child.setting_name]
                child.setStyleSheet(f"background-color: {default_color};")
                self.parent.current_colors[child.setting_name] = default_color
        # Reapply dialog style
        self.apply_dialog_style()

    def showEvent(self, event):
        super().showEvent(event)
        # Ensure dialog style is applied whenever the dialog is shown
        self.apply_dialog_style()

class ScheduleWindow(QMainWindow):
    def __init__(self, enable_test_mode=False):
        super().__init__()
        self.setWindowTitle("Southampton Schedule Tracker")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.MSWindowsFixedSizeDialogHint)
        
        # Define window sizes
        self.window_sizes = {
            'small': QSize(355, 230),
            'medium': QSize(445, 355),
            'large': QSize(675, 555),
            'test_mode': QSize(385, 345)
        }
        
        # Base font sizes for scaling
        self.base_title_font_size = 12
        self.base_label_font_size = 12
        self.base_button_font_size = 10
        
        # Track password reset attempts
        self.reset_password_attempts = 0
        
        # Initialize settings
        self.settings = QSettings('SouthamptonHS', 'ScheduleTracker')
        self.admin_password = self.settings.value('admin_password', 'shs')
        
        # Create menu bar after settings are initialized
        self.create_menu_bar()
        
        # Define default colors
        self.default_colors = {
            "window_bg_color": "#000000",
            "window_text_color": "#FFFFFF",
            "message_bg_color": "#000066",
            "message_text_color": "#FFFFFF"
        }
        
        # Initialize current colors from settings or defaults
        self.current_colors = {}
        for key, default in self.default_colors.items():
            self.current_colors[key] = self.settings.value(key, default)
        
        # Test mode initialization
        self.test_mode = False
        self.test_time = datetime.now()
        self.test_container = None
        
        # Load schedules
        with open('schedules.json', 'r') as f:
            self.schedules = json.load(f)['southampton_high_school']
        
        # Create central widget and layout
        self.setup_ui()
        
        # Set up system tray
        self.setup_system_tray()
        
        # Set up timer for updates
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_periods)
        self.timer.start(60000)  # Update every minute
        
        # Initial update
        self.update_periods()
        
        # Restore window position
        self.restore_window_position()
        
        # If test mode is enabled, set up the test controls
        if self.test_mode:
            self.setup_test_controls()

    def setup_ui(self):
        # Create central widget and set it to expand
        central_widget = QWidget()
        central_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        
        # Create schedule displays with labels
        schedule_container = QWidget()
        schedule_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        schedule_layout = QVBoxLayout(schedule_container)
        schedule_layout.setSpacing(1)
        schedule_layout.setContentsMargins(1, 1, 1, 1)
        
        # Store containers for later resizing
        self.schedule_containers = []
        
        # Regular Schedule
        regular_container = QWidget()
        regular_container.setObjectName("regular_container")
        regular_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        regular_layout = QVBoxLayout(regular_container)
        regular_layout.setSpacing(1)
        regular_layout.setContentsMargins(2, 2, 2, 2)
        
        regular_title = QLabel("Regular")
        regular_title.setProperty("class", "title")
        regular_title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Policy.Minimum)
        regular_title.setAlignment(Qt.AlignLeft)  # Left align title
        
        self.regular_label = QLabel("Not in session")
        self.regular_label.setObjectName("regular_label")
        self.regular_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.regular_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.regular_label.setWordWrap(True)
        self.regular_label.setMinimumHeight(30)  # Ensure minimum height for text visibility
        
        regular_layout.addWidget(regular_title)
        regular_layout.addWidget(self.regular_label)
        schedule_layout.addWidget(regular_container)
        self.schedule_containers.append(regular_container)
        
        # Delay Schedule
        delay_container = QWidget()
        delay_container.setObjectName("delay_container")
        delay_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        delay_layout = QVBoxLayout(delay_container)
        delay_layout.setSpacing(1)
        delay_layout.setContentsMargins(2, 2, 2, 2)
        
        delay_title = QLabel("2-Hr Delay")
        delay_title.setProperty("class", "title")
        delay_title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Policy.Minimum)
        delay_title.setAlignment(Qt.AlignLeft)  # Left align title
        
        self.delay_label = QLabel("Not in session")
        self.delay_label.setObjectName("delay_label")
        self.delay_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.delay_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.delay_label.setWordWrap(True)
        self.delay_label.setMinimumHeight(30)  # Ensure minimum height for text visibility
        
        delay_layout.addWidget(delay_title)
        delay_layout.addWidget(self.delay_label)
        schedule_layout.addWidget(delay_container)
        self.schedule_containers.append(delay_container)
        
        # Homeroom Schedule
        homeroom_container = QWidget()
        homeroom_container.setObjectName("homeroom_container")
        homeroom_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        homeroom_layout = QVBoxLayout(homeroom_container)
        homeroom_layout.setSpacing(1)
        homeroom_layout.setContentsMargins(2, 2, 2, 2)
        
        homeroom_title = QLabel("Homeroom")
        homeroom_title.setProperty("class", "title")
        homeroom_title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Policy.Minimum)
        homeroom_title.setAlignment(Qt.AlignLeft)  # Left align title
        
        self.homeroom_label = QLabel("Not in session")
        self.homeroom_label.setObjectName("homeroom_label")
        self.homeroom_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.homeroom_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.homeroom_label.setWordWrap(True)
        self.homeroom_label.setMinimumHeight(30)  # Ensure minimum height for text visibility
        
        homeroom_layout.addWidget(homeroom_title)
        homeroom_layout.addWidget(self.homeroom_label)
        schedule_layout.addWidget(homeroom_container)
        self.schedule_containers.append(homeroom_container)
        
        self.main_layout.addWidget(schedule_container)
        
        # Set up window properties
        self.setMinimumWidth(300)
        self.setMinimumHeight(200)
        
        # Store the default size
        self.default_size = QSize(300, 200)
        self.test_size = QSize(300, 240)  # Size when test controls are visible
        
        # Set initial size
        self.resize(self.default_size)
        
        # Apply styles
        self.apply_styles()
        
        # Initial font scaling
        self.scale_fonts()
        
        # Initial container adjustment
        self.adjust_container_heights()

    def create_menu_bar(self):
        menubar = self.menuBar()
        tools_menu = menubar.addMenu('Tools')
        
        # Group 1: Display Settings
        # Create Window Size submenu
        size_menu = tools_menu.addMenu('Window Size')
        
        # Add size options
        size_group = QActionGroup(self)
        size_group.setExclusive(True)
        
        for size_name in ['small', 'medium', 'large']:
            action = QAction(size_name.capitalize(), self)
            action.setCheckable(True)
            action.setData(size_name)
            if size_name == self.settings.value('window_size', 'small'):
                action.setChecked(True)
            action.triggered.connect(lambda checked, s=size_name: self.change_window_size(s))
            size_group.addAction(action)
            size_menu.addAction(action)
        
        # Store the action group for later use
        self.size_actions = size_group
        
        # Create Icon Selection submenu
        icon_menu = tools_menu.addMenu('Select Tray Icon')
        
        # Add icon options
        clock_icon_action = QAction('Clock Icon', self)
        clock_icon_action.setCheckable(True)
        timer_icon_action = QAction('Timer Icon', self)
        timer_icon_action.setCheckable(True)
        
        # Create action group for icons
        icon_group = QActionGroup(self)
        icon_group.setExclusive(True)
        icon_group.addAction(clock_icon_action)
        icon_group.addAction(timer_icon_action)
        
        # Set checked state based on saved preference
        saved_icon = self.settings.value('tray_icon', 'clock.png')
        clock_icon_action.setChecked(saved_icon == 'clock.png')
        timer_icon_action.setChecked(saved_icon == 'timer.png')
        
        clock_icon_action.triggered.connect(lambda: self.change_tray_icon('clock.png'))
        timer_icon_action.triggered.connect(lambda: self.change_tray_icon('timer.png'))
        
        # Add to icon menu
        icon_menu.addAction(clock_icon_action)
        icon_menu.addAction(timer_icon_action)
        
        # Store actions for later use
        self.icon_actions = {'clock.png': clock_icon_action, 'timer.png': timer_icon_action}
        
        tools_menu.addSeparator()
        
        # Group 2: Application Settings
        color_settings_action = QAction('Color Settings', self)
        color_settings_action.triggered.connect(self.show_color_settings)
        tools_menu.addAction(color_settings_action)
        
        schedule_editor_action = QAction('Schedule Editor', self)
        schedule_editor_action.triggered.connect(self.show_schedule_editor)
        tools_menu.addAction(schedule_editor_action)
        
        tools_menu.addSeparator()
        
        # Group 3: Security Settings
        self.test_mode_action = QAction('Enable Test Mode', self)
        self.test_mode_action.setCheckable(True)
        self.test_mode_action.triggered.connect(self.toggle_test_mode)
        tools_menu.addAction(self.test_mode_action)
        
        change_password_action = QAction('Change Admin Password', self)
        change_password_action.triggered.connect(self.change_password)
        tools_menu.addAction(change_password_action)
        
        reset_password_action = QAction('Reset Password', self)
        reset_password_action.triggered.connect(self.reset_password)
        tools_menu.addAction(reset_password_action)
        
        tools_menu.addSeparator()
        
        # Group 4: Exit
        exit_action = QAction('Exit', self)
        exit_action.triggered.connect(self.quit_application)
        tools_menu.addAction(exit_action)
        
        # Add Help menu
        help_menu = menubar.addMenu('Help')
        
        # Add User Guide action
        user_guide_action = QAction('User Guide', self)
        user_guide_action.triggered.connect(self.show_user_guide)
        help_menu.addAction(user_guide_action)
        
        # Add About action
        about_action = QAction('About Schedule Tracker', self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

    def show_schedule_editor(self):
        # Prompt for password
        password_dialog = QInputDialog(self)
        password_dialog.setWindowTitle('Schedule Editor Access')
        password_dialog.setLabelText('Enter password to access schedule editor:')
        password_dialog.setTextEchoMode(QLineEdit.Password)
        self.setup_dialog_style(password_dialog)
        
        if not password_dialog.exec():
            return
        
        password = password_dialog.textValue()
        
        if password != self.admin_password:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle('Error')
            msg.setText('Incorrect password')
            self.setup_dialog_style(msg)
            msg.exec()
            return
        
        editor = ScheduleEditorDialog(self.schedules, self)
        if editor.exec() == QDialog.Accepted:
            self.schedules = editor.get_updated_schedules()
            self.save_schedules()
            self.update_periods()

    def setup_dialog_style(self, dialog):
        # Apply style directly to the provided dialog
        dialog.setStyleSheet("""
            QDialog, QMessageBox {
                background-color: black;
            }
            QLabel {
                color: white;
            }
            QLineEdit {
                background-color: #000066;
                color: white;
                border: 1px solid #0000cc;
                padding: 5px;
                selection-background-color: #000099;
            }
            QPushButton {
                background-color: #000066;
                color: white;
                border: 1px solid #0000cc;
                min-width: 60px;
                padding: 5px;
            }
        """)

    def save_schedules(self):
        try:
            with open('schedules.json', 'w') as f:
                json.dump({'southampton_high_school': self.schedules}, f, indent=4)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save schedules: {str(e)}")

    def update_periods(self):
        regular = self.get_current_period('regular_schedule')
        delay = self.get_current_period('two_hour_delay')
        homeroom = self.get_current_period('homeroom_schedule')
        
        current_time = self.get_current_time()
        time_status = "TEST MODE" if self.test_mode else "LIVE"
        
        self.regular_label.setText(regular)
        self.delay_label.setText(delay)
        self.homeroom_label.setText(homeroom)
        
        # Update window title with current time and mode
        self.setWindowTitle(f"SH Schedule Tracker - {current_time} ({time_status})")
        
        # Update tray tooltip
        tooltip = f"Current Time: {current_time} ({time_status})\nRegular: {regular}\n2-Hour Delay: {delay}\nHomeroom: {homeroom}"
        self.tray_icon.setToolTip(tooltip)

    def setup_system_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        
        # Load saved icon preference or use default
        icon_file = self.settings.value('tray_icon', 'clock.png')
        icon_path = os.path.join(ICON_DIR, icon_file)
        icon = QIcon(icon_path)
        self.tray_icon.setIcon(icon)
        self.tray_icon.show()
        
        # Connect only the activation signal for toggling window visibility
        self.tray_icon.activated.connect(self.tray_icon_activated)

    def tray_icon_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            # Toggle window visibility on any click
            if self.isVisible():
                self.hide_window()
            else:
                self.show_window()

    def show_window(self):
        self.show()
        self.activateWindow()  # Brings window to front

    def hide_window(self):
        self.hide()

    def closeEvent(self, event):
        # Save settings before closing
        self.save_window_position()
        self.settings.setValue('admin_password', self.admin_password)
        
        # Ask user if they want to exit or minimize to tray
        reply = QMessageBox(
            QMessageBox.Warning,
            'Exit?',
            'Do you want to exit the application?\nClick No to minimize to tray instead.',
            QMessageBox.Yes | QMessageBox.No,
            self
        )
        
        # Set fixed size and center dialog on parent window
        reply.setFixedSize(265, 135)
        
        # Apply simple styling to ensure text visibility
        reply.setStyleSheet("""
            * {
                background-color: black;
                color: white;
            }
            QPushButton {
                background-color: #000066;
                border: 1px solid #0000cc;
                min-width: 60px;
                padding: 5px;
            }
        """)
        
        # Calculate center position relative to parent window
        x = self.x() + (self.width() - 265) // 2
        y = self.y() + (self.height() - 135) // 2
        reply.move(x, y)
        
        if reply.exec() == QMessageBox.Yes:
            self.settings.setValue('test_mode_enabled', self.test_mode)
            event.accept()
            QApplication.quit()
        else:
            event.ignore()
            self.hide_window()

    def save_window_position(self):
        # Save current window position and size as individual values
        pos = self.pos()
        size = self.size()
        self.settings.setValue('window_position_x', pos.x())
        self.settings.setValue('window_position_y', pos.y())
        self.settings.setValue('window_width', size.width())
        self.settings.setValue('window_height', size.height())

    def restore_window_position(self):
        # Get saved position
        pos_x = self.settings.value('window_position_x', type=int)
        pos_y = self.settings.value('window_position_y', type=int)
        
        # Set initial size based on saved preference or default to small
        saved_size = self.settings.value('window_size', 'small')
        self.setFixedSize(self.window_sizes[saved_size])
        
        if pos_x is not None and pos_y is not None:
            # Check if the saved position is valid (on a visible screen)
            screen = QApplication.primaryScreen().availableGeometry()
            if (screen.contains(pos_x, pos_y) and 
                screen.contains(pos_x + self.width(), pos_y + self.height())):
                self.move(pos_x, pos_y)
            else:
                self.center_on_screen()

    def center_on_screen(self):
        """Center the window on the screen"""
        # Force the window to calculate its true size
        self.adjustSize()
        
        # Get the screen geometry
        screen = QApplication.primaryScreen().availableGeometry()
        
        # Calculate center position
        x = screen.center().x() - (self.frameGeometry().width() // 2)
        y = screen.center().y() - (self.frameGeometry().height() // 2)
        
        # Ensure coordinates are within screen bounds
        x = max(screen.left(), min(x, screen.right() - self.frameGeometry().width()))
        y = max(screen.top(), min(y, screen.bottom() - self.frameGeometry().height()))
        
        # Move window
        self.move(x, y)

    def setup_test_controls(self):
        if self.test_container is None:
            # Set fixed test mode size
            self.setFixedSize(self.window_sizes['test_mode'])
            
            self.test_container = QWidget()
            self.test_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Policy.Minimum)
            test_layout = QVBoxLayout(self.test_container)
            test_layout.setSpacing(2)
            test_layout.setContentsMargins(2, 2, 2, 2)
            
            # Manual time control layout
            time_control = QHBoxLayout()
            time_control.setSpacing(2)
            
            self.time_edit = QTimeEdit()
            self.time_edit.setDisplayFormat("HH:mm")  # Use 24-hour format
            self.time_edit.setFixedHeight(25)  # Set consistent height
            self.time_edit.setMinimumWidth(100)  # Doubled from 50
            self.time_edit.setMaximumWidth(120)  # Doubled from 60
            self.time_edit.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)  # Changed to Fixed
            self.time_edit.setReadOnly(False)  # Make editable
            self.time_edit.setStyleSheet("""
                QTimeEdit {
                    background-color: #000000;
                    color: white;
                    border: 1px solid #666666;
                    padding: 2px;
                    font-weight: bold;
                }
                QTimeEdit::up-button {
                    width: 16px;
                    background-color: #000000;
                    border: 1px solid #666666;
                    border-radius: 2px;
                }
                QTimeEdit::down-button {
                    width: 16px;
                    background-color: #000000;
                    border: 1px solid #666666;
                    border-radius: 2px;
                }
                QTimeEdit::up-button:pressed, QTimeEdit::down-button:pressed {
                    background-color: #333333;
                }
            """)
            
            set_time_btn = QPushButton("Set")
            set_time_btn.setFixedHeight(25)  # Match time edit height
            set_time_btn.setMinimumWidth(40)
            set_time_btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
            set_time_btn.clicked.connect(self.set_test_time)
            set_time_btn.setEnabled(True)  # Enable the button
            set_time_btn.setStyleSheet("""
                QPushButton {
                    background-color: #000000;
                    color: white;
                    border: 1px solid #666666;
                    padding: 2px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #333333;
                }
            """)
            
            # Add test time label to time control layout
            self.test_time_label = QLabel("")
            self.test_time_label.setFixedHeight(25)  # Match other elements
            self.test_time_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self.test_time_label.setStyleSheet("""
                QLabel {
                    background-color: #000000;
                    color: white;
                    border: 1px solid #666666;
                    padding: 2px;
                    font-weight: bold;
                }
            """)
            
            time_control.addWidget(self.time_edit)
            time_control.addWidget(set_time_btn)
            time_control.addWidget(self.test_time_label)
            time_control.addStretch()  # Add stretch to push everything to the left
            
            # File-based time control layout
            file_control = QHBoxLayout()
            file_control.setSpacing(2)
            
            # Add delay control
            delay_label = QLabel("Delay (sec):")
            delay_label.setStyleSheet("""
                QLabel {
                    background-color: #000000;
                    color: white;
                    border: 1px solid #666666;
                    padding: 2px;
                    font-weight: bold;
                }
            """)
            delay_label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
            delay_label.setFixedHeight(25)  # Match other elements
            
            self.delay_spinbox = QSpinBox()
            self.delay_spinbox.setMinimum(1)
            self.delay_spinbox.setMaximum(60)
            self.delay_spinbox.setValue(5)  # Default 5 seconds
            self.delay_spinbox.setFixedHeight(25)  # Match time edit height
            self.delay_spinbox.setMinimumWidth(50)
            self.delay_spinbox.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
            self.delay_spinbox.setReadOnly(False)  # Make editable
            self.delay_spinbox.valueChanged.connect(self.update_delay)
            self.delay_spinbox.setStyleSheet("""
                QSpinBox {
                    background-color: #000000;
                    color: white;
                    border: 1px solid #666666;
                    padding: 2px;
                    font-weight: bold;
                }
                QSpinBox::up-button {
                    width: 16px;
                    background-color: #000000;
                    border: 1px solid #666666;
                    border-radius: 2px;
                }
                QSpinBox::down-button {
                    width: 16px;
                    background-color: #000000;
                    border: 1px solid #666666;
                    border-radius: 2px;
                }
                QSpinBox::up-button:pressed, QSpinBox::down-button:pressed {
                    background-color: #333333;
                }
            """)
            
            load_file_btn = QPushButton("Load Time File")
            load_file_btn.setFixedHeight(25)  # Match time edit height
            load_file_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            load_file_btn.clicked.connect(self.load_time_file)
            load_file_btn.setEnabled(True)  # Enable the button
            load_file_btn.setStyleSheet("""
                QPushButton {
                    background-color: #000000;
                    color: white;
                    border: 1px solid #666666;
                    padding: 2px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #333333;
                }
            """)
            
            self.stop_file_btn = QPushButton("Stop")
            self.stop_file_btn.setFixedHeight(25)  # Match time edit height
            self.stop_file_btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
            self.stop_file_btn.clicked.connect(self.stop_time_file)
            self.stop_file_btn.setEnabled(False)  # Initially disabled until file is loaded
            self.stop_file_btn.setStyleSheet("""
                QPushButton {
                    background-color: #000000;
                    color: white;
                    border: 1px solid #666666;
                    padding: 2px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #333333;
                }
                QPushButton:disabled {
                    background-color: #000000;
                    color: #666666;
                }
            """)
            
            file_control.addWidget(delay_label)
            file_control.addWidget(self.delay_spinbox)
            file_control.addWidget(load_file_btn, 2)  # Give load button more space
            file_control.addWidget(self.stop_file_btn)
            
            test_layout.addLayout(time_control)
            test_layout.addLayout(file_control)
            
            self.main_layout.addWidget(self.test_container)
            
            # Initialize file processing attributes
            self.time_file_timer = QTimer()
            self.time_file_timer.timeout.connect(self.process_next_time)
            self.time_file_lines = []
            self.current_line_index = 0
            
            # Resize window to accommodate test controls
            self.resize(self.test_size)
            
            self.test_mode = True
            self.set_test_time()
            self.update_periods()
            
            # Apply initial scaling to test controls
            self.scale_fonts()
            
            # Apply consistent styling to all test controls
            self.test_container.setStyleSheet("""
                QPushButton {
                    background-color: #808080;
                    color: black;
                    border: 1px solid #666666;
                    padding: 2px 10px;
                    min-width: 80px;
                }
                QPushButton:disabled {
                    background-color: #808080;
                    color: black;
                    border: 1px solid #666666;
                }
                QLabel {
                    color: black;
                    background-color: #808080;
                }
            """)

    def remove_test_controls(self):
        if self.test_container is not None:
            # Stop any running time file processing
            if hasattr(self, 'time_file_timer'):
                self.time_file_timer.stop()
            
            # Remove test controls from layout
            self.main_layout.removeWidget(self.test_container)
            self.test_container.deleteLater()
            self.test_container = None
            
            # Restore previous window size
            saved_size = self.settings.value('window_size', 'small')
            self.setFixedSize(self.window_sizes[saved_size])

    def set_test_time(self):
        if self.test_mode:
            time = self.time_edit.time()
            self.test_time = datetime.now().replace(
                hour=time.hour(),
                minute=time.minute(),
                second=0
            )
            self.update_periods()

    def update_delay(self):
        """Update the timer interval if it's running"""
        if hasattr(self, 'time_file_timer') and self.time_file_timer.isActive():
            self.time_file_timer.setInterval(self.delay_spinbox.value() * 1000)

    def load_time_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Time File",
            TEST_DIR,  # Set initial directory to testing folder
            "Text Files (*.txt);;All Files (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r') as file:
                    # Read and validate times
                    self.time_file_lines = []
                    for line in file:
                        time_str = line.strip()
                        try:
                            # Validate time format
                            datetime.strptime(time_str, "%H:%M")
                            self.time_file_lines.append(time_str)
                        except ValueError:
                            continue  # Skip invalid times
            
                if self.time_file_lines:
                    self.current_line_index = 0
                    self.stop_file_btn.setEnabled(True)
                    self.process_next_time()
                    # Use the current spinbox value for the delay
                    self.time_file_timer.start(self.delay_spinbox.value() * 1000)
            
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Error loading time file: {str(e)}")

    def process_next_time(self):
        if self.current_line_index < len(self.time_file_lines):
            time_str = self.time_file_lines[self.current_line_index]
            time = datetime.strptime(time_str, "%H:%M")
            self.test_time = datetime.now().replace(
                hour=time.hour,
                minute=time.minute,
                second=0
            )
            # Update the test time label
            self.test_time_label.setText(f"Test Time: {time_str}")
            self.update_periods()
            self.current_line_index += 1
        else:
            self.stop_time_file()

    def stop_time_file(self):
        self.time_file_timer.stop()
        self.stop_file_btn.setEnabled(False)
        self.time_file_lines = []
        self.current_line_index = 0
        self.test_time_label.setText("")  # Clear the test time label

    def apply_styles(self):
        # Apply window background and text colors
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background-color: {self.current_colors['window_bg_color']};
            }}
            
            /* Style for schedule title labels (Regular, 2-Hr Delay, Homeroom) */
            QLabel[class="title"] {{
                background-color: transparent;
                color: {self.current_colors['window_text_color']};
                border: none;
                font-weight: bold;
                font-size: {self.base_title_font_size}px;
                padding: 2px;
            }}
            
            /* Style for period display labels */
            #regular_label, #delay_label, #homeroom_label {{
                background-color: {self.current_colors['message_bg_color']};
                color: {self.current_colors['message_text_color']};
                border: 2px solid #0000cc;
                border-radius: 5px;
                padding: 8px;
                margin: 2px;
                font-weight: bold;
            }}
            
            /* Style for schedule containers */
            QWidget[class="schedule_container"] {{
                background-color: {self.current_colors['window_bg_color']};
                border: 1px solid #0000cc;
                border-radius: 5px;
                margin: 2px;
                padding: 4px;
            }}
            
            QPushButton {{
                background-color: #000066;
                color: white;
                border: 1px solid #0000cc;
                padding: 5px 10px;
                min-width: 80px;
            }}
            QPushButton:hover {{
                background-color: #000099;
            }}
            QMenuBar {{
                background-color: {self.current_colors['window_bg_color']};
                color: white;
            }}
            QMenuBar::item:selected {{
                background-color: #000099;
            }}
            QMenu {{
                background-color: {self.current_colors['window_bg_color']};
                color: white;
            }}
            QMenu::item:selected {{
                background-color: #000099;
            }}
        """)

    def quit_application(self):
        # Save position before quitting
        self.save_window_position()
        QApplication.quit()

    def change_password(self):
        # First verify current password
        current_pwd_dialog = QInputDialog(self)
        current_pwd_dialog.setWindowTitle('Change Password')
        current_pwd_dialog.setLabelText('Enter current password:')
        current_pwd_dialog.setTextEchoMode(QLineEdit.Password)
        self.setup_dialog_style(current_pwd_dialog)
        
        if not current_pwd_dialog.exec():
            return
        
        current_pwd = current_pwd_dialog.textValue()
        
        if current_pwd != self.admin_password:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle('Error')
            msg.setText('Incorrect password')
            self.setup_dialog_style(msg)
            msg.exec()
            return
        
        # Get new password
        new_pwd_dialog = QInputDialog(self)
        new_pwd_dialog.setWindowTitle('Change Password')
        new_pwd_dialog.setLabelText('Enter new password:')
        new_pwd_dialog.setTextEchoMode(QLineEdit.Password)
        self.setup_dialog_style(new_pwd_dialog)
        
        if not new_pwd_dialog.exec():
            return
        
        new_pwd = new_pwd_dialog.textValue()
        
        if not new_pwd:
            return
        
        # Confirm new password
        confirm_pwd_dialog = QInputDialog(self)
        confirm_pwd_dialog.setWindowTitle('Change Password')
        confirm_pwd_dialog.setLabelText('Confirm new password:')
        confirm_pwd_dialog.setTextEchoMode(QLineEdit.Password)
        self.setup_dialog_style(confirm_pwd_dialog)
        
        if not confirm_pwd_dialog.exec():
            return
        
        confirm_pwd = confirm_pwd_dialog.textValue()
        
        if new_pwd != confirm_pwd:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle('Error')
            msg.setText('Passwords do not match')
            self.setup_dialog_style(msg)
            msg.exec()
            return
        
        # Save new password
        self.admin_password = new_pwd
        self.settings.setValue('admin_password', new_pwd)
        
        success_msg = QMessageBox(self)
        success_msg.setIcon(QMessageBox.Information)
        success_msg.setWindowTitle('Success')
        success_msg.setText('Password changed successfully')
        self.setup_dialog_style(success_msg)
        success_msg.exec()

    def reset_password(self):
        # Check if maximum attempts reached
        if self.reset_password_attempts >= 3:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle('Maximum Attempts Reached')
            msg.setText('You have reached the maximum number of password reset attempts.\n\n' +
                       'Please contact the developer at info@fragillidaesoftware.com for assistance.')
            self.setup_dialog_style(msg)
            msg.exec()
            return
        
        # Prompt for master reset password
        reset_pwd_dialog = QInputDialog(self)
        reset_pwd_dialog.setWindowTitle('Reset Password')
        reset_pwd_dialog.setLabelText('Enter master reset password:')
        reset_pwd_dialog.setTextEchoMode(QLineEdit.Password)
        self.setup_dialog_style(reset_pwd_dialog)
        
        if not reset_pwd_dialog.exec():
            return
        
        master_pwd = reset_pwd_dialog.textValue()
        
        if master_pwd != 'chucksoft':
            self.reset_password_attempts += 1
            remaining_attempts = 3 - self.reset_password_attempts
            
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle('Error')
            
            if remaining_attempts > 0:
                msg.setText(f'Incorrect master reset password\n\n{remaining_attempts} attempts remaining')
            else:
                msg.setText('Incorrect master reset password\n\n' +
                          'You have reached the maximum number of attempts.\n' +
                          'Please contact the developer at info@fragillidaesoftware.com for assistance.')
            
            self.setup_dialog_style(msg)
            msg.exec()
            return
        
        # Reset to default password
        self.admin_password = 'shs'
        self.settings.setValue('admin_password', 'shs')
        
        # Reset attempt counter on successful password reset
        self.reset_password_attempts = 0
        
        success_msg = QMessageBox(self)
        success_msg.setIcon(QMessageBox.Information)
        success_msg.setWindowTitle('Success')
        success_msg.setText('Password has been reset to default')
        self.setup_dialog_style(success_msg)
        success_msg.exec()

    def toggle_test_mode(self, checked):
        if checked:
            # Prompt for password
            password_dialog = QInputDialog(self)
            password_dialog.setWindowTitle('Test Mode Access')
            password_dialog.setLabelText('Enter password to enable test mode:')
            password_dialog.setTextEchoMode(QLineEdit.Password)
            self.setup_dialog_style(password_dialog)
            
            if not password_dialog.exec():
                self.test_mode_action.setChecked(False)
                return
            
            password = password_dialog.textValue()
            
            if password == self.admin_password:
                self.test_mode_action.setText('Disable Test Mode')
                self.setup_test_controls()
            else:
                self.test_mode_action.setChecked(False)
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Warning)
                msg.setWindowTitle('Error')
                msg.setText('Incorrect password')
                self.setup_dialog_style(msg)
                msg.exec()
        else:
            self.test_mode_action.setText('Enable Test Mode')
            self.remove_test_controls()
            self.test_mode = False
            self.update_periods()

    def get_current_period(self, schedule_type):
        current_time = datetime.strptime(self.get_current_time(), "%H:%M")
        schedule = self.schedules[schedule_type]
        periods = schedule['periods']
        
        # Check if it's before school (between midnight and warning bell)
        warning_bell = datetime.strptime("07:25", "%H:%M")
        if current_time < warning_bell:
            return "Before School"
        
        # Find Period 1
        period_1 = next((p for p in periods if p['name'] == '1'), None)
        if period_1 and period_1['start']:
            period_1_start = datetime.strptime(period_1['start'], "%H:%M")
            # If we're between warning bell and period 1
            if warning_bell <= current_time < period_1_start:
                return f"Period 1 starts at {period_1['start']}"
        
        # Check if it's after school (after 14:30)
        after_school_time = datetime.strptime("14:30", "%H:%M")
        if current_time >= after_school_time:
            return "After School"
        
        # Check if we're in a period
        for period in periods:
            if period['start'] and period['end']:
                start_time = datetime.strptime(period['start'], "%H:%M")
                end_time = datetime.strptime(period['end'], "%H:%M")
                
                if start_time <= current_time <= end_time:
                    period_name = period['name']
                    return f"Period {period_name}" if period_name.isdigit() else period_name
        
        # If not in a period, check if we're between periods
        for i in range(len(periods) - 1):
            current_period = periods[i]
            next_period = periods[i + 1]
            
            if current_period['end'] and next_period['start']:
                period_end = datetime.strptime(current_period['end'], "%H:%M")
                next_start = datetime.strptime(next_period['start'], "%H:%M")
                
                if period_end < current_time < next_start:
                    current_name = current_period['name']
                    next_name = next_period['name']
                    
                    # Format period numbers
                    if current_name.isdigit():
                        current_name = f"Period {current_name}"
                    if next_name.isdigit():
                        next_name = f"Period {next_name}"
                    
                    return f"{current_name} → {next_name}"
        
        return "Not in Session"

    def get_current_time(self):
        if self.test_mode:
            return self.test_time.strftime("%H:%M")
        return datetime.now().strftime("%H:%M")

    def show_color_settings(self):
        dialog = ColorSettingsDialog(self)
        self.setup_dialog_style(dialog)
        if dialog.exec() == QDialog.Accepted:
            # Save colors to settings
            for key, color in self.current_colors.items():
                self.settings.setValue(key, color)
            
            # Apply new colors
            self.apply_styles()
            
            # Force update of all schedule labels
            for label in [self.regular_label, self.delay_label, self.homeroom_label]:
                font = label.font()
                label.setStyleSheet(f"""
                    background-color: {self.current_colors['message_bg_color']};
                    color: {self.current_colors['message_text_color']};
                    border: 1px solid #0000cc;
                    border-radius: 3px;
                    padding: 8px;
                    margin: 1px;
                    font-weight: bold;
                """)
            
            # Update title labels
            for widget in self.findChildren(QLabel):
                if widget.property("class") == "title":
                    widget.setStyleSheet(f"""
                        background-color: transparent;
                        color: {self.current_colors['window_text_color']};
                        border: none;
                        font-weight: bold;
                        font-size: {self.base_title_font_size}px;
                        padding: 2px;
                    """)
            
            # Force a repaint of the window
            self.repaint()

    def resizeEvent(self, event):
        """Handle window resize events"""
        super().resizeEvent(event)
        self.scale_fonts()
        self.adjust_layout_spacing()
        self.adjust_container_heights()
        
    def scale_fonts(self):
        """Scale fonts based on window size"""
        # Calculate scale factor based on window width
        width_scale = self.width() / 300  # 300 is our base width
        height_scale = self.height() / 200  # 200 is our base height
        scale_factor = min(width_scale, height_scale)  # Use smaller scale to maintain readability
        
        # Scale title fonts - ensure minimum size for titles
        title_font_size = max(8, int(self.base_title_font_size * scale_factor))
        for widget in self.findChildren(QLabel):
            if widget.property("class") == "title":
                font = widget.font()
                font.setPointSize(title_font_size)
                font.setBold(True)
                widget.setFont(font)
        
        # Scale label fonts with a more conservative minimum size
        label_font_size = max(7, int(self.base_label_font_size * scale_factor))
        for label in [self.regular_label, self.delay_label, self.homeroom_label]:
            font = label.font()
            font.setPointSize(label_font_size)
            font.setBold(True)
            label.setFont(font)
            
            # Adjust padding based on font size but keep it minimal at small sizes
            padding = max(2, int(6 * scale_factor))
            label.setStyleSheet(f"""
                background-color: {self.current_colors['message_bg_color']};
                color: {self.current_colors['message_text_color']};
                border: 1px solid #0000cc;
                border-radius: 3px;
                padding: {padding}px;
                margin: 1px;
                font-weight: bold;
            """)
        
        # Scale button fonts if they exist
        button_font_size = max(8, int(self.base_button_font_size * scale_factor))
        for button in self.findChildren(QPushButton):
            font = button.font()
            font.setPointSize(button_font_size)
            button.setFont(font)
            
    def adjust_layout_spacing(self):
        """Adjust layout spacing and margins based on window size"""
        # Calculate base spacing based on window size
        base_spacing = max(1, min(self.width(), self.height()) // 100)
        
        # Adjust main layout
        self.main_layout.setSpacing(base_spacing)
        self.main_layout.setContentsMargins(base_spacing, base_spacing, base_spacing, base_spacing)
        
        # Adjust all container layouts
        for container in [self.findChild(QWidget, name) for name in ["regular_container", "delay_container", "homeroom_container"]]:
            if container and container.layout():
                container.layout().setSpacing(base_spacing)
                container.layout().setContentsMargins(base_spacing, base_spacing, base_spacing, base_spacing)
                
        # Adjust test controls if they exist
        if hasattr(self, 'test_container') and self.test_container:
            self.test_container.layout().setSpacing(base_spacing)
            self.test_container.layout().setContentsMargins(base_spacing, base_spacing, base_spacing, base_spacing)

    def adjust_container_heights(self):
        """Adjust the heights of schedule containers based on window size"""
        if not hasattr(self, 'schedule_containers'):
            return
            
        # Calculate the available height for schedule containers
        available_height = self.height()
        if self.menuBar():
            available_height -= self.menuBar().height()
        if hasattr(self, 'test_container') and self.test_container:
            available_height -= self.test_container.height()
            
        # Calculate base height for each container (minus margins and spacing)
        base_height = (available_height - self.main_layout.spacing() * 4) // 3
        
        # Set minimum height for each container based on window size
        min_height = max(60, base_height)  # Increased minimum height to ensure text visibility
        
        for container in self.schedule_containers:
            container.setMinimumHeight(min_height)
            
        # Update the style to ensure borders are visible
        self.apply_container_styles()
            
    def apply_container_styles(self):
        """Apply styles to containers to make them visually distinct"""
        # Container styles are now handled in apply_styles()

    def change_tray_icon(self, icon_file):
        # Update icon
        icon_path = os.path.join(ICON_DIR, icon_file)
        icon = QIcon(icon_path)
        self.tray_icon.setIcon(icon)
        
        # Update checked states
        for action_file, action in self.icon_actions.items():
            action.setChecked(action_file == icon_file)
        
        # Save preference
        self.settings.setValue('tray_icon', icon_file)

    def change_window_size(self, size_name):
        # Update window size
        if not self.test_mode:
            self.setFixedSize(self.window_sizes[size_name])
            # Save preference
            self.settings.setValue('window_size', size_name)
        
        # Update checked states
        for action in self.size_actions.actions():
            action.setChecked(action.data() == size_name)
        
        # Trigger resize event to update scaling
        self.scale_fonts()
        self.adjust_layout_spacing()
        self.adjust_container_heights()

    def show_about_dialog(self):
        dialog = AboutDialog(self)
        dialog.exec()

    def show_user_guide(self):
        dialog = UserGuideDialog(self)
        dialog.exec()

class ScheduleEditorDialog(QDialog):
    def __init__(self, schedules, parent=None):
        super().__init__(parent)
        self.schedules = schedules.copy()  # Work with a copy of the schedules
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Schedule Editor")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        
        layout = QVBoxLayout(self)
        
        # Schedule type selector
        self.schedule_selector = QComboBox()
        self.schedule_selector.addItems([
            "Regular Schedule",
            "Two Hour Delay",
            "Homeroom Schedule"
        ])
        self.schedule_selector.currentIndexChanged.connect(self.load_schedule)
        
        # Period table
        self.period_table = QTableWidget()
        self.period_table.setColumnCount(3)
        self.period_table.setHorizontalHeaderLabels(["Period", "Start Time", "End Time"])
        header = self.period_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        
        # Buttons
        button_layout = QHBoxLayout()
        add_btn = QPushButton("Add Period")
        delete_btn = QPushButton("Delete Period")
        save_btn = QPushButton("Save Changes")
        cancel_btn = QPushButton("Cancel")
        
        add_btn.clicked.connect(self.add_period)
        delete_btn.clicked.connect(self.delete_period)
        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(add_btn)
        button_layout.addWidget(delete_btn)
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addWidget(self.schedule_selector)
        layout.addWidget(self.period_table)
        layout.addLayout(button_layout)
        
        # Load initial schedule
        self.load_schedule()
        
        # Apply styles
        self.setStyleSheet("""
            QDialog {
                background-color: #000000;
                color: white;
            }
            QTableWidget {
                background-color: #000066;
                color: white;
                gridline-color: #0000cc;
                border: 1px solid #0000cc;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #000033;
                color: white;
                padding: 5px;
                border: 1px solid #0000cc;
            }
            QPushButton {
                background-color: #000066;
                color: white;
                border: 1px solid #0000cc;
                padding: 5px 10px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #000099;
            }
            QComboBox {
                background-color: #000066;
                color: white;
                border: 1px solid #0000cc;
                padding: 5px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                background-color: #0000cc;
            }
            QComboBox QAbstractItemView {
                background-color: #000066;
                color: white;
                selection-background-color: #000099;
            }
        """)

    def load_schedule(self):
        schedule_map = {
            0: "regular_schedule",
            1: "two_hour_delay",
            2: "homeroom_schedule"
        }
        schedule_key = schedule_map[self.schedule_selector.currentIndex()]
        schedule = self.schedules[schedule_key]
        
        self.period_table.setRowCount(0)
        for period in schedule['periods']:
            row = self.period_table.rowCount()
            self.period_table.insertRow(row)
            
            # Period name
            name_item = QTableWidgetItem(period['name'])
            self.period_table.setItem(row, 0, name_item)
            
            # Start time
            start_item = QTableWidgetItem(period['start'] if period['start'] else "")
            self.period_table.setItem(row, 1, start_item)
            
            # End time
            end_item = QTableWidgetItem(period['end'] if period['end'] else "")
            self.period_table.setItem(row, 2, end_item)

    def add_period(self):
        row = self.period_table.rowCount()
        self.period_table.insertRow(row)
        
        # Add empty items
        for col in range(3):
            self.period_table.setItem(row, col, QTableWidgetItem(""))

    def delete_period(self):
        current_row = self.period_table.currentRow()
        if current_row >= 0:
            self.period_table.removeRow(current_row)

    def get_updated_schedules(self):
        schedule_map = {
            0: "regular_schedule",
            1: "two_hour_delay",
            2: "homeroom_schedule"
        }
        
        # Update current schedule
        schedule_key = schedule_map[self.schedule_selector.currentIndex()]
        periods = []
        
        for row in range(self.period_table.rowCount()):
            period = {
                'name': self.period_table.item(row, 0).text().strip(),
                'start': self.period_table.item(row, 1).text().strip(),
                'end': self.period_table.item(row, 2).text().strip()
            }
            periods.append(period)
        
        self.schedules[schedule_key]['periods'] = periods
        return self.schedules

class UserGuideDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("User Guide")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        layout = QVBoxLayout(self)
        
        # Create text display
        text_display = QTextEdit()
        text_display.setReadOnly(True)
        
        # Read and display user guide content
        try:
            with open('user_guide.md', 'r') as file:
                content = file.read()
                text_display.setPlainText(content)
        except Exception as e:
            text_display.setPlainText(f"Error loading user guide: {str(e)}")
        
        # OK button
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        ok_button.setFixedWidth(80)
        
        # Add widgets to layout
        layout.addWidget(text_display)
        layout.addWidget(ok_button, alignment=Qt.AlignCenter)
        
        # Apply dark theme styling
        self.setStyleSheet("""
            QDialog {
                background-color: #000000;
            }
            QTextEdit {
                background-color: #000066;
                color: white;
                border: 1px solid #0000cc;
                font-size: 11pt;
            }
            QPushButton {
                background-color: #000066;
                color: white;
                border: 1px solid #0000cc;
                padding: 5px 15px;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #000099;
            }
        """)

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("About Southampton Schedule Tracker")
        self.setFixedSize(355, 245)  # Increased height from 230 to 245
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Icon
        icon_label = QLabel()
        icon_path = os.path.join("icons", "fragillidae_icon64.png")
        if os.path.exists(icon_path):
            icon_label.setPixmap(QIcon(icon_path).pixmap(64, 64))  # Back to original size
        icon_label.setAlignment(Qt.AlignCenter)
        
        # Company info with more compact formatting
        info_text = """
        <div style='text-align: center;'>
        <h3 style='margin: 5px;'>SH Schedule Tracker v1.05</h3>
        <p style='margin: 8px;'><b>Fragillidae Software</b></p>
        <p style='margin: 8px;'>Chuck Finch</p>
        <p style='margin: 8px;'><a href="http://www.fragillidaesoftware.com">www.fragillidaesoftware.com</a></p>
        <p style='margin: 8px;'><a href="mailto:info@fragillidaesoftware.com">info@fragillidaesoftware.com</a></p>
        </div>
        """
        
        info_label = QLabel(info_text)
        info_label.setOpenExternalLinks(True)
        info_label.setAlignment(Qt.AlignCenter)
        
        # OK button
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        ok_button.setFixedWidth(80)
        
        # Add widgets to layout with some spacing
        layout.addWidget(icon_label)
        layout.addWidget(info_label)
        layout.addStretch(1)  # Add flexible space
        layout.addWidget(ok_button, alignment=Qt.AlignCenter)
        
        # Apply dark theme styling
        self.setStyleSheet("""
            QDialog {
                background-color: #000000;
            }
            QLabel {
                color: white;
                font-size: 11pt;
            }
            QLabel a {
                color: #3399ff;
            }
            QPushButton {
                background-color: #000066;
                color: white;
                border: 1px solid #0000cc;
                padding: 5px 15px;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #000099;
            }
        """)

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    window = ScheduleWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main() 