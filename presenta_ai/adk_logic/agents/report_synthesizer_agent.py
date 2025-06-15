"""
Agent responsible for synthesizing individual reviews into a final report.

This module defines the `ReportSynthesizerAgent`, an LlmAgent that takes
the textual reviews from the LogicCriticAgent and AudiencePersonaAgent,
along with the structured data from the DocumentAnalyzerAgent (and potentially
QnaGeneratorAgent in the future), and compiles them into a single, coherent
JSON report conforming to the `FinalReport` Pydantic model.
"""
import logging

from google.adk.agents import LlmAgent
from google.adk.prompts import PromptTemplate
# Note: The FinalReport Pydantic model from data_models.py is not directly imported here.
# Instead, its structure is described within the prompt template to guide the LLM.
# This keeps the agent focused on its LLM interaction rather than direct model instantiation.

# This prompt template instructs the LLM to act as a skilled editor,
# synthesizing various inputs into a structured JSON final report.
REPORT_SYNTHESIZER_BASE_PROMPT_TEMPLATE = PromptTemplate(
    """
    You are a skilled editor responsible for compiling a comprehensive presentation review report.
    You have received feedback from a Logic Critic, an Audience Persona reviewer, and the initial document analysis.
    Your task is to synthesize these inputs into a single, structured final report in JSON format.

    The JSON output MUST conform to the following Pydantic model structure for 'FinalReport':
    {
        "summary_review": "str (Overall assessment of the presentation, synthesizing all feedback)",
        "storyline_review": "str (Specific feedback on the presentation's narrative and flow)",
        "slide_by_slide_reviews": [
            {
                "slide_number": "int (The slide number this review pertains to)",
                "evaluation": "str (Synthesized evaluation for this slide)",
                "suggestion": "str (Actionable suggestion for this slide)"
            }
            // ... more SlideReview objects ...
        ],
        "qna_list": "Optional[List[QnAPair]] (This will be provided by another agent later, you can omit this field or set it to null/None if not available from inputs)"
    }

    Use the information from the Document Analysis to structure the slide-by-slide reviews if possible.
    If slide-specific feedback isn't available from the Logic Critic or Audience Persona, focus on overall themes for summary and storyline.

    # Review 1: Comments from the Logic Critic
    {{logic_critic_review_text}}

    # Review 2: Comments from the Audience Persona
    {{audience_persona_review_text}}

    # Original Document Information (JSON String from DocumentAnalyzerAgent)
    {{document_analysis_json_str}}

    # (If Q&A list is available in state later, it would be under 'qna_list_json_str')
    # For now, focus on the first three components for the FinalReport.

    Compile the report and provide ONLY the JSON string as your output.
    """
)

def create_report_synthesizer_agent(mock_llm_client_for_adk_agent=None) -> LlmAgent:
    """
    Factory function to create the Report Synthesizer Agent.
    This agent synthesizes reviews from other agents into a final report.
    """
    return LlmAgent(
        name="ReportSynthesizerAgent",
        model="gemini-1.5-pro-preview-0409", # Placeholder, will be mocked
        instruction=REPORT_SYNTHESIZER_BASE_PROMPT_TEMPLATE,
        # Input keys expected by the prompt template from ADK State:
        # logic_critic_review_text, audience_persona_review_text, document_analysis_json_str
        output_key="final_report_json_str", # LLM will output a JSON string
        llm=mock_llm_client_for_adk_agent
    )

if __name__ == '__main__':
    if not logging.getLogger().hasHandlers():
        logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    dummy_llm = "DUMMY_LLM_CLIENT"

    logger.info("--- Testing ReportSynthesizerAgent Creation ---")
    synthesizer_agent = create_report_synthesizer_agent(mock_llm_client_for_adk_agent=dummy_llm)
    logger.info(f"Created agent: {synthesizer_agent.name}")
    logger.info(f"Instruction (template text):\n{synthesizer_agent.instruction.template[:500]}...") # instruction is a PromptTemplate

    # Example state that this agent would expect
    mock_state = {
        "logic_critic_review_text": "The logic needs more support on slide 2.",
        "audience_persona_review_text": "The audience might find the jargon confusing.",
        "document_analysis_json_str": '{"slides": [{"slide_number": 1, "text": "Intro"}, {"slide_number": 2, "text": "Details"}], "error": null}'
    }

    # Render the prompt manually for checking (ADK LlmAgent does this internally)
    rendered_prompt = synthesizer_agent.instruction.render(**mock_state)
    logger.info("\n--- Rendered Prompt Example (ReportSynthesizerAgent) ---")
    logger.info(rendered_prompt)
    logger.info("--- End of ReportSynthesizerAgent __main__ test ---")
