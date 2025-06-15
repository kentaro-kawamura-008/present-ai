from google.adk.agents import LlmAgent
from google.adk.prompts import PromptTemplate
from presenta_ai.adk_logic.data_models import DocumentAnalysisResult # Assuming data_models.py is in the root of adk_logic

# Placeholder for the actual prompt template string
# This will instruct the LLM on how to analyze the document at 'gcs_file_path'
# and what to return, aiming to populate DocumentAnalysisResult.
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
    This agent uses its multimodal capabilities (simulated by the mock LLM)
    to analyze the presentation document.
    """
    return LlmAgent(
        name="DocumentAnalyzerAgent",
        # The 'model' parameter will be effectively overridden by mock_llm_client when testing locally
        model="gemini-1.5-pro-preview-0409", # Placeholder, will be mocked
        instruction=DOCUMENT_ANALYZER_PROMPT_TEMPLATE,
        # ADK LlmAgent expects input keys from the State for its prompt template.
        # These will be 'gcs_file_path', 'presentation_goal', and 'audience_profile'.
        # The output of this agent (a DocumentAnalysisResult, ideally as a JSON string from the LLM)
        # will be saved to the State with this key.
        output_key="document_analysis_json_str", # The LLM will output a JSON string
        # If a real LLM client were used, and it supported Pydantic model output directly:
        # output_model=DocumentAnalysisResult,
        # output_key="document_analysis",
        llm=mock_llm_client_for_adk_agent # Pass the mock LLM client here for local execution
    )
