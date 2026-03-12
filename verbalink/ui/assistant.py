"""Main research assistant widget shown in the application's central area."""

import logging
import re

import ollama
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from ..threading import ThreadManager
from ..models import AIAgent
from ..workers import ConversationGenerator


class AIResearchAssistant(QWidget):
    new_chat_created = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.thread_manager = ThreadManager()
        self.agent1 = AIAgent(name="Sarah", persona="(default)")
        self.agent2 = AIAgent(name="Sam", persona="(default)")
        self.conversation_history = []
        self.is_dark_mode = False
        self.conversation_generator = None
        self.max_displayed_messages = 100  
        self.setup_ui()

    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)

        # Topic input
        topic_layout = QHBoxLayout()
        self.topic_input = QLineEdit()
        self.topic_input.setPlaceholderText("Enter conversation topic...")
        topic_layout.addWidget(QLabel("Topic:"))
        topic_layout.addWidget(self.topic_input)
        self.main_layout.addLayout(topic_layout)

        # Chat area
        self.chat_scroll_area = QScrollArea(self)
        self.chat_scroll_area.setWidgetResizable(True)
        self.chat_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.chat_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.chat_content = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_content)
        self.chat_layout.setContentsMargins(0, 0, 0, 0)
        self.chat_layout.setSpacing(10)
        self.chat_layout.setAlignment(Qt.AlignTop)
        self.chat_scroll_area.setWidget(self.chat_content)
        self.main_layout.addWidget(self.chat_scroll_area)
        
        # Add the disclaimer
        self.disclaimer_label = QLabel("Although we strive for accuracy, AI-generated content may still contain errors. Please verify key details before using it.")
        self.disclaimer_label.setStyleSheet("color: #999999; font-size: 10px;")
        self.disclaimer_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.disclaimer_label)

        # Control panel
        control_panel = QGroupBox("Conversation Controls")
        control_layout = QVBoxLayout(control_panel)

        # Message count input
        message_count_layout = QHBoxLayout()
        self.message_count_input = QLineEdit()
        self.message_count_input.setPlaceholderText("Number of messages (default: 20)")
        message_count_layout.addWidget(QLabel("Message Count:"))
        message_count_layout.addWidget(self.message_count_input)
        control_layout.addLayout(message_count_layout)

        # Buttons
        button_layout = QHBoxLayout()
        self.start_button = QPushButton("Start Conversation")
        self.start_button.clicked.connect(self.start_conversation)
        self.stop_button = QPushButton("Stop Conversation")
        self.stop_button.clicked.connect(self.stop_conversation)
        self.stop_button.setEnabled(False)
        self.continue_button = QPushButton("Continue Conversation")
        self.continue_button.clicked.connect(self.continue_conversation)
        self.continue_button.setEnabled(False)
        self.export_button = QPushButton("Export Conversation")
        self.export_button.clicked.connect(self.export_conversation)
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addWidget(self.continue_button)
        button_layout.addWidget(self.export_button)
        control_layout.addLayout(button_layout)

        self.main_layout.addWidget(control_panel)

    def start_conversation(self):
        if self.conversation_history:
            reply = QMessageBox.warning(self, "Existing Conversation",
                                        "Starting a new conversation will clear the current one. Are you sure you want to proceed?",
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No:
                return

        topic = self.topic_input.text().strip()
        if not topic:
            QMessageBox.warning(self, "No Topic", "Please enter a conversation topic.")
            return

        try:
            max_messages = int(self.message_count_input.text()) if self.message_count_input.text() else 20
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid number for message count.")
            return

        self.clear_chat()
        self.conversation_generator = ConversationGenerator(
            self.agent1,
            self.agent2,
            topic,
            max_messages=max_messages
        )
        self.conversation_thread = QThread()
        self.conversation_generator.moveToThread(self.conversation_thread)
        self.conversation_thread.started.connect(self.conversation_generator.run)
        self.conversation_generator.finished.connect(self.conversation_thread.quit)
        self.conversation_generator.finished.connect(self.conversation_finished)
        self.conversation_generator.error.connect(self.handle_error)
        self.conversation_generator.conversation_updated.connect(self.append_message)
        self.conversation_thread.start()

        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.continue_button.setEnabled(False)

    def stop_conversation(self):
        if self.conversation_generator:
            self.conversation_generator.stop()
            self.conversation_thread.quit()
            self.conversation_thread.wait()

    def continue_conversation(self):
        if not self.conversation_generator:
            QMessageBox.warning(self, "No Active Conversation", "There is no active conversation to continue.")
            return

        try:
            additional_messages = int(self.message_count_input.text()) if self.message_count_input.text() else 20
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid number for additional messages.")
            return

        self.conversation_generator.max_messages += additional_messages
        self.conversation_generator._stop_requested = False

        if not self.conversation_thread.isRunning():
            self.conversation_thread.start()

        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.continue_button.setEnabled(False)

    def conversation_finished(self):
        if self.conversation_thread:
            self.conversation_thread.quit()
            self.conversation_thread.wait()
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.continue_button.setEnabled(True)

    def handle_error(self, error_message):
        QMessageBox.warning(self, "Error", f"An error occurred: {error_message}")
        self.send_button.setEnabled(True)
        self.user_input.setEnabled(True)

    def append_message(self, sender, message):
        """Append a new message to the chat window with professional formatting."""
        self.conversation_history.append({'role': sender, 'content': message})
    
        message_widget = self.create_message_widget(sender, message)
        self.chat_layout.addWidget(message_widget)
    
        # Ensure newest messages are visible
        QTimer.singleShot(100, self.scroll_to_bottom)
    
        # Manage message history
        if self.chat_layout.count() > self.max_displayed_messages:
            self.cull_messages()
        
    def create_message_widget(self, sender, message):
        # Create a container widget that spans full width
        container = QWidget()
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
    
        # Create the actual message bubble widget
        message_widget = QWidget()
        message_widget.setMaximumWidth(int(self.chat_scroll_area.width() * 0.97))
    
        # Set size policy to allow proper expansion
        size_policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        message_widget.setSizePolicy(size_policy)
    
        message_layout = QVBoxLayout(message_widget)
        message_layout.setContentsMargins(10, 10, 10, 10)
        message_layout.setSpacing(5)

        # Header with sender and timestamp
        header_layout = QHBoxLayout()
        sender_label = QLabel(sender)
        sender_label.setStyleSheet("""
            font-weight: bold;
            font-size: 13px;
            color: #4a90e2;
        """)
        header_layout.addWidget(sender_label)
        header_layout.addStretch()

        timestamp = QDateTime.currentDateTime().toString("MM/dd/yyyy hh:mm:ss AP")
        timestamp_label = QLabel(timestamp)
        timestamp_label.setStyleSheet("color: #808080; font-size: 10px;")
        header_layout.addWidget(timestamp_label)
    
        message_layout.addLayout(header_layout)

        # Process and format message content first
        formatted_message = self.format_message_content(message)
        content_label = QLabel(formatted_message)
        content_label.setWordWrap(True)
        content_label.setTextFormat(Qt.RichText)
        content_label.setOpenExternalLinks(True)
        content_label.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)
        content_label.setMinimumWidth(int(message_widget.maximumWidth() * 0.97))
        message_layout.addWidget(content_label)

        # Apply bubble style
        is_ai = sender == self.agent1.name or sender == self.agent2.name
        self.apply_bubble_style(message_widget, is_ai)

        # Center the message widget in the container
        container_layout.addStretch(1)
        container_layout.addWidget(message_widget)
        container_layout.addStretch(1)

        return container

    def format_message_content(self, message):
        # Basic formatting with standard ASCII characters
        formatted = message.replace('\n\n', '<br><br>')
        formatted = formatted.replace('\n', '<br>')
    
        # Bold text
        formatted = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', formatted)
    
        # Italic text
        formatted = re.sub(r'\*(.*?)\*', r'<em>\1</em>', formatted)
    
        # Lists with basic hyphen
        formatted = re.sub(r'^-\s*(.*?)(?:<br>|$)',
            lambda m: f'<div style="margin-left: 20px; margin-bottom: 5px;"><span>-</span> {m.group(1)}</div>',
            formatted,
            flags=re.MULTILINE
        )
    
        # Numbered lists
        formatted = re.sub(r'^(\d+)\.\s*(.*?)(?:<br>|$)',
            lambda m: f'<div style="margin-left: 20px; margin-bottom: 5px;"><span>{m.group(1)}.</span> {m.group(2)}</div>',
            formatted,
            flags=re.MULTILINE
        )
    
        # Code blocks
        formatted = re.sub(r'```(.*?)```',
            lambda m: f'<pre><code>{m.group(1)}</code></pre>',
            formatted,
            flags=re.DOTALL
        )
    
        # Inline code
        formatted = re.sub(r'`(.*?)`',
            lambda m: f'<code>{m.group(1)}</code>',
            formatted
        )
    
        # Clean up extra spaces and line breaks
        formatted = re.sub(r'(?:<br>){3,}', '<br><br>', formatted)
        formatted = re.sub(r'<div>\s*<br>', '<div>', formatted)
        formatted = re.sub(r'<br>\s*</div>', '</div>', formatted)
    
        return formatted

    def apply_bubble_style(self, widget, is_ai):
        """Apply professional styling to message bubbles."""
        if is_ai:
            # AI message styling
            bubble_color = "#242424" if not self.is_dark_mode else "#242424"
            text_color = "#4b424f" if not self.is_dark_mode else "#dfe6e9"
            border_color = "#e9ecef" if not self.is_dark_mode else "#353b48"
        else:
            # User message styling
            bubble_color = "#242424" if not self.is_dark_mode else "#2c3e50"
            text_color = "#1976d2" if not self.is_dark_mode else "#dfe6e9"
            border_color = "#bbdefb" if not self.is_dark_mode else "#2980b9"

        widget.setStyleSheet(f"""
            QWidget {{
                background-color: {bubble_color};
                color: {text_color};
                border: 0px solid {border_color};
                border-radius: 10px;
            }}
            QLabel {{
                background-color: transparent;
                color: {text_color};
            }}
        """)
    
    def cull_messages(self):
        # Remove old messages from the display
        while self.chat_layout.count() > self.max_displayed_messages:
            item = self.chat_layout.takeAt(0)
            if item:
                widget = item.widget()
                if widget:
                    widget.setParent(None)
                    widget.deleteLater()

    def clear_chat(self):
        self.conversation_history = []
        while self.chat_layout.count():
            item = self.chat_layout.takeAt(0)
            if item:
                widget = item.widget()
                if widget:
                    widget.setParent(None)
                    widget.deleteLater()
        self.chat_layout.update()

    def apply_message_style(self, widget, sender):
        bg_color = "#3a3a3a" if self.is_dark_mode else "#f0f0f0"
        text_color = "#ffffff" if self.is_dark_mode else "#000000"
    
        widget.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_color};
                color: {text_color};
                border-radius: 15px;
                margin: 5px 0;
            }}
            QLabel {{
                background-color: transparent;
                color: {text_color};
            }}
        """)

    def scroll_to_bottom(self):
        self.chat_scroll_area.verticalScrollBar().setValue(
            self.chat_scroll_area.verticalScrollBar().maximum()
        )

    def clear_chat(self):
        self.conversation_history = []
        for i in reversed(range(self.chat_layout.count())):
            widget = self.chat_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

    def export_conversation(self):
        if not self.conversation_history:
            QMessageBox.warning(self, "No Conversation", "There is no conversation to export.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Export Conversation", "", "Text Files (*.txt)")
        if file_path:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"Topic: {self.topic_input.text()}\n\n")
                f.write(f"Agent 1: {self.agent1.name}\nPersona: {self.agent1.persona}\n\n")
                f.write(f"Agent 2: {self.agent2.name}\nPersona: {self.agent2.persona}\n\n")
                f.write("Conversation:\n")
                for message in self.conversation_history:
                    f.write(f"{message['role']}: {message['content']}\n")
            QMessageBox.information(self, "Export Successful", "Conversation exported successfully.")

    def update_style(self, is_dark_mode):
        self.is_dark_mode = is_dark_mode
        for i in range(self.chat_layout.count()):
            widget = self.chat_layout.itemAt(i).widget()
            if isinstance(widget, QWidget):
                sender = self.conversation_history[i]['role']
                self.apply_message_style(widget, sender)

    def get_conversation_text(self):
        return "\n\n".join([f"{msg['role']}: {msg['content']}" for msg in self.conversation_history])

    def reset_state(self):
        if self.conversation_thread and self.conversation_thread.isRunning():
            self.conversation_thread.quit()
            self.conversation_thread.wait()
        self.conversation_generator = None
        self.conversation_thread = None
        self.clear_chat()
        self.topic_input.clear()
        self.message_count_input.clear()
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.continue_button.setEnabled(False)

