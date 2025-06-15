# Presenta-AI: AI-Powered Presentation Reviewer

## Project Overview

Presenta-AI is a Python application designed to provide AI-driven reviews of presentations. Users can upload their presentation files (PPTX or PDF), define a goal and audience, configure an "AI Review Team" with different agent behaviors, and receive a structured review report. This version of the application operates entirely with a mocked backend environment, meaning no actual calls to external cloud services like Google Cloud Storage or Vertex AI are made.

## Core Technologies

-   **Python**: The application is entirely written in Python 3.10+.
-   **Streamlit**: Used for building the interactive user interface.
-   **Google Agent Development Kit (ADK)**: Powers the backend logic, orchestrating a team of AI agents to perform the review.
-   **Pydantic**: Used for data validation and settings management through robust data models.
-   **PyYAML**: Used for parsing YAML configuration files.

## Mocked Environment

A crucial aspect of this implementation is that all external services are mocked locally. This allows for development and testing without reliance on live cloud infrastructure.

-   **Mock Google Cloud Storage (GCS)**:
    -   Implemented in `presenta_ai/utils/mock_gcs_client.py`.
    -   The `MockGCSClient` class simulates file uploads and reads using an in-memory Python dictionary. When a file is uploaded via the UI, it's notionally "stored" here, and the backend refers to it by a mock GCS path (e.g., `gs://mock_bucket/...`).

-   **Mock Vertex AI (Gemini API) Client**:
    -   Implemented in `presenta_ai/utils/mock_llm_client.py`.
    -   The `MockVertexAIClient` simulates responses from a Large Language Model (like Google's Gemini). It does **not** make any real API calls.
    -   It contains internal routing logic: based on keywords in the prompts it receives (or special hints passed during mock calls), it returns predefined, realistic-looking JSON or text responses that mimic how a real LLM might respond for different agents (e.g., Document Analyzer, Logic Critic, Auto-Composition).

-   **Mock Cloud Logging**:
    -   Instead of integrating with Google Cloud Logging, standard Python `logging` is used throughout the application.
    -   Log messages are configured to print directly to the console, providing visibility into the application's operations during local development.

## Directory Structure

-   `presenta_ai/`: Project root.
    -   `app.py`: The main Streamlit application script.
    -   `requirements.txt`: Python dependencies.
    -   `Dockerfile`: For containerizing the application.
    -   `README.md`: This file.
    -   `config/`: Contains configuration files.
        -   `agent_config_options.yaml`: Defines selectable behaviors and prompt fragments for the AI agents.
    -   `adk_logic/`: Contains the backend ADK agent logic.
        -   `main_runner.py`: Orchestrates the ADK agent workflow.
        -   `data_models.py`: Pydantic models for data structuring.
        -   `agents/`: Factories for creating specific ADK agents (DocumentAnalyzer, LogicCritic, etc.).
        -   `prompts/`: Prompt templates and generation logic (e.g., `auto_compose_prompt.py`).
        -   `tools/`: (Currently minimal as document parsing was shifted to LLM capabilities).
        -   `callbacks.py`: (Placeholder for future ADK callback implementations).
    -   `utils/`: Common utility modules.
        -   `mock_gcs_client.py`: Mock GCS client.
        -   `mock_llm_client.py`: Mock LLM client.
        -   `config_loader.py`: Utilities for loading `agent_config_options.yaml`.

## Configuration

The behavior of the AI review agents (Logic Critic, Audience Persona, Q&A Generator) is configurable via `presenta_ai/config/agent_config_options.yaml`. This file defines:
-   The name and description of each configurable agent.
-   The available policy options for each agent (e.g., "Strict" vs. "Supportive" for the Logic Critic).
-   The `id` for each option (used internally).
-   A user-friendly `label` and `description` for each option (displayed in the UI).
-   A `cost_factor` (used in the UI's "Team Summary" sidebar).
-   A `prompt_fragment` which is appended to the agent's base prompt to tailor its behavior.

## How to Run

1.  **Python Version**: Ensure you have Python 3.10 or newer.
2.  **Clone Repository**: (If applicable) Clone the project repository to your local machine.
3.  **Create Virtual Environment** (recommended):
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```
4.  **Install Dependencies**: Navigate to the project root (`presenta_ai/`) and install requirements:
    ```bash
    pip install -r requirements.txt
    ```
5.  **Run the Streamlit Application**:
    ```bash
    streamlit run app.py
    ```
    The application should open in your web browser (usually at `http://localhost:8501`).

## How It Works (High-Level Flow)

1.  **Input**: The user accesses the Streamlit UI, uploads a presentation file, and provides the presentation's goal and audience details.
2.  **Team Configuration**:
    *   The user configures the "AI Review Team" by selecting desired behaviors for each agent (e.g., Logic Critic, Audience Persona, Q&A Generator) using radio buttons. These options are dynamically populated from `config/agent_config_options.yaml`.
    *   Alternatively, the user can click "AI Auto-Compose Team." This triggers a call to the (mock) LLM with the presentation goal, audience info, and available agent options. The mock LLM returns a suggested team configuration, which updates the UI selections.
    *   A "Team Summary" sidebar shows the implications (cost factor, review focus) of the current selections.
3.  **Review Process**:
    *   Clicking "Analyze Presentation" initiates the backend review process by calling `run_review_process` in `adk_logic/main_runner.py`.
    *   `run_review_process` uses the Google ADK `Runner` to execute a `SequentialAgent`. This workflow runs a series of specialized agents:
        1.  `DocumentAnalyzerAgent`: "Analyzes" the document (using the mock LLM which receives the file path).
        2.  `LogicCriticAgent`: Reviews logical consistency based on the chosen policy.
        3.  `AudiencePersonaAgent`: Reviews from the audience's perspective based on the chosen persona.
        4.  `QnaGeneratorAgent`: Generates Q&A pairs (if enabled).
        5.  `ReportSynthesizerAgent`: Compiles all feedback into a final report structure.
    *   All agents interact with the `MockLLMClient` and share information via the ADK `State` object within a session.
4.  **Output**: The `FinalReport` (including Q&A if generated) is returned to the Streamlit UI and displayed in a structured, tabbed format.

## Testing Internal Components

Many of the Python modules in `adk_logic/` and `utils/` include an `if __name__ == '__main__':` block. These blocks contain simple test routines that allow for isolated testing or demonstration of that specific module's functionality (e.g., testing mock LLM responses, agent prompt rendering, or config loading). These can be run directly, for example: `python -m presenta_ai.utils.mock_llm_client`.

```
