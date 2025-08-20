Of course. Here is a comprehensive, professional README tailored specifically for your GitHub repository. You can copy and paste this directly into the `README.md` file in your `dovvnloading/Verbalink` repo.

---

# Verbalink: AI Conversation Generation & Analysis Tool

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)
![Framework](https://img.shields.io/badge/framework-PyQt5-green.svg)

Verbalink is a desktop application designed for researchers, writers, and AI enthusiasts to generate, analyze, and interact with conversations between two configurable AI agents. Powered by local language models via [Ollama](https://ollama.com/), this tool provides a robust framework for exploring AI interaction, linguistic patterns, and conversational dynamics.

![Untitled video - Made with Clipchamp (2)](https://github.com/user-attachments/assets/76a7e3ef-1c70-477e-946c-59adf8b7fc5e)

---

<img width="600" height="500" alt="Screenshot 2025-08-20 111432" src="https://github.com/user-attachments/assets/c0b156a5-25ef-4c18-914e-d0dc592406c8" />

---

<img width="1202" height="832" alt="Screenshot 2025-08-20 111413" src="https://github.com/user-attachments/assets/e14a1e8c-6a5b-4366-b05e-44f082bb9e2d" />

---

<img width="800" height="600" alt="Screenshot 2025-08-20 111401" src="https://github.com/user-attachments/assets/ef7779b7-c975-43a8-99d6-e7432a10baf4" />

---

<img width="800" height="600" alt="Screenshot 2025-08-20 111342" src="https://github.com/user-attachments/assets/e35b05bb-700e-42d4-a556-a7c017c8075b" />

---

## Key Features

*   **Advanced AI Agent Configuration**: Define two distinct AI agents with custom names and detailed personas. These personas guide the agents' conversational style, knowledge base, and point of view.
*   **Dynamic Conversation Generation**:
    *   Initiate a discussion on any topic between the two configured AI agents.
    *   Precisely control the length of the conversation by setting the number of messages.
    *   Full control over the generation process with start, stop, and continue functionalities.
*   **Multi-Faceted Conversation Analysis**: After generating a conversation, leverage a comprehensive analysis suite for deep insights:
    *   **Executive Summary**: A concise, high-level overview of the entire conversation.
    *   **Key Insights**: Extracts the most critical ideas, conclusions, and takeaways.
    *   **Thematic Analysis**: Identifies recurring topics, arguments, and patterns of discussion.
    *   **Conversation Flow**: Analyzes the logical progression, topic shifts, and interaction dynamics.
    *   **Nuanced Ideas**: A specialized analysis that uncovers novel, subtle, or potentially revolutionary concepts that emerged.
    *   **Sentiment Analysis**: Evaluates the emotional tone of the conversation and tracks its shifts over time.
*   **Interactive Analysis Discussion**: For any generated analysis report, open a dedicated chat window. In this window, you can discuss the findings with a specialized "Verbalink" AI assistant to get clarifications, ask follow-up questions, and achieve a deeper understanding of the results.
*   **Modern and Functional UI**:
    *   Built with PyQt5, featuring a clean, professional user interface.
    *   Includes a custom window frame and title bar for a consistent look and feel.
    *   Supports both **Light and Dark modes** to suit user preference.
*   **Efficient and Responsive Operation**: Utilizes multi-threading for all AI-related tasks, ensuring the user interface remains fluid and responsive even during intensive generation and analysis processes.
*   **Persistent Sessions**: Agent configurations and theme preferences are saved locally, ensuring your setup is retained between application launches.

## How It Works

Verbalink orchestrates a series of structured interactions with a local Large Language Model (LLM) running through the Ollama service.

1.  **Generation**: The `ConversationGenerator` class instantiates two AI agents based on the user-defined personas. It then moderates a turn-by-turn conversation, carefully managing the conversational history to provide the necessary context to the LLM for generating each new message.
2.  **Analysis & Chunking**: The `AnalysisWorker` takes the full text of the generated conversation. If the conversation is very long and exceeds the LLM's context window limit, the worker automatically splits the text into smaller, manageable chunks. It then runs each of the six specialized analysis prompts on every chunk.
3.  **Synthesis**: If the conversation was chunked for analysis, a final synthesis prompt is executed. This prompt instructs the LLM to combine the analysis results from each individual chunk into a single, coherent, and unified report for each analysis type.
4.  **Interaction**: The `ChatDialog` provides the interactive discussion feature. It takes a specific, final analysis report and uses it as the foundational context for a new conversation with a helpful AI assistant, enabling a focused, in-depth exploration of the analysis results.

## Prerequisites

Before you begin, ensure you have the following installed and running on your system:

1.  **Python 3.8+**
2.  **Ollama**: You must have the Ollama service installed and running. You can download it from [ollama.com](https://ollama.com/).
3.  **An Ollama Language Model**: The application requires at least one model to be pulled and available to the Ollama service. The code is optimized for models like `qwen2.5:7b`, but other general-purpose models should work. To download the recommended model, open your terminal and run:
    ```sh
    ollama pull qwen2.5:7b
    ```

## Getting Started

Follow these steps to get Verbalink running on your local machine.

### 1. Clone the Repository

```sh
git clone https://github.com/dovvnloading/Verbalink.git
cd Verbalink
```

### 2. Set Up a Virtual Environment and Install Dependencies

It is highly recommended to use a Python virtual environment to manage dependencies and avoid conflicts with other projects.

```sh
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install the required packages
pip install PyQt5 ollama
```

### 3. Run the Application

First, ensure the Ollama service is running in the background. Then, start the Verbalink application from your terminal:

```sh
python main.py
```
*(Note: The main script file is assumed to be named `main.py`)*

## Detailed Usage Guide

This guide provides a step-by-step walkthrough of the application's features.

### Step 1: Configure the AI Agents

The quality and nature of the generated conversation depend heavily on the agent personas. This should be your first step.

1.  Navigate to the menu bar and select **Research > Configure Agents**. This will open the "Configure Agents" window.
2.  **Manually Define Personas**:
    *   For **Agent 1** and **Agent 2**, fill in the **Name** field.
    *   In the **Persona** text box, provide a detailed description. A good persona includes background, expertise, beliefs, personality traits, and communication style. The more detailed the persona, the more convincingly the agent will adhere to it.
3.  **Automatically Generate Personas**:
    *   If you want a starting point, select a **Theme** from the dropdown menu (e.g., "Scientific Research," "Political Debate").
    *   Click the **"Generate"** button. The application will ask the LLM to create two detailed, opposing, or complementary agent profiles based on the selected theme and populate the fields for you. You can then edit these generated personas as needed.
4.  Once you are satisfied with the configurations, click **"OK"** to save and close the window. Your configurations are saved automatically for future sessions.

### Step 2: Generate a Conversation

With your agents configured, you can now generate a conversation on the main screen.

1.  **Set the Topic**: In the "Topic" input field at the top of the main window, enter the subject you want the agents to discuss.
2.  **Set the Message Count**: In the "Message Count" field within the "Conversation Controls" box, enter the total number of messages you want in the conversation (e.g., entering `20` will result in 10 messages from each agent). If left blank, it defaults to 20.
3.  **Start Generation**: Click the **"Start Conversation"** button.
    *   The button will become disabled, and the "Stop Conversation" button will become active.
    *   The main chat area will begin to populate with messages from each agent in real-time.
4.  **Control the Process**:
    *   **Stop Conversation**: Click this at any time to interrupt the generation process. The conversation will halt at its current state.
    *   **Continue Conversation**: After stopping a conversation, this button becomes active. Clicking it will resume the generation from where it left off, adding more messages until the total message count is reached. You can also enter a new, higher number in the "Message Count" field before continuing.

### Step 3: Analyze the Conversation

Once a conversation has been generated (either completed or stopped), you can perform a detailed analysis.

1.  Navigate to the menu bar and select **Analysis > Analyze Conversation**. This will open the "Research Conversation Analysis" window.
2.  You have two options for running the analysis:
    *   **Full Evaluation (Recommended)**: Click the **"Run Full Evaluation"** button. This will execute all six analysis types sequentially. The progress bar at the bottom will update in real-time to show the progress. This provides the most comprehensive overview.
    *   **Single Analysis**: If you only need one specific type of analysis, first click on its corresponding tab (e.g., "Thematic Analysis"), and then click the **"Run Analysis"** button. This will only generate the report for the currently active tab.
3.  Upon completion, the text areas within each tab will be populated with the detailed analysis reports.

### Step 4: Discuss and Explore the Analysis Results

This unique feature allows you to interact with the findings from the analysis.

1.  In the "Research Conversation Analysis" window, navigate to the tab of an analysis you wish to explore further (e.g., "Nuanced Ideas").
2.  Click the **"Discuss Nuanced Ideas"** button at the bottom of the window.
3.  A new, dedicated chat window will appear. In this window, an AI assistant named "Verbalink" is already primed with the full text of the "Nuanced Ideas" report.
4.  You can now ask specific questions to deepen your understanding. For example:
    *   *"Can you elaborate on the second novel concept you identified?"*
    *   *"What specific phrases in the original conversation led you to identify this as a 'subtle connection'?"*
    *   *"Based on this analysis, what would be a logical next topic for these agents to discuss?"*
5.  This allows for an interactive deep-dive into the results, turning a static report into a dynamic exploration.

### Step 5: Exporting and Managing Chats

1.  **Export Conversation**: To save a conversation externally, go to **File > Export Conversation**. This will prompt you to save a `.txt` file containing the topic, the full agent personas, and the complete conversation transcript.
2.  **New Chat**: To start over, select **File > New Chat**. This will clear the main window and reset the application state, allowing you to start a new session with a new topic or new agents.

## Configuration

*   **LLM Model**: The application is hardcoded to use a specific model (e.g., `model='qwen2.5:7b'`). To change this, you must edit the source code. Look for the `ollama.chat()` calls within the `ConversationGenerator` and `AnalysisWorker` classes and change the `model` parameter to any other model you have installed in Ollama.
*   **Theme**: You can toggle between light and dark modes at any time by navigating to **View > Toggle Dark Mode**. Your preference will be saved for your next session.

## Contributing

Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

If you have a suggestion that would make this better, please fork the repo and create a pull request. You can also simply open an issue with the tag "enhancement".

1.  Fork the Project (`https://github.com/dovvnloading/Verbalink/fork`)
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the Branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request

## License

Distributed under the MIT License. See `LICENSE` for more information.

---
---
---
---

### A Developer's Note on Project Status & Future Direction

Please note that Verbalink is a personal side project, originally created over a year and a half ago. It has remained largely untouched since its initial development, with only minor updates made recently. The primary objective was to rapidly prototype a functional proof-of-concept, prioritizing implementation speed over architectural purity.

For any developers looking to contribute, fork, or build upon this concept, it is essential to understand the current state of the code and the critical modernizations required.

#### The Codebase: A Snapshot in Time

The application in its current form should be viewed as a functional prototype from a previous generation of local LLM capabilities. Its key characteristics are:

*   **Monolithic Structure**: The entire application—including the UI, event handling, AI API calls, and business logic—is contained within a single Python script. This was a deliberate choice for rapid development but is not a sustainable architecture.
*   **Tight Coupling**: There is no formal separation of concerns. UI elements directly call AI functions, making the code difficult to debug, modify, or extend.
*   **Outdated Models**: The language models referenced in the code (primarily `qwen2.5:7b` and `phi4:14b`) were practical choices at the time of development. They are now significantly outdated and will produce lower-quality results.

#### Critical Update Recommendation: Language Models

The single most important update for anyone using or experimenting with this code is to replace the language models. The models currently in the script are outdated and will produce significantly lower-quality results compared to modern alternatives.

It is **strongly recommended** to replace all hardcoded model references (e.g., `model='qwen2.5:7b'`) with newer, more capable models such as `qwen3` or `gpt-oss:20b`.

This change alone will dramatically improve the quality of conversation generation, the depth of the analysis, and the models' ability to follow complex persona instructions. Using the original, older models will not give a fair representation of what is possible with this concept today.

#### Architectural Path for Future Development

For anyone interested in evolving Verbalink into a more serious, robust application, a complete rewrite and architectural redesign is the necessary first step. The current repository serves best as a functional blueprint of an idea, not as a foundation to build upon directly.

A more robust implementation should be built on the following principles:

1.  **Separation of Concerns**: The codebase should be broken down into distinct, logical modules. A potential structure could be:
    *   `ui/`: Containing all PyQt5 classes related to windows, dialogs, and widgets.
    *   `core/`: Housing the main application logic, state management, and orchestration.
    *   `ai/`: Abstracting all interactions with the Ollama API, with separate modules for generation and analysis.
    *   `utils/`: For helper functions, threading managers, and other shared utilities.

2.  **Adoption of a Design Pattern**: Implementing a recognized design pattern like Model-View-Controller (MVC) or Model-View-ViewModel (MVVM) would formalize the separation between the data (Model), the user interface (View), and the application logic (Controller/ViewModel).

3.  **Configuration Management**: All hardcoded parameters, especially model names, should be moved to an external configuration file (e.g., `config.json` or `settings.ini`). This would allow users to easily change models without modifying the source code.

4.  **Robust Error Handling and Logging**: A centralized system for logging and displaying user-friendly error messages should be implemented to improve stability and diagnostics.

In its current state, this repository serves as a functional blueprint of an idea from a specific point in time. It is not a foundation for production-grade software.
