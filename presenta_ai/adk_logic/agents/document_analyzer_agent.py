"""
Agent responsible for analyzing the content of a presentation document.

This module defines the `DocumentAnalyzerAgent`, an LlmAgent that takes the
GCS path of a presentation file, its goal, and audience profile as input.
It instructs an LLM to analyze the document and return a structured summary
of its content, conforming to the `DocumentAnalysisResult` Pydantic model.
The LLM is expected to output this as a JSON string.
"""
import logging # For __main__ block
from google.adk.agents import LlmAgent
from google.adk.prompts import PromptTemplate
# Assuming data_models.py is in the adk_logic directory, which is a sibling to this agents directory,
# or presenta_ai is in PYTHONPATH.
from presenta_ai.adk_logic.data_models import DocumentAnalysisResult

# This prompt template instructs the LLM on how to analyze the document
# at 'gcs_file_path' and what structured JSON to return.
DOCUMENT_ANALYZER_PROMPT_TEMPLATE = PromptTemplate(
    """
    You are an AI assistant specialized in analyzing presentation documents.
    The presentation file is located at the GCS path: {{gcs_file_path}}.
    Your task is to analyze this presentation and provide a structured summary.

    Please provide your analysis in a JSON format that conforms to the following Pydantic model:
    {
        "slides": [
            {
                "slide_number": int, // The slide number, starting from 1
                "text": "str", // A summary of the key textual content or themes of this slide
                "title": "Optional[str]", // The title of the slide, if identifiable
                "notes": "Optional[str]" // Any speaker notes associated with the slide, if identifiable
            }
            // Repeat for each identifiable slide or logical section
        ],
        "error": "Optional[str]" // If analysis fails, provide an error message here
    }

    If you can identify distinct slides, provide an entry for each.
    If the document structure isn't clear slide-by-slide but you can identify logical sections,
    represent each section as a 'slide' in your output.
    Focus on extracting key information and themes.
    If you cannot analyze the document, set the 'error' field.

    Presentation Goal: {{presentation_goal}}
    Audience Profile: {{audience_profile}}

    Based on the document at {{gcs_file_path}}, the presentation goal, and audience profile,
    perform the analysis and return the JSON.
    """
)

def create_document_analyzer_agent(mock_llm_client_for_adk_agent=None) -> LlmAgent:
    """
    Factory function to create the Document Analyzer Agent.

    This agent is responsible for the initial analysis of the presentation
    document. It uses an LLM (potentially with multimodal capabilities, though
    simulated by a mock LLM here) to extract slide content, titles, and notes.

    Args:
        mock_llm_client_for_adk_agent: An optional mock LLM client instance,
            typically used for local testing or when a real LLM is not available.
            If None, the ADK LlmAgent will attempt to use a globally configured client.

    Returns:
        LlmAgent: An instance of the Document Analyzer Agent.
    """
    return LlmAgent(
        name="DocumentAnalyzerAgent",
        # The 'model' parameter will be effectively overridden by mock_llm_client when testing.
        model="gemini-1.5-pro-preview-0409", # Placeholder, actual model may vary.
        instruction=DOCUMENT_ANALYZER_PROMPT_TEMPLATE,
        # These input keys are expected by the DOCUMENT_ANALYZER_PROMPT_TEMPLATE.
        # The ADK LlmAgent will pull values for these keys from the current session state.
        # 'audience_profile' is expected to be a dictionary-like object in the state
        # that can be accessed with dot notation in the prompt (e.g., {{audience_profile.role}}).
        # The Pydantic model `PresentaAiState` ensures this structure.
        output_key="document_analysis_json_str", # The LLM is prompted to output a JSON string.
        # If a real LLM client were used that supports direct Pydantic model output:
        # output_model=DocumentAnalysisResult, # This would allow direct parsing to the Pydantic model.
        # output_key="document_analysis", # And the output would be stored under this key as the model instance.
        llm=mock_llm_client_for_adk_agent # Pass the mock LLM client for local execution.
    )

if __name__ == '__main__':
    # Configure basic logging for the __main__ execution
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)

    logger.info("--- Testing DocumentAnalyzerAgent Creation ---")

    # Create an instance of the agent (no mock LLM needed for just creation)
    analyzer_agent = create_document_analyzer_agent()
    logger.info(f"Created agent: {analyzer_agent.name}")
    logger.info(f"Agent instruction template (first 300 chars):\n{analyzer_agent.instruction.template[:300]}...")

    # Example of how the prompt would be rendered with mock data
    # (ADK LlmAgent does this internally using the session state)
    mock_state_data = {
        "gcs_file_path": "gs://mock-bucket/mock_presentation.pptx",
        "presentation_goal": "To secure funding for a new AI-powered cat toy.",
        "audience_profile": {"role": "Investors", "interests": "ROI, market size, cute cat videos"}
    }

    # Manually render the prompt for demonstration
    # Note: The 'audience_profile' in the state is a dictionary. The PromptTemplate's
    # dot notation `{{audience_profile.role}}` handles accessing nested dictionary values.
    rendered_prompt = DOCUMENT_ANALYZER_PROMPT_TEMPLATE.render(**mock_state_data)
    logger.info("\n--- Example Rendered Prompt (DocumentAnalyzerAgent) ---")
    logger.info(rendered_prompt)
    logger.info("--- End of DocumentAnalyzerAgent __main__ test ---")
