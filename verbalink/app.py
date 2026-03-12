"""Application bootstrap and top-level main window for Verbalink."""

import json
import logging
import os
import sys
import tempfile
import time

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from .models import AIAgent
from .ui.dialogs import AgentConfigDialog, ConversationAnalysisWindow
from .ui.assistant import AIResearchAssistant


class ChatApplication(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Verbalink")
        self.setGeometry(100, 100, 1200, 800)
        self.is_dark_mode = self.load_theme_preference()
        
        # Create temp directory for the application
        self.temp_dir = os.path.join(tempfile.gettempdir(), 'verbalink')
        os.makedirs(self.temp_dir, exist_ok=True)
        self.chat_file = os.path.join(self.temp_dir, 'research_chats.json')
        
        self.update_window_icon()
        self.setup_ui()
        self.apply_style()
        self.current_chat_id = None
        self.chats = {}
        self.load_chats()
        
        self.conversation_analysis_window = None
        
        if sys.platform == "win32":
            self.set_window_dark_mode(self.is_dark_mode)

    def setup_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.ai_research_assistant = AIResearchAssistant(self)
        self.main_layout.addWidget(self.ai_research_assistant)

        self.create_menu_bar()

    def create_menu_bar(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")
        view_menu = menu_bar.addMenu("View")
        research_menu = menu_bar.addMenu("Research")
        analysis_menu = menu_bar.addMenu("Analysis")
        
        new_chat_action = QAction("New Chat", self)
        new_chat_action.setShortcut("Ctrl+N")
        new_chat_action.triggered.connect(self.new_chat)
        file_menu.addAction(new_chat_action)

        export_action = QAction("Export Conversation", self)
        export_action.triggered.connect(self.ai_research_assistant.export_conversation)
        file_menu.addAction(export_action)

        self.dark_mode_action = QAction("Toggle Dark Mode", self)
        self.dark_mode_action.setCheckable(True)
        self.dark_mode_action.setChecked(self.is_dark_mode)
        self.dark_mode_action.triggered.connect(self.toggle_dark_mode)
        view_menu.addAction(self.dark_mode_action)

        config_agents_action = QAction("Configure Agents", self)
        config_agents_action.triggered.connect(self.configure_agents)
        research_menu.addAction(config_agents_action)

        start_research_action = QAction("Start Research Conversation", self)
        start_research_action.triggered.connect(self.ai_research_assistant.start_conversation)
        research_menu.addAction(start_research_action)

        analyze_conversation_action = QAction("Analyze Conversation", self)
        analyze_conversation_action.triggered.connect(self.open_conversation_analysis)
        analysis_menu.addAction(analyze_conversation_action)

    def new_chat(self):
        self.current_chat_id = f"chat_{int(time.time())}"
        self.chats[self.current_chat_id] = {
            "messages": [],
            "title": "New Research Chat",
            "agent1": None,
            "agent2": None,
            "topic": ""
        }
        self.ai_research_assistant.reset_state()
        self.save_chats()
        return self.current_chat_id

    def save_chats(self):
        try:
            with open(self.chat_file, "w", encoding='utf-8') as f:
                json.dump(self.chats, f, default=lambda o: o.__dict__, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Error saving chats: {e}")
            # Create a backup in case of failure
            backup_file = os.path.join(self.temp_dir, 'research_chats_backup.json')
            try:
                with open(backup_file, "w", encoding='utf-8') as f:
                    json.dump(self.chats, f, default=lambda o: o.__dict__, ensure_ascii=False)
            except Exception as backup_error:
                logging.error(f"Error creating backup: {backup_error}")

    def load_chats(self):
        try:
            if os.path.exists(self.chat_file):
                with open(self.chat_file, "r", encoding='utf-8') as f:
                    self.chats = json.load(f)
                for chat_id, chat_data in self.chats.items():
                    if chat_data["agent1"]:
                        chat_data["agent1"] = AIAgent(**chat_data["agent1"])
                    if chat_data["agent2"]:
                        chat_data["agent2"] = AIAgent(**chat_data["agent2"])
        except Exception as e:
            logging.error(f"Error loading chats: {e}")
            # Try to load from backup if main file fails
            backup_file = os.path.join(self.temp_dir, 'research_chats_backup.json')
            if os.path.exists(backup_file):
                try:
                    with open(backup_file, "r", encoding='utf-8') as f:
                        self.chats = json.load(f)
                    for chat_id, chat_data in self.chats.items():
                        if chat_data["agent1"]:
                            chat_data["agent1"] = AIAgent(**chat_data["agent1"])
                        if chat_data["agent2"]:
                            chat_data["agent2"] = AIAgent(**chat_data["agent2"])
                except Exception as backup_error:
                    logging.error(f"Error loading backup: {backup_error}")
                    self.chats = {}

    def configure_agents(self):
        dialog = AgentConfigDialog(self)
        dialog.configUpdated.connect(self.update_agents_from_config)
        dialog.exec_()

    def update_agents_from_config(self):
        settings = QSettings("AIResearch", "AgentConfig")
        agent1_name = settings.value("agent1_name", "", type=str)
        agent1_persona = settings.value("agent1_persona", "", type=str)
        agent2_name = settings.value("agent2_name", "", type=str)
        agent2_persona = settings.value("agent2_persona", "", type=str)

        self.ai_research_assistant.agent1 = AIAgent(
            name=agent1_name or "Sarah",
            persona=agent1_persona or "(default)"
        )
        self.ai_research_assistant.agent2 = AIAgent(
            name=agent2_name or "Sam",
            persona=agent2_persona or "(default)"
        )
    
        if self.current_chat_id:
            self.chats[self.current_chat_id]["agent1"] = self.ai_research_assistant.agent1
            self.chats[self.current_chat_id]["agent2"] = self.ai_research_assistant.agent2
            self.save_chats()
            
    def open_conversation_analysis(self):
        if not self.conversation_analysis_window:
            self.conversation_analysis_window = ConversationAnalysisWindow(self)
        self.conversation_analysis_window.is_dark_mode = self.is_dark_mode  # Add this line
        self.conversation_analysis_window.apply_style(self.is_dark_mode)
        self.conversation_analysis_window.show()

    def apply_style(self):
        if self.is_dark_mode:
            self.setStyleSheet("""
                QMainWindow, QWidget {
                    background-color: #1e1e1e;
                    color: #ffffff;
                }
                QTextEdit, QPushButton, QLineEdit {
                    background-color: #2b2b2b;
                    color: #ffffff;
                    border: 1px solid #3a3a3a;
                    padding: 5px;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #3a3a3a;
                }
                QMenuBar {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QMenuBar::item:selected {
                    background-color: #3a3a3a;
                }
                QMenu {
                    background-color: #2b2b2b;
                    color: #ffffff;
                    border: 1px solid #3a3a3a;
                }
                QMenu::item:selected {
                    background-color: #3a3a3a;
                }
                QGroupBox {
                    border: 1px solid #3a3a3a;
                    margin-top: 0.5em;
                    padding-top: 0.5em;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 3px 0 3px;
                }
            """)
        else:
            self.setStyleSheet("""
                QMainWindow, QWidget {
                    background-color: #ffffff;
                    color: #333333;
                }
                QTextEdit, QPushButton, QLineEdit {
                    background-color: #f0f0f0;
                    color: #000000;
                    border: 1px solid #d0d0d0;
                    padding: 5px;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                }
                QMenuBar {
                    background-color: #f0f0f0;
                    color: #000000;
                }
                QMenuBar::item:selected {
                    background-color: #e0e0e0;
                }
                QMenu {
                    background-color: #f0f0f0;
                    color: #000000;
                    border: 1px solid #d0d0d0;
                }
                QMenu::item:selected {
                    background-color: #e0e0e0;
                }
                QGroupBox {
                    border: 1px solid #d0d0d0;
                    margin-top: 0.5em;
                    padding-top: 0.5em;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 3px 0 3px;
                }
            """)
        self.ai_research_assistant.update_style(self.is_dark_mode)

    def toggle_dark_mode(self):
        self.is_dark_mode = not self.is_dark_mode
        self.dark_mode_action.setChecked(self.is_dark_mode)
        self.apply_style()
        self.update_window_icon()
        if self.conversation_analysis_window:
            self.conversation_analysis_window.is_dark_mode = self.is_dark_mode  # Add this line
            self.conversation_analysis_window.apply_style(self.is_dark_mode)
        self.save_theme_preference()
        
        if sys.platform == "win32":
            self.set_window_dark_mode(self.is_dark_mode)

    def update_window_icon(self):
        pixmap = QPixmap(16, 16)
        color = QColor("#202020") if self.is_dark_mode else QColor("#f0f0f0")
        pixmap.fill(color)
        self.setWindowIcon(QIcon(pixmap))

    def set_window_dark_mode(self, enable):
        if sys.platform == "win32":
            try:
                from ctypes.wintypes import DWORD, BOOL, HRGN, HWND
                import ctypes

                class DWMWINDOWATTRIBUTE(ctypes.c_int):
                    DWMWA_USE_IMMERSIVE_DARK_MODE = 20

                class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
                    _fields_ = [
                        ("Attrib", ctypes.c_int),
                        ("pvData", ctypes.c_void_p),
                        ("cbData", ctypes.c_size_t)
                    ]

                user32 = ctypes.windll.user32
                dwmapi = ctypes.windll.dwmapi

                set_window_composition_attribute = user32.SetWindowCompositionAttribute
                set_window_composition_attribute.restype = BOOL
                set_window_composition_attribute.argtypes = [HWND, ctypes.POINTER(WINDOWCOMPOSITIONATTRIBDATA)]

                set_window_attribute = dwmapi.DwmSetWindowAttribute
                set_window_attribute.argtypes = (HWND, DWORD, ctypes.POINTER(DWORD), DWORD)
                set_window_attribute.restype = DWORD

                hwnd = self.winId().__int__()

                value = DWORD(enable)
                set_window_attribute(hwnd, DWMWINDOWATTRIBUTE.DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(value), ctypes.sizeof(value))

            except Exception as e:
                print(f"Error setting dark mode: {e}")

    def save_theme_preference(self):
        settings = QSettings("AIResearch", "ResearchTool")
        settings.setValue("darkMode", self.is_dark_mode)

    def load_theme_preference(self):
        settings = QSettings("AIResearch", "ResearchTool")
        return settings.value("darkMode", False, type=bool)

def main():
    app = QApplication(sys.argv)
    chat_app = ChatApplication()
    chat_app.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()