"""Dialog windows used throughout the Verbalink UI."""

import logging
import re

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from .chrome import CustomTitleBarWindow
from ..workers import AnalysisWorker, ChatWorker


class ChatDialog(CustomTitleBarWindow):
    def __init__(self, parent, analysis_type, analysis_content):
        super().__init__(parent, f"{analysis_type} Discussion")
        self.parent = parent
        self.analysis_type = analysis_type
        self.analysis_content = analysis_content
        
        # Set a larger initial size and minimum size
        self.setGeometry(300, 200, 800, 600)  # Increased from default size
        self.setMinimumSize(600, 400)  # Set minimum size to prevent too-small window
        
        self.setup_ui()
        self.thread = None
        self.worker = None

    def setup_ui(self):
        layout = self.get_content_layout()
        layout.setContentsMargins(15, 15, 15, 15)  # Increased margins for better spacing
        layout.setSpacing(10)

        # Chat display area
        self.chat_scroll_area = QScrollArea()
        self.chat_scroll_area.setWidgetResizable(True)
        self.chat_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.chat_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.chat_content = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_content)
        self.chat_layout.setAlignment(Qt.AlignTop)
        self.chat_layout.setSpacing(12)  # Increased spacing between messages
        self.chat_layout.setContentsMargins(10, 10, 10, 10)
        
        self.chat_scroll_area.setWidget(self.chat_content)
        layout.addWidget(self.chat_scroll_area, stretch=1)  # Added stretch factor

        # Input area with better sizing
        input_layout = QHBoxLayout()
        input_layout.setSpacing(10)
        
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Type your message here...")
        self.user_input.setMinimumHeight(36)  # Increased height for better visibility
        
        self.send_button = QPushButton("Send")
        self.send_button.setMinimumWidth(80)  # Set minimum width for button
        self.send_button.setMinimumHeight(36)  # Match height with input field
        self.send_button.clicked.connect(self.send_message)
        
        input_layout.addWidget(self.user_input, stretch=1)  # Added stretch factor
        input_layout.addWidget(self.send_button)
        
        layout.addLayout(input_layout)

        self.apply_style()
        
        # Make input respond to Enter key
        self.user_input.returnPressed.connect(self.send_button.click)

    def apply_style(self):
        self.is_dark_mode = self.parent.is_dark_mode
        bg_color = "#242424" if self.is_dark_mode else "#ffffff"
        text_color = "#ffffff" if self.is_dark_mode else "#000000"
        input_bg_color = "#3a3a3a" if self.is_dark_mode else "#f0f0f0"
        button_color = "#4a4a4a" if self.is_dark_mode else "#e0e0e0"
        border_color = "#3a3a3a" if self.is_dark_mode else "#d0d0d0"

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_color};
                color: {text_color};
            }}
            QLineEdit {{
                background-color: {input_bg_color};
                color: {text_color};
                border: 1px solid {border_color};
                border-radius: 5px;
                padding: 5px 10px;
                font-size: 14px;
            }}
            QPushButton {{
                background-color: {button_color};
                color: {text_color};
                border: none;
                padding: 8px 20px;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {'#5a5a5a' if self.is_dark_mode else '#d0d0d0'};
            }}
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            QScrollArea > QWidget > QWidget {{
                background-color: transparent;
            }}
            QScrollBar:vertical {{
                background: {input_bg_color};
                width: 12px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {button_color};
                min-height: 20px;
                border-radius: 6px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar:horizontal {{
                background: {input_bg_color};
                height: 12px;
                margin: 0px;
            }}
            QScrollBar::handle:horizontal {{
                background: {button_color};
                min-width: 20px;
                border-radius: 6px;
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
        """)

    def update_style(self):
        super().update_style()
        self.apply_style()

    def send_message(self):
        user_message = self.user_input.text().strip()
        if user_message:
            self.add_message_bubble("You", user_message, is_user=True)
            self.user_input.clear()
            self.get_ai_response(user_message)

    def get_ai_response(self, user_message):
        system_prompt = f"""Your name is verbalink, You are an AI assistant helping users understand the {self.analysis_type} of a research conversation. 
        You have been provided with the {self.analysis_type} analysis.
        
        Your role is to help the user understand this {self.analysis_type}.
        - When referencing the analysis, be specific about which parts you're discussing
        - Explain concepts, clarify points, and answer questions about the analysis
        - If the user asks about methodology or reasoning, offer insights based on the analysis provided
        - Keep your responses focused on helping the user comprehend the analysis
        """

        self.thread = QThread()
        self.worker = ChatWorker(
            system_prompt, 
            user_message, 
            analysis_content=self.analysis_content,
            model='qwen2.5:7b'
        )
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.handle_ai_response)
        self.worker.error.connect(self.handle_error)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

        self.send_button.setEnabled(False)
        self.user_input.setEnabled(False)

    def handle_ai_response(self, ai_message):
        formatted_message = self.format_ai_message(ai_message)
        self.add_message_bubble("Verbalink", formatted_message, is_user=False)
        self.send_button.setEnabled(True)
        self.user_input.setEnabled(True)

    def handle_error(self, error_message):
        QMessageBox.warning(self, "Error", f"An error occurred: {error_message}")
        self.send_button.setEnabled(True)
        self.user_input.setEnabled(True)
        
    def format_conversation_chunks(self):
        return "\n\n".join(self.conversation_chunks)

    def format_ai_message(self, message):
        """
        Format AI message with proper styling
        """
        formatted = message.replace('\n', '<br>')
        formatted = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', formatted)
        formatted = re.sub(r'\*(.*?)\*', r'<em>\1</em>', formatted)
        formatted = re.sub(r'^- (.*)$', r'- \1', formatted, flags=re.MULTILINE)  # Using simple hyphen
        formatted = re.sub(r'^(\d+)\. (.*)$', lambda m: f"{m.group(1)}. {m.group(2)}", formatted, flags=re.MULTILINE)
        formatted = re.sub(r'```(.*?)```', r'<pre><code>\1</code></pre>', formatted, flags=re.DOTALL)
        formatted = re.sub(r'`(.*?)`', r'<code>\1</code>', formatted)
        return formatted

    def add_message_bubble(self, sender, message, is_user):
        bubble = QWidget()
        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(10, 10, 10, 10)
        bubble_layout.setSpacing(5)

        # Header (sender and timestamp)
        header_layout = QHBoxLayout()
        sender_label = QLabel(sender)
        sender_label.setStyleSheet(f"font-weight: bold; color: {'#ffffff' if self.is_dark_mode else '#000000'};")
        timestamp = QDateTime.currentDateTime().toString("MM/dd/yyyy hh:mm:ss AP")
        timestamp_label = QLabel(timestamp)
        timestamp_label.setStyleSheet("color: #808080; font-size: 10px;")
        header_layout.addWidget(sender_label)
        header_layout.addStretch()
        header_layout.addWidget(timestamp_label)
        bubble_layout.addLayout(header_layout)

        # Message content
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setTextFormat(Qt.RichText)
        message_label.setOpenExternalLinks(True)
        message_label.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)
        bubble_layout.addWidget(message_label)

        # Style the bubble
        bubble_color = "#3a3a3a" if self.is_dark_mode else "#f0f0f0"
        text_color = "#ffffff" if self.is_dark_mode else "#000000"
        user_bubble_color = "#4a4a4a" if self.is_dark_mode else "#e0e0e0"
        
        if is_user:
            bubble_color = user_bubble_color
        
        bubble.setStyleSheet(f"""
            QWidget {{
                background-color: {bubble_color};
                border-radius: 10px;
            }}
            QLabel {{
                background-color: transparent;
                color: {text_color};
            }}
        """)

        message_label.setStyleSheet(f"""
            QLabel {{
                color: {text_color};
            }}
            code {{
                background-color: {'#2b2b2b' if self.is_dark_mode else '#f8f8f8'};
                color: {'#e6e6e6' if self.is_dark_mode else '#333333'};
                padding: 2px 4px;
                border-radius: 3px;
                font-family: monospace;
            }}
            pre {{
                background-color: {'#2b2b2b' if self.is_dark_mode else '#f8f8f8'};
                color: {'#e6e6e6' if self.is_dark_mode else '#333333'};
                padding: 10px;
                border-radius: 5px;
                font-family: monospace;
                white-space: pre-wrap;
            }}
        """)

        self.chat_layout.addWidget(bubble)
        self.scroll_to_bottom()

    def scroll_to_bottom(self):
        self.chat_scroll_area.verticalScrollBar().setValue(
            self.chat_scroll_area.verticalScrollBar().maximum()
        )


class AgentConfigDialog(CustomTitleBarWindow):
    configUpdated = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent, "Configure Agents")
        self.parent = parent
        self.setGeometry(300, 300, 600, 500)
        self._closed = False  # Add flag to track window state
        self.setup_ui()
        self.apply_style()

    def setup_ui(self):
        layout = self.get_content_layout()
        layout.setSpacing(10)
        
        self.agent1_layout = QFormLayout()
        self.agent2_layout = QFormLayout()
        
        self.agent1_name = QLineEdit()
        self.agent1_persona = QTextEdit()
        self.agent1_persona.setPlaceholderText("Describe Agent 1's personality, background, and beliefs...")
        
        self.agent2_name = QLineEdit()
        self.agent2_persona = QTextEdit()
        self.agent2_persona.setPlaceholderText("Describe Agent 2's personality, background, and beliefs...")
        
        self.agent1_layout.addRow("Agent 1 Name:", self.agent1_name)
        self.agent1_layout.addRow("Agent 1 Persona:", self.agent1_persona)
        
        self.agent2_layout.addRow("Agent 2 Name:", self.agent2_name)
        self.agent2_layout.addRow("Agent 2 Persona:", self.agent2_persona)
        
        # Theme dropdown
        self.theme_layout = QHBoxLayout()
        self.theme_label = QLabel("Theme:")
        self.theme_dropdown = QComboBox()
        self.theme_dropdown.addItems([
            "Debate", "Scientific Research", "Conversational Study", "Linguistics",
            "Scientific Discourse", "Political Debate", "Ideology Study",
            "Historical Analysis", "Social Research", "Academic Lecture",
            "Philosophy", "Technology", "Ethics", "Economics", "Psychology",
            "Anthropology", "Environmental Studies", "Literature", "Art Criticism",
            "Medical Research", "Legal Discourse", "Religious Studies"
        ])
        self.theme_layout.addWidget(self.theme_label)
        self.theme_layout.addWidget(self.theme_dropdown)
        
        # Generate button
        self.generate_button = QPushButton("Generate")
        self.generate_button.clicked.connect(self.generate_agents)
        
        # Group boxes for better organization
        self.agent1_group = QGroupBox("Agent 1")
        self.agent1_group.setLayout(self.agent1_layout)
        self.agent2_group = QGroupBox("Agent 2")
        self.agent2_group.setLayout(self.agent2_layout)
        
        layout.addWidget(self.agent1_group)
        layout.addWidget(self.agent2_group)
        layout.addLayout(self.theme_layout)
        layout.addWidget(self.generate_button)
        
        buttons = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")
        self.clear_button = QPushButton("Clear All Fields")
        buttons.addWidget(self.ok_button)
        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.clear_button)
        
        layout.addLayout(buttons)
        
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        self.clear_button.clicked.connect(self.clear_fields)

        self.load_config()

    def apply_style(self):
        is_dark_mode = self.parent.is_dark_mode if self.parent else False
        bg_color = "#2b2b2b" if is_dark_mode else "#ffffff"
        text_color = "#ffffff" if is_dark_mode else "#000000"
        input_bg_color = "#3a3a3a" if is_dark_mode else "#f0f0f0"
        border_color = "#4a4a4a" if is_dark_mode else "#d0d0d0"
        group_border_color = "#3a3a3a" if is_dark_mode else "#d0d0d0"

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_color};
                color: {text_color};
            }}
            QLineEdit, QTextEdit, QComboBox {{
                background-color: {input_bg_color};
                color: {text_color};
                border: 1px solid {border_color};
                border-radius: 5px;
                padding: 5px;
            }}
            QPushButton {{
                background-color: {input_bg_color};
                color: {text_color};
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
            }}
            QPushButton:hover {{
                background-color: {'#4a4a4a' if is_dark_mode else '#e0e0e0'};
            }}
            QGroupBox {{
                border: 1px solid {group_border_color};
                border-radius: 5px;
                margin-top: 1em;
                padding-top: 0.5em;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
                color: {text_color};
            }}
            QLabel {{
                color: {text_color};
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {text_color};
                margin-right: 5px;
            }}
        """)

        # Update title bar style
        self.update_style()

    def clear_fields(self):
        self.agent1_name.clear()
        self.agent1_persona.clear()
        self.agent2_name.clear()
        self.agent2_persona.clear()
        self.save_config()

    def load_config(self):
        settings = QSettings("AIResearch", "AgentConfig")
        self.agent1_name.setText(settings.value("agent1_name", "", type=str))
        self.agent1_persona.setPlainText(settings.value("agent1_persona", "", type=str))
        self.agent2_name.setText(settings.value("agent2_name", "", type=str))
        self.agent2_persona.setPlainText(settings.value("agent2_persona", "", type=str))

    def save_config(self):
        settings = QSettings("AIResearch", "AgentConfig")
        settings.setValue("agent1_name", self.agent1_name.text())
        settings.setValue("agent1_persona", self.agent1_persona.toPlainText())
        settings.setValue("agent2_name", self.agent2_name.text())
        settings.setValue("agent2_persona", self.agent2_persona.toPlainText())

    def closeEvent(self, event):
        if not self._closed:
            self._closed = True
            self.save_config()
            self.hide()
            self.deleteLater()
        event.accept()

    def accept(self):
        self.save_config()
        self.configUpdated.emit()
        self.closeEvent(QCloseEvent())

    def reject(self):
        self.save_config()
        self.closeEvent(QCloseEvent())

    def close(self):
        self.closeEvent(QCloseEvent())

    def generate_agents(self):
        theme = self.theme_dropdown.currentText()
        prompt = f"Generate two detailed agent profiles for a {theme} conversation. DO NOT ADD EXTRA ADDED SIDE COMMENTARY OF YOUR OWN, OR ANYHTING THAT WAS NOT DIRECTLY REQUESTED - do not fucking add your own thoughts and input just do the requested task."

        response = ollama.chat(model='qwen2.5:7b', messages=[
            {'role': 'system', 'content': 'FOLLOW THE DIRECTIONS EXPLICITLY.'},
            {'role': 'user', 'content': prompt}
        ])

        generated_content = response['message']['content']
    
        # Split content into two profiles
        agent_profiles = generated_content.split("Agent")[1:] if "Agent" in generated_content else generated_content.split("Profile")[1:]
    
        if len(agent_profiles) >= 2:
            # Process Agent 1
            self.set_agent_profile(self.agent1_name, self.agent1_persona, agent_profiles[0])
            # Process Agent 2
            self.set_agent_profile(self.agent2_name, self.agent2_persona, agent_profiles[1])

    def clean_text(self, text):
        # First remove all markdown asterisks and formatting
        text = re.sub(r'\*+', '', text)  # Remove all asterisks
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Remove bold
        text = re.sub(r'\*(.*?)\*', r'\1', text)  # Remove italic
        text = re.sub(r'`(.*?)`', '', text)  # Remove code blocks entirely
        text = re.sub(r'#+\s*', '', text)  # Remove headers
        text = re.sub(r'\[.*?\]', '', text)  # Remove square brackets
        text = re.sub(r'\(.*?\)', '', text)  # Remove parentheses if needed

        # Remove list markers and standardize
        text = re.sub(r'^\s*[-+*]\s*', '- ', text, flags=re.MULTILINE)  # Convert list markers to simple hyphen

        # Clean up numbers at start of lines
        text = re.sub(r'^\s*\d+[:.]?\s*', '', text, flags=re.MULTILINE)

        # Remove quotes and other special characters
        text = text.replace('"', '')
        text = text.replace('"', '')
        text = text.replace('"', '')
        text = text.replace(''', "'")
        text = text.replace(''', "'")
        text = text.replace('–', '-')
        text = text.replace('—', '-')
        text = text.replace('…', '...')

        # Clean up spacing and lines
        text = re.sub(r'\n\s*\n', '\n\n', text)  # Standardize line spacing
        text = re.sub(r' +', ' ', text)  # Remove multiple spaces
        text = text.strip()

        return text

    def parse_and_format_profile(self, text):
        # Remove any remaining profile markers
        text = re.sub(r'(?:Profile|Agent)\s*\d*\s*:', '', text)
    
        # Split into sections
        sections = {
            'Background': '',
            'Personality': '',
            'Goals': '',
            'Key Strengths': '',
            'Weaknesses': ''
        }
    
        current_section = None
        lines = []
    
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Check if this is a section header
            for section in sections.keys():
                if section.lower() in line.lower():
                    current_section = section
                    break
        
            if current_section and line:
                if sections[current_section]:
                    sections[current_section] += '\n'
                sections[current_section] += line
    
        # Format the final output
        formatted = []
        for section, content in sections.items():
            if content:
                formatted.append(f"{section}:\n{content}\n")
    
        return '\n'.join(formatted)

    def extract_content(self, text, tag):
        import re
        pattern = f"<{tag}>(.*?)</{tag}>"
        match = re.search(pattern, text, re.DOTALL)
        extracted = match.group(1).strip() if match else ""
        logging.debug(f"Extracting {tag}: {'Success' if extracted else 'Failed'}")
        return extracted

    def set_agent_profile(self, name_widget, persona_widget, profile_text):
        # Clean the entire text first
        cleaned_text = self.clean_text(profile_text)
    
        # Extract and set name
        name_match = re.search(r'(?:Name:|Profile\s*\d*:?\s*)(.*?)(?:\n|$)', cleaned_text, re.IGNORECASE)
        if name_match:
            clean_name = name_match.group(1).strip()
            name_widget.setText(clean_name)
    
        # Format and set persona
        formatted_persona = self.parse_and_format_profile(cleaned_text)
        persona_widget.setPlainText(formatted_persona)

    def format_persona(self, text):
        # Ensure consistent newlines
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Ensure single blank line between sections
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Ensure colon after main labels
        text = re.sub(r'^(Persona|Description|Background|Beliefs)(?:\s*)(?!:)', r'\1:', text, flags=re.MULTILINE)
        
        # Ensure proper spacing for bullet points
        text = re.sub(r'^(\s*-\s*)', r'\n\1', text, flags=re.MULTILINE)
        
        # Remove any leading/trailing whitespace
        text = text.strip()
        
        return text

    
    
    def apply_style(self):
        is_dark_mode = self.parent.is_dark_mode if self.parent else False
        
        if is_dark_mode:
            self.setStyleSheet("""
                QDialog {
                    background-color: #1e1e1e;
                    color: #ffffff;
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
                QLineEdit, QTextEdit, QComboBox {
                    background-color: #2b2b2b;
                    color: #ffffff;
                    border: 1px solid #3a3a3a;
                    padding: 5px;
                    border-radius: 5px;
                }
                QPushButton {
                    background-color: #2b2b2b;
                    color: #ffffff;
                    border: 1px solid #3a3a3a;
                    padding: 5px 15px;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #3a3a3a;
                }
            """)
        else:
            self.setStyleSheet("""
                QDialog {
                    background-color: #ffffff;
                    color: #333333;
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
                QLineEdit, QTextEdit, QComboBox {
                    background-color: #f0f0f0;
                    color: #000000;
                    border: 1px solid #d0d0d0;
                    padding: 5px;
                    border-radius: 5px;
                }
                QPushButton {
                    background-color: #f0f0f0;
                    color: #000000;
                    border: 1px solid #d0d0d0;
                    padding: 5px 15px;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                }
            """)

        # Set fonts
        font = QFont()
        font.setPointSize(10)
        self.setFont(font)

        title_font = QFont()
        title_font.setPointSize(11)
        title_font.setBold(True)
        self.agent1_group.setFont(title_font)
        self.agent2_group.setFont(title_font)


class ConversationAnalysisWindow(CustomTitleBarWindow):
    def __init__(self, parent=None):
        super().__init__(parent, "Research Conversation Analysis")
        self.parent = parent
        self.setGeometry(200, 200, 800, 600)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.chat_dialogs = {}
        self.analysis_worker = None
        self.conversation_chunks = []
        self.setup_ui()

    def setup_ui(self):
        layout = self.get_content_layout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # Create text edits for each analysis type
        self.summary_text = self.create_styled_text_edit()
        self.insights_text = self.create_styled_text_edit()
        self.thematic_text = self.create_styled_text_edit()
        self.flow_text = self.create_styled_text_edit()
        self.nuanced_text = self.create_styled_text_edit()
        self.sentiment_text = self.create_styled_text_edit()

        # Create tabs with associated chat buttons
        self.setup_analysis_tab("Executive Summary", self.summary_text)
        self.setup_analysis_tab("Key Insights", self.insights_text)
        self.setup_analysis_tab("Thematic Analysis", self.thematic_text)
        self.setup_analysis_tab("Conversation Flow", self.flow_text)
        self.setup_analysis_tab("Nuanced Ideas", self.nuanced_text)
        self.setup_analysis_tab("Sentiment Analysis", self.sentiment_text)

        # Add the disclaimer
        self.disclaimer_label = QLabel("Although we strive for precision, AI-generated content may occasionally have errors. Please confirm key details independently.")
        self.disclaimer_label.setStyleSheet("color: #999999; font-size: 9px;")
        self.disclaimer_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.disclaimer_label)

        # Control panel
        control_panel = QHBoxLayout()

        self.analyze_button = QPushButton("Run Full Evaluation")
        self.analyze_button.clicked.connect(self.start_analysis)
        control_panel.addWidget(self.analyze_button)

        self.run_current_button = QPushButton("Run Analysis")
        self.run_current_button.clicked.connect(self.run_current_analysis)
        control_panel.addWidget(self.run_current_button)

        layout.addLayout(control_panel)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

    def setup_analysis_tab(self, tab_name, text_edit):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(text_edit)
        
        chat_button = QPushButton(f"Discuss {tab_name}")
        chat_button.clicked.connect(lambda: self.open_analysis_chat(tab_name))
        layout.addWidget(chat_button)
        
        self.tab_widget.addTab(container, tab_name)

    def create_styled_text_edit(self):
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        return text_edit

    def open_analysis_chat(self, analysis_type):
        text_edit = self.get_text_edit_for_type(analysis_type)
        analysis_content = text_edit.toPlainText()
        
        if not analysis_content:
            QMessageBox.warning(self, "No Analysis", f"No {analysis_type} analysis available yet.")
            return
            
        if analysis_type not in self.chat_dialogs or self.chat_dialogs[analysis_type].isHidden():
            chat_dialog = ChatDialog(self, analysis_type, analysis_content)
            self.chat_dialogs[analysis_type] = chat_dialog
            chat_dialog.show()
        else:
            self.chat_dialogs[analysis_type].activateWindow()

    def get_text_edit_for_type(self, analysis_type):
        type_map = {
            "Executive Summary": self.summary_text,
            "Key Insights": self.insights_text,
            "Thematic Analysis": self.thematic_text,
            "Conversation Flow": self.flow_text,
            "Nuanced Ideas": self.nuanced_text,
            "Sentiment Analysis": self.sentiment_text
        }
        return type_map.get(analysis_type)

    def start_analysis(self):
        conversation = self.parent.ai_research_assistant.get_conversation_text()
        if not conversation:
            QMessageBox.warning(self, "No Conversation", "There is no research conversation to analyze.")
            return

        self.analysis_worker = AnalysisWorker(conversation)
        self.analysis_worker.analysis_complete.connect(self.update_analysis_results)
        self.analysis_worker.progress_update.connect(self.update_progress)
        self.analysis_worker.chunks_ready.connect(self.set_conversation_chunks)
        self.analysis_worker.start()
        
        self.analyze_button.setEnabled(False)
        self.run_current_button.setEnabled(False)
        self.progress_bar.setValue(0)

    def run_current_analysis(self):
        current_tab = self.tab_widget.currentIndex()
        conversation = self.parent.ai_research_assistant.get_conversation_text()
        if not conversation:
            QMessageBox.warning(self, "No Conversation", "There is no research conversation to analyze.")
            return

        analysis_type = self.get_analysis_type(current_tab)
        self.analysis_worker = SingleAnalysisWorker(conversation, analysis_type)
        self.analysis_worker.analysis_complete.connect(self.update_single_analysis_result)
        self.analysis_worker.progress_update.connect(self.update_progress)
        
        self.conversation_chunks = [conversation]
        
        self.analysis_worker.start()
        self.analyze_button.setEnabled(False)
        self.run_current_button.setEnabled(False)
        self.progress_bar.setValue(0)

    def get_analysis_type(self, tab_index):
        analysis_types = ['summary', 'insights', 'thematic', 'flow', 'nuanced', 'sentiment']
        return analysis_types[tab_index]

    def update_analysis_results(self, results):
        self.summary_text.setHtml(self.format_text(results['summary'], "Executive Summary"))
        self.insights_text.setHtml(self.format_text(results['insights'], "Key Insights"))
        self.thematic_text.setHtml(self.format_text(results['thematic'], "Thematic Analysis"))
        self.flow_text.setHtml(self.format_text(results['flow'], "Conversation Flow"))
        self.nuanced_text.setHtml(self.format_text(results['nuanced'], "Nuanced Ideas"))
        self.sentiment_text.setHtml(self.format_text(results['sentiment'], "Sentiment Analysis"))

        # Update any active chat dialogs with new content
        for analysis_type, dialog in self.chat_dialogs.items():
            if not dialog.isHidden():
                text_edit = self.get_text_edit_for_type(analysis_type)
                if text_edit:
                    dialog.analysis_content = text_edit.toPlainText()

        self.analyze_button.setEnabled(True)
        self.run_current_button.setEnabled(True)
        self.progress_bar.setValue(100)

    def update_single_analysis_result(self, result):
        analysis_type, content = result
        text_edit = getattr(self, f"{analysis_type}_text")
        text_edit.setHtml(self.format_text(content, self.tab_widget.tabText(self.tab_widget.currentIndex())))

        # Update chat dialog if it exists and is visible
        if analysis_type in self.chat_dialogs and not self.chat_dialogs[analysis_type].isHidden():
            self.chat_dialogs[analysis_type].analysis_content = content

        self.analyze_button.setEnabled(True)
        self.run_current_button.setEnabled(True)
        self.progress_bar.setValue(100)

    def format_text(self, text, title):
        formatted_text = f"""
        <h1>{title}</h1>
        {self.process_content(text)}
        """
        return formatted_text

    def process_content(self, content):
        # Convert markdown-style lists to HTML lists
        lines = content.split('\n')
        in_list = False
        processed_lines = []

        for line in lines:
            if line.strip().startswith('- '):
                if not in_list:
                    processed_lines.append('<ul>')
                    in_list = True
                processed_lines.append(f'<li>{line.strip()[2:]}</li>')
            else:
                if in_list:
                    processed_lines.append('</ul>')
                    in_list = False
                processed_lines.append(f'<p>{line}</p>')

        if in_list:
            processed_lines.append('</ul>')

        # Convert markdown-style bold and italic to HTML
        processed_content = '\n'.join(processed_lines)
        processed_content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', processed_content)
        processed_content = re.sub(r'\*(.*?)\*', r'<em>\1</em>', processed_content)

        return processed_content

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def set_conversation_chunks(self, chunks):
        self.conversation_chunks = chunks

    def apply_style(self, is_dark_mode):
        self.is_dark_mode = is_dark_mode
        bg_color = "#2b2b2b" if is_dark_mode else "#ffffff"
        text_color = "#ffffff" if is_dark_mode else "#333333"
        border_color = "#3a3a3a" if is_dark_mode else "#d0d0d0"
        progress_color = "#808080"

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_color};
                color: {text_color};
            }}
            QTextEdit {{
                background-color: {bg_color};
                color: {text_color};
                border: 1px solid {border_color};
                padding: 10px;
                border-radius: 5px;
            }}
            QPushButton {{
                background-color: {border_color};
                color: {text_color};
                border: 1px solid {border_color};
                padding: 8px 15px;
                border-radius: 5px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {'#4a4a4a' if is_dark_mode else '#e0e0e0'};
            }}
            QTabWidget::pane {{
                border: 1px solid {border_color};
            }}
            QTabBar::tab {{
                background-color: {bg_color};
                color: {text_color};
                padding: 10px 20px;
                border: 1px solid {border_color};
                border-bottom: none;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }}
            QTabBar::tab:selected {{
                background-color: {'#3a3a3a' if is_dark_mode else '#f0f0f0'};
                border-bottom: 2px solid {progress_color};
            }}
            QProgressBar {{
                border: 1px solid {border_color};
                border-radius: 0px;
                text-align: center;
                color: {text_color};
                background-color: {bg_color};
            }}
            QProgressBar::chunk {{
                background-color: {progress_color};
                width: 1px;
            }}
        """)

        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {border_color};
                border-radius: 0px;
                text-align: center;
                color: {text_color};
                background-color: {bg_color};
            }}
            QProgressBar::chunk {{
                background-color: {progress_color};
                width: 1px;
            }}
        """)

    def closeEvent(self, event):
        # Clean up all active chat dialogs
        for dialog in self.chat_dialogs.values():
            dialog.close()
        if self.analysis_worker and self.analysis_worker.isRunning():
            self.analysis_worker.terminate()
        event.accept()   
        
