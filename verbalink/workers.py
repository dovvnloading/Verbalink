"""Background workers that perform LLM calls and conversation analysis."""

import logging
import re

import ollama
from PyQt5.QtCore import QObject, QThread, pyqtSignal

from .models import AIAgent


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

