# -*- coding: utf-8 -*-

import sys
import re
import logging
import ollama
import time
import json
import os
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
import tempfile
import os

logging.basicConfig(filename='ai_research_log.txt', level=logging.DEBUG, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

class ThreadManager(QObject):
    def __init__(self):
        super().__init__()
        self.threads = []

    def start_thread(self, worker_class, *args, **kwargs):
        thread = QThread()
        worker = worker_class(*args, **kwargs)
        self.threads.append((thread, worker))
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self.remove_thread(thread))
        thread.start()
        return worker

    def remove_thread(self, thread):
        self.threads = [(t, w) for t, w in self.threads if t != thread]

    def stop_all_threads(self):
        for thread, worker in self.threads:
            if hasattr(worker, 'stop'):
                worker.stop()
            thread.quit()
            thread.wait()
            
class CustomTitleBar(QWidget):
    def __init__(self, parent=None, title="", enable_maximize=True):
        super().__init__(parent)
        self.parent = parent
        self.enable_maximize = enable_maximize
        self.is_pressed = False
        self.start_pos = None
        self.setup_ui(title)

    def setup_ui(self, title):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(5)

        # Title label
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-weight: bold;")

        # Window controls
        btn_size = 16
        self.minimize_btn = QPushButton("─")
        self.minimize_btn.setFixedSize(btn_size, btn_size)
        self.minimize_btn.clicked.connect(self.parent.showMinimized)
        self.minimize_btn.setAutoDefault(False)
        self.minimize_btn.setDefault(False)

        if self.enable_maximize:
            self.maximize_btn = QPushButton("□")
            self.maximize_btn.setFixedSize(btn_size, btn_size)
            self.maximize_btn.clicked.connect(self.toggle_maximize)
            self.maximize_btn.setAutoDefault(False)
            self.maximize_btn.setDefault(False)

        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(btn_size, btn_size)
        self.close_btn.clicked.connect(self.parent.close)
        self.close_btn.setAutoDefault(False)
        self.close_btn.setDefault(False)

        # Add widgets to layout
        layout.addWidget(self.title_label)
        layout.addStretch()
        layout.addWidget(self.minimize_btn)
        if self.enable_maximize:
            layout.addWidget(self.maximize_btn)
        layout.addWidget(self.close_btn)

        self.update_style()

        # Set focus policy to prevent focus
        self.setFocusPolicy(Qt.NoFocus)
        self.minimize_btn.setFocusPolicy(Qt.NoFocus)
        if self.enable_maximize:
            self.maximize_btn.setFocusPolicy(Qt.NoFocus)
        self.close_btn.setFocusPolicy(Qt.NoFocus)

    def update_style(self):
        is_dark = self.parent.is_dark_mode if hasattr(self.parent, 'is_dark_mode') else False
        bg_color = "#1e1e1e" if is_dark else "#f0f0f0"
        text_color = "#ffffff" if is_dark else "#525252"
        button_hover = "#3a3a3a" if is_dark else "#e0e0e0"
        close_hover = "#c42b1c"

        self.setStyleSheet(f"""
            CustomTitleBar {{
                background-color: {bg_color};
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }}
            QLabel {{
                color: {text_color};
                background: transparent;
            }}
            QPushButton {{
                background: transparent;
                border: none;
                color: {text_color};
                border-radius: 2px;
                padding: 2px;
            }}
            QPushButton:hover {{
                background: {button_hover};
            }}
            QPushButton#closeButton:hover {{
                background: {close_hover};
                color: white;
            }}
        """)
        self.close_btn.setObjectName("closeButton")

    def toggle_maximize(self):
        if self.parent.isMaximized():
            self.parent.showNormal()
            self.maximize_btn.setText("□")
        else:
            self.parent.showMaximized()
            self.maximize_btn.setText("❐")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_pressed = True
            self.start_pos = event.globalPos()

    def mouseReleaseEvent(self, event):
        self.is_pressed = False
        self.start_pos = None

    def mouseMoveEvent(self, event):
        if self.is_pressed:
            if self.start_pos is not None:
                move = event.globalPos() - self.start_pos
                self.parent.move(self.parent.pos() + move)
                self.start_pos = event.globalPos()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            event.ignore()
        else:
            super().keyPressEvent(event)


class CustomTitleBarWindow(QDialog):
    def __init__(self, parent=None, title="", enable_maximize=True):
        super().__init__(parent, Qt.Window | Qt.FramelessWindowHint)
        self.parent = parent
        self.setup_window(title, enable_maximize)

    def setup_window(self, title, enable_maximize):
        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Custom title bar
        self.title_bar = CustomTitleBar(self, title, enable_maximize)
        self.main_layout.addWidget(self.title_bar)

        # Content widget
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.main_layout.addWidget(self.content_widget)

        # Apply window shadow
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(20)
        self.shadow.setOffset(0, 0)
        self.shadow.setColor(QColor(0, 0, 0, 100))
        self.setGraphicsEffect(self.shadow)

    def update_style(self):
        is_dark = self.parent.is_dark_mode if hasattr(self.parent, 'is_dark_mode') else False
        bg_color = "#2b2b2b" if is_dark else "#ffffff"
        border_color = "#3a3a3a" if is_dark else "#d0d0d0"

        self.setStyleSheet(f"""
            CustomTitleBarWindow {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 5px;
            }}
        """)
        self.title_bar.update_style()

    def get_content_layout(self):
        return self.content_layout

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            event.ignore()
        else:
            super().keyPressEvent(event)

    def nativeEvent(self, eventType, message):
        retval, result = super().nativeEvent(eventType, message)
        return retval, result

class ChatWorker(QObject):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, system_prompt, user_message, analysis_content, model='phi4:14b'):
        super().__init__()
        self.system_prompt = system_prompt
        self.user_message = user_message
        self.analysis_content = analysis_content
        self.model = model

    def run(self):
        try:
            messages = [
                {'role': 'system', 'content': self.system_prompt},
                {'role': 'user', 'content': f"Analysis Content:\n{self.analysis_content}\n\nUser Question: {self.user_message}"}
            ]
            response = ollama.chat(model=self.model, messages=messages)
            ai_message = response['message']['content']
            self.finished.emit(ai_message)
        except Exception as e:
            self.error.emit(str(e))

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

class SingleAnalysisWorker(QThread):
    analysis_complete = pyqtSignal(tuple)
    progress_update = pyqtSignal(int)

    def __init__(self, conversation, analysis_type):
        super().__init__()
        self.conversation = conversation
        self.analysis_type = analysis_type
        self.max_tokens = 100000
        self.words_per_token = 0.65

    def run(self):
        result = {}
    
        total_words = self.word_count(self.conversation)
        estimated_tokens = int(total_words / self.words_per_token)
    
        if estimated_tokens <= self.max_tokens:
            chunks = [self.conversation]
        else:
            chunks = self.split_conversation(self.conversation)
    
        self.progress_update.emit(10)
    
        analysis_function = getattr(self, f"generate_{self.analysis_type}")
        result = self.process_chunks(chunks, analysis_function, self.analysis_type.capitalize(), 10, 90)
    
        self.analysis_complete.emit((self.analysis_type, result))
        self.progress_update.emit(100)

    def word_count(self, text):
        return len(re.findall(r'\w+', text))

    def split_conversation(self, conversation):
        chunks = []
        lines = conversation.split('\n')
        current_chunk = []
        current_word_count = 0
        
        for line in lines:
            line_word_count = self.word_count(line)
            if current_word_count + line_word_count > int(self.max_tokens * self.words_per_token):
                chunks.append('\n'.join(current_chunk))
                current_chunk = []
                current_word_count = 0
            
            current_chunk.append(line)
            current_word_count += line_word_count
        
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
        
        return chunks

    def process_chunks(self, chunks, analysis_function, title, progress_start, progress_end):
        results = []
    
        for i, chunk in enumerate(chunks):
            result = analysis_function(chunk)
            results.append(result)
            progress = progress_start + int((i + 1) / len(chunks) * (progress_end - progress_start))
            self.progress_update.emit(progress)
    
        if len(chunks) > 1:
            combined_result = self.synthesize_results(results, title)
        else:
            combined_result = results[0]
    
        return combined_result

    def synthesize_results(self, results, analysis_type):
        combine_prompt = f"""
        Give a highly detailed synthesis the following {analysis_type} results into a coherent narrative:

        {' '.join(results)}

        Use this structured template for your synthesis output, ensuring to maintain attention to detail:

        [*{analysis_type.upper()} SYNTHESIS*]
    
        1. **Summary:** Provide a brief overview of the combined {analysis_type} results, incorporating detailed observations.
    
        2. **Key Takeaways:** Highlight the most critical conclusions drawn from the synthesis with specific examples.
    
        3. **Future Directions:** Suggest potential avenues for further exploration based on the synthesis, paying close attention to detail.
    
        [END_{analysis_type.upper()}_SYNTHESIS]
        """
        response = ollama.chat(model='qwen2.5:7b', messages=[
            {'role': 'system', 'content': f'You are skilled at synthesizing {analysis_type} information. Follow the specified template in your synthesis output and focus on detail.'},
            {'role': 'user', 'content': combine_prompt}
        ])
        return response['message']['content']

    def generate_summary(self, chunk):
        summary_prompt = f"""
        Analyze the following research conversation segment and provide a comprehensive and in-depth summary of the main points:

        {chunk}

        Summarize in 5-7 sentences, ensuring to capture all relevant details and nuances of the discussion. Please **do not stray from the content's details**; focus closely on the specifics of the conversation.

        Use the following structured template for your output:

        [*SUMMARY*]
    
        1. **Key Points:** Clearly and thoroughly outline the primary ideas discussed, including any sub-points that are significant.
    
        2. **Implications:** Discuss the significance or potential impact of these points, considering how they relate to the broader research context.
    
        3. **Recommendations:** If applicable, provide detailed suggestions or next steps based on the insights drawn from the conversation.
    
        4. **Contextual Factors:** Note any relevant contextual elements that may influence the interpretation of these points.
        """
        response = ollama.chat(model='qwen2.5:7b', messages=[
            {'role': 'system', 'content': 'You are an expert analyst. Please follow the specified template for your summary output and pay close attention to detail.'},
            {'role': 'user', 'content': summary_prompt}
        ])
        return response['message']['content']

    def generate_insights(self, chunk):
        insights_prompt = f"""
        Extract the most important insights or ideas from this conversation segment:

        {chunk}

        Provide 5-8 key insights using the following structured template, with attention to detail:

        [*KEY INSIGHTS*]
    
        1. **Insight 1:** Briefly describe the first key insight with specific details.
    
        2. **Insight 2:** Briefly describe the second key insight, ensuring to capture all relevant nuances.
    
        3. **Continue until a total of 5-8 insights is reached, being thorough in each description.**
        """
        response = ollama.chat(model='qwen2.5:7b', messages=[
            {'role': 'system', 'content': 'You are proficient in extracting valuable insights. Adhere to the specified template for your output and focus on detail.'},
            {'role': 'user', 'content': insights_prompt}
        ])
        return response['message']['content']

    def generate_thematic(self, chunk):
        thematic_prompt = f"""
        Identify the main themes or patterns in this research conversation segment:

        {chunk}

        Use the following structured template for your response, ensuring to highlight details:

        [*THEMATIC ANALYSIS*]
    
        1. **Main Theme(s):** Clearly identify the central theme(s) present, paying close attention to their significance.
    
        2. **Significance:** Explain the importance of these themes in the context of the research, incorporating detailed observations.
    
        3. **Potential Applications:** Discuss how these themes could be applied in future research or practical scenarios with specific examples.
        """
        response = ollama.chat(model='qwen2.5:7b', messages=[
            {'role': 'system', 'content': 'You are an expert in thematic analysis. Follow the specified template for your output and focus on detail.'},
            {'role': 'user', 'content': thematic_prompt}
        ])
        return response['message']['content']

    def generate_flow(self, chunk):
        flow_prompt = f"""
        Analyze the flow of the following conversation segment concisely:

        {chunk}

        Structure your analysis using this template:

        [*FLOW ANALYSIS*]
    
        1. **Main Topic:** Identify the primary subject of discussion with attention to detail.
    
        2. **Conversation Direction:** Describe the progression and evolution of the conversation, ensuring to capture any subtle shifts.
    
        3. **Key Shifts:** Highlight significant changes in topic, tone, or dynamics, being meticulous about specifics.
    
        4. **Notable Patterns:** Identify interesting linguistic or interaction patterns observed, paying attention to detail.
    
        5. **Overall Character:** Summarize the general tone and emotional feel of the conversation in a single paragraph, incorporating nuanced details.
        """
        response = ollama.chat(model='qwen2.5:7b', messages=[
            {'role': 'system', 'content': 'You are a skilled conversation analyst. Ensure your analysis adheres to the provided template and focuses on detail.'},
            {'role': 'user', 'content': flow_prompt}
        ])
        return response['message']['content']

    def generate_nuanced(self, chunk):
        nuanced_prompt = f"""                        
        You are analyzing the following research conversation segment for truly *new, revolutionary, and nuanced* ideas that are grounded in logic and deviate from established theories. Be critical in your analysis, applying logic, reasoning, and expertise to ensure you only focus on coherent and novel concepts. Disregard ideas that are:
        - Already established, widely known, or accepted within the field.
        - Illogical, irrelevant, or lacking in reasoning or supporting evidence.
        - Rehashed ideas or random combinations with no meaningful insight.

        {chunk}

        Your analysis should focus solely on legitimate insights and disregard any concepts that do not meet the criteria of novelty and logical coherence. Use this structured format:

        [*NUANCED IDEAS ANALYSIS*]
    
        1. **Novel Concepts:** Identify any new or unexpected ideas, but ensure they are grounded in logic, feasible, and supported by reasoning. Avoid anything that appears nonsensical or lacks context.
    
        2. **Subtle Connections:** Highlight innovative, subtle connections between ideas, but only if they form a logical and coherent argument. Ensure that these connections have explanatory power or potential value.
    
        3. **Potential Breakthroughs:** Focus on ideas that could lead to significant advancements in the field, ensuring they are both novel and logically plausible. If an idea seems promising but lacks supporting evidence, mention it but clearly note any gaps.
    
        4. **Overlooked Perspectives:** Identify any under-explored perspectives that are logically sound and could offer fresh insights, but ensure they are not merely contrarian or irrelevant.
    
        5. **Emerging Patterns:** Detect any consistent, logical trends or patterns in thinking that could suggest new, unexplored paths for future research. Avoid any random or arbitrary connections.
    
        Apply a strict logic filter. If no new, nuanced, or logically sound ideas are present, respond with: "No Nuanced Ideas Present."
        """
    
        # use qwen3 series for better output- here i used 7b for simplicity/faster output sake and cunsumer grade hardware 
        response = ollama.chat(model='qwen2.5:7b', messages=[
            {'role': 'system', 'content': '''Apply a strict logic filter. If no new, nuanced, or logically sound ideas are present, respond with: "No Nuanced Ideas Present.". You are an expert in identifying novel and nuanced ideas. Use logic, reason, and critical thinking to evaluate all ideas in this conversation. 
            Ignore any that are already known, established, illogical, or irrelevant. Your priority is finding ideas that are genuinely new, feasible, and supported by reasoning. If no truly new ideas are found, respond with "No Nuanced Ideas Present."'''},
            {'role': 'user', 'content': nuanced_prompt}
        ])   
    
        return response['message']['content']

    def generate_sentiment(self, chunk):
        sentiment_prompt = f"""
        Perform a highly detailed sentiment analysis of the following conversation segment:

        {chunk}

        Focus on the following aspects in your analysis:

        [*SENTIMENT ANALYSIS*]

        1. **Overall Emotional Tone:** Identify the general emotional atmosphere of the conversation (e.g., positive, negative, neutral) and explain the dominant emotional undercurrents.
    
        2. **Emotion Intensity:** Assess the strength or intensity of the expressed emotions, whether subtle or extreme, and how these emotions manifest in the language.
    
        3. **Emotional Shifts:** Highlight any noticeable transitions in emotions or tone throughout the conversation and their significance in the context.
    
        4. **Subtle Emotional Cues:** Pay attention to any implicit or underlying emotions that may be inferred from the conversation’s subtleties, such as word choice, phrasing, or tone changes.
    
        5. **Impact on Conversation Dynamics:** Describe how the emotional tone influences the overall dynamics or flow of the conversation, particularly in relation to agreement, disagreement, or collaboration.
        """
    
        response = ollama.chat(model='qwen2.5:7b', messages=[
            {'role': 'system', 'content': 'You are a sentiment analysis expert. Provide a detailed analysis based on the specified template, focusing on emotional tone and nuances.'},
            {'role': 'user', 'content': sentiment_prompt}
        ])
    
        return response['message']['content']


class AIAgent:
    def __init__(self, name=None, persona=None):
        self.name = name or ""
        self.persona = persona or "(default)"

class ConversationGenerator(QObject):
    finished = pyqtSignal()
    result = pyqtSignal(object)
    error = pyqtSignal(str)
    conversation_updated = pyqtSignal(str, str)

    def __init__(self, agent1, agent2, topic, model='qwen2.5:7b', max_messages=20):
        super().__init__()
        self.agent1 = agent1
        self.agent2 = agent2
        self.topic = topic
        self.model = model
        self.conversation = []
        self._stop_requested = False
        self.message_delay = 3
        self.max_messages = max_messages
        self.current_message_count = 0

    def run(self):
        try:
            if not self.conversation:
                self._initialize_conversation()
            while self.current_message_count < self.max_messages:
                if self._stop_requested:
                    break
                self._continue_conversation()
            self.result.emit({'conversation': self.conversation})
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()

    def _initialize_conversation(self):
        system_prompt = f"You are {self.agent1.name}. {self.agent1.persona} You're discussing {self.topic}. Dont use emotes or action describers such as: (leans back in chair with a grin)"
        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': f"Start a conversation about {self.topic}."}
        ]
        response = ollama.chat(model=self.model, messages=messages)
        message = response['message']['content']
        self.conversation_updated.emit(self.agent1.name, message)
        self.conversation.append({'role': self.agent1.name, 'content': message})
        self.current_message_count += 1

    def _continue_conversation(self):
        current_agent = self.agent2 if len(self.conversation) % 2 == 1 else self.agent1
        other_agent = self.agent1 if current_agent == self.agent2 else self.agent2
        
        system_prompt = f"You are {current_agent.name}. {current_agent.persona} You're discussing {self.topic} with {other_agent.name}. Dont use emotes or action describers such as: (leans back in chair with a grin)"
        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': self.conversation[-1]['content']}
        ]
        response = ollama.chat(model=self.model, messages=messages)
        message = response['message']['content']
        self.conversation_updated.emit(current_agent.name, message)
        self.conversation.append({'role': current_agent.name, 'content': message})
        self.current_message_count += 1
        time.sleep(self.message_delay)

    def stop(self):
        self._stop_requested = True



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

class AnalysisWorker(QThread):
    analysis_complete = pyqtSignal(dict)
    progress_update = pyqtSignal(int)
    chunks_ready = pyqtSignal(list)

    def __init__(self, conversation):
        super().__init__()
        self.conversation = conversation
        self.max_tokens = 100000
        self.words_per_token = 0.65

    def run(self):
        results = {}
    
        total_words = self.word_count(self.conversation)
        estimated_tokens = int(total_words / self.words_per_token)
    
        if estimated_tokens <= self.max_tokens:
            chunks = [self.conversation]
        else:
            chunks = self.split_conversation(self.conversation)
            self.chunks_ready.emit(chunks)
    
        self.progress_update.emit(7)
    
        results['summary'] = self.process_chunks(chunks, self.generate_summary, "Executive Summary", 7, 26)
        results['insights'] = self.process_chunks(chunks, self.extract_insights, "Key Insights", 26, 45)
        results['thematic'] = self.process_chunks(chunks, self.generate_thematic_analysis, "Thematic Analysis", 45, 64)
        results['flow'] = self.process_chunks(chunks, self.analyze_conversation_flow, "Conversation Flow", 64, 83)
        results['nuanced'] = self.process_chunks(chunks, self.analyze_nuanced_ideas, "Nuanced Ideas", 83, 100)
        results['sentiment'] = self.process_chunks(chunks, self.analyze_sentiment, "Sentiment Analysis", 83, 100)
        
        self.analysis_complete.emit(results)
        
        self.analysis_complete.emit(results)

    def word_count(self, text):
        return len(re.findall(r'\w+', text))

    def split_conversation(self, conversation):
        chunks = []
        lines = conversation.split('\n')
        current_chunk = []
        current_word_count = 0
        
        for line in lines:
            line_word_count = self.word_count(line)
            if current_word_count + line_word_count > int(self.max_tokens * self.words_per_token):
                chunks.append('\n'.join(current_chunk))
                current_chunk = []
                current_word_count = 0
            
            current_chunk.append(line)
            current_word_count += line_word_count
        
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
        
        return chunks

    def process_chunks(self, chunks, analysis_function, title, progress_start, progress_end):
        results = []
    
        for i, chunk in enumerate(chunks):
            result = analysis_function(chunk)
            results.append(result)
            progress = progress_start + int((i + 1) / len(chunks) * (progress_end - progress_start))
            self.progress_update.emit(progress)
    
        if len(chunks) > 1:
            combined_result = self.synthesize_results(results, title)  # Pass the title here
        else:
            combined_result = results[0]
    
        return combined_result

    def generate_summary(self, chunk):
        summary_prompt = f"""
        Analyze the following research conversation segment and provide a comprehensive and in-depth summary of the main points:

        {chunk}

        Summarize in 5-7 sentences, ensuring to capture all relevant details and nuances of the discussion. Please **do not stray from the content's details**; focus closely on the specifics of the conversation.

        Use the following structured template for your output:

        [*SUMMARY*]
    
        1. **Key Points:** Clearly and thoroughly outline the primary ideas discussed, including any sub-points that are significant.
    
        2. **Implications:** Discuss the significance or potential impact of these points, considering how they relate to the broader research context.
    
        3. **Recommendations:** If applicable, provide detailed suggestions or next steps based on the insights drawn from the conversation.
    
        4. **Contextual Factors:** Note any relevant contextual elements that may influence the interpretation of these points.
        """
        response = ollama.chat(model='qwen2.5:7b', messages=[
            {'role': 'system', 'content': 'You are an expert analyst. Please follow the specified template for your summary output and pay close attention to detail.'},
            {'role': 'user', 'content': summary_prompt}
        ])
        return response['message']['content']

    def analyze_conversation_flow(self, chunk):
        flow_prompt = f"""
        Analyze the flow of the following conversation segment concisely:

        {chunk}

        Structure your analysis using this template:

        [*FLOW ANALYSIS*]
    
        1. **Main Topic:** Identify the primary subject of discussion with attention to detail.
    
        2. **Conversation Direction:** Describe the progression and evolution of the conversation, ensuring to capture any subtle shifts.
    
        3. **Key Shifts:** Highlight significant changes in topic, tone, or dynamics, being meticulous about specifics.
    
        4. **Notable Patterns:** Identify interesting linguistic or interaction patterns observed, paying attention to detail.
    
        5. **Overall Character:** Summarize the general tone and emotional feel of the conversation in a single paragraph, incorporating nuanced details.
        """
        response = ollama.chat(model='qwen2.5:7b', messages=[
            {'role': 'system', 'content': 'You are a skilled conversation analyst. Ensure your analysis adheres to the provided template and focuses on detail.'},
            {'role': 'user', 'content': flow_prompt}
        ])
        return response['message']['content']

    def extract_insights(self, chunk):
        insights_prompt = f"""
        Extract the most important insights or ideas from this conversation segment:

        {chunk}

        Provide 5-8 key insights using the following structured template, with attention to detail:

        [*KEY INSIGHTS*]
    
        1. **Insight 1:** Briefly describe the first key insight with specific details.
    
        2. **Insight 2:** Briefly describe the second key insight, ensuring to capture all relevant nuances.
    
        3. **Continue until a total of 5-8 insights is reached, being thorough in each description.**
        """
        response = ollama.chat(model='qwen2.5:7b', messages=[
            {'role': 'system', 'content': 'You are proficient in extracting valuable insights. Adhere to the specified template for your output and focus on detail.'},
            {'role': 'user', 'content': insights_prompt}
        ])
        return response['message']['content']

    def generate_thematic_analysis(self, chunk):
        thematic_prompt = f"""
        Identify the main themes or patterns in this research conversation segment:

        {chunk}

        Use the following structured template for your response, ensuring to highlight details:

        [*THEMATIC ANALYSIS*]
    
        1. **Main Theme(s):** Clearly identify the central theme(s) present, paying close attention to their significance.
    
        2. **Significance:** Explain the importance of these themes in the context of the research, incorporating detailed observations.
    
        3. **Potential Applications:** Discuss how these themes could be applied in future research or practical scenarios with specific examples.
        """
        response = ollama.chat(model='qwen2.5:7b', messages=[
            {'role': 'system', 'content': 'You are an expert in thematic analysis. Follow the specified template for your output and focus on detail.'},
            {'role': 'user', 'content': thematic_prompt}
        ])
        return response['message']['content']
    
    def analyze_nuanced_ideas(self, chunk):
        nuanced_prompt = f"""
        Analyze the following research conversation segment for new, novel, and nuanced ideas that might have been overlooked:

        {chunk}

        Use the following structured template for your response, focusing on originality and subtlety:

        [*NUANCED IDEAS ANALYSIS*]
    
        1. **Novel Concepts:** Identify any new or unexpected ideas that emerged in the conversation, no matter how subtle.
    
        2. **Subtle Connections:** Highlight any unusual connections or correlations between ideas that might not be immediately obvious.
    
        3. **Potential Breakthroughs:** Discuss any ideas or concepts that could potentially lead to breakthroughs or significant advancements in the field.
    
        4. **Overlooked Perspectives:** Point out any perspectives or viewpoints that were mentioned but not fully explored, which could offer valuable insights.
    
        5. **Emerging Patterns:** Identify any emerging patterns or trends in thinking that could indicate new directions for research or exploration.
        """
        response = ollama.chat(model='qwen2.5:7b', messages=[
            {'role': 'system', 'content': 'You are an expert in identifying novel and nuanced ideas. Focus on originality, subtlety, and potential breakthroughs in your analysis.'},
            {'role': 'user', 'content': nuanced_prompt}
        ])
        return response['message']['content']
    
    def analyze_sentiment(self, chunk):        
        sentiment_prompt = f"""
        Perform a detailed sentiment analysis on the following conversation segment:

        {chunk}

        Use the following structured template for your analysis:

        [*SENTIMENT ANALYSIS*]

        1. **Overall Tone:** Identify the dominant emotional tone of the conversation (e.g., positive, negative, neutral) and any shifts that occur throughout.
    
        2. **Emotional Intensity:** Discuss the intensity of emotions expressed, providing examples to support your analysis.
    
        3. **Emotional Variability:** Highlight any notable changes or fluctuations in sentiment, noting how these shifts impact the conversation's dynamics.
    
        4. **Key Emotional Drivers:** Identify specific statements or topics that significantly influence the emotional tone.
    
        5. **Subtle Emotional Undercurrents:** Point out any underlying emotions that may not be explicitly stated but are implied through word choice, tone, or context.
    
        6. **Impact on the Conversation:** Analyze how the emotional tone affected the flow of the conversation and the interaction between participants.
        """
        response = ollama.chat(model='qwen2.5:7b', messages=[
            {'role': 'system', 'content': 'You are an expert in sentiment analysis. Provide a comprehensive emotional analysis following the specified template.'},
            {'role': 'user', 'content': sentiment_prompt}
        ])
        return response['message']['content']


    def synthesize_results(self, results, analysis_type):
        combine_prompt = f"""
        Give a highly detailed synthesis the following {analysis_type} results into a coherent narrative:

        {' '.join(results)}

        Use this structured template for your synthesis output, ensuring to maintain attention to detail:

        [*{analysis_type.upper()} SYNTHESIS*]
    
        1. **Summary:** Provide a brief overview of the combined {analysis_type} results, incorporating detailed observations.
    
        2. **Key Takeaways:** Highlight the most critical conclusions drawn from the synthesis with specific examples.
    
        3. **Future Directions:** Suggest potential avenues for further exploration based on the synthesis, paying close attention to detail.
    
        [END_{analysis_type.upper()}_SYNTHESIS]
        """
        response = ollama.chat(model='qwen2.5:7b', messages=[
            {'role': 'system', 'content': f'You are skilled at synthesizing {analysis_type} information. Follow the specified template in your synthesis output and focus on detail.'},
            {'role': 'user', 'content': combine_prompt}
        ])
        return response['message']['content']

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