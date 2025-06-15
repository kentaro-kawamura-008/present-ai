"""
Agent responsible for generating anticipated Questions and Answers (Q&A)
based on the presentation content.

This module defines the `QnaGeneratorAgent`, an LlmAgent that uses the
document analysis to create a list of potential questions an audience might ask,
along with concise answers. The agent's creation can be toggled via a
`selection_id` (e.g., "enabled" or "disabled"). If disabled, the factory
function returns `None`.
"""
import logging

from google.adk.agents import LlmAgent, BaseAgent
from google.adk.prompts import PromptTemplate
# The get_prompt_fragment import is kept for consistency, though not actively used
# to modify the prompt for this agent as the toggle is based on selection_id directly.
from presenta_ai.utils.config_loader import get_prompt_fragment
# from presenta_ai.adk_logic.data_models import QnAPair # For prompt structure reference in comments

# Module-level logger
logger = logging.getLogger(__name__) # Used for logging within the factory function

QNA_GENERATOR_BASE_PROMPT_TEMPLATE = PromptTemplate(
    """
    You are an AI assistant that generates anticipated questions and their answers
    based on presentation content.

    Analyze the provided document analysis (JSON string) and generate a list of
    potential questions an audience might ask, along with concise, accurate answers.

    The JSON output MUST be a list of objects, where each object conforms to the
    following Pydantic model structure for a 'QnAPair':
    [
        {
            "question": "str (The anticipated question)",
            "answer": "str (A concise answer to the question)"
        }
        // ... more QnAPair objects ...
    ]

    # Document Analysis Result (JSON String)
    {{document_analysis_json_str}}

    Generate at least 3-5 relevant Q&A pairs. If the document analysis is empty or
    uninformative, you can state that no specific Q&A can be generated.
    Provide ONLY the JSON list as your output.
    """
)

def create_qna_generator_agent(selection_id: str, mock_llm_client_for_adk_agent=None) -> Optional[BaseAgent]:
    """
    Factory function to create the Q&A Generator Agent.

    This agent generates potential questions and answers based on the presentation's
    document analysis. Its inclusion in the review workflow is determined by the
    `selection_id`. If `selection_id` is "disabled", this function returns `None`.

    Args:
        selection_id (str): The identifier that determines if the agent should be
            created (e.g., "enabled", "disabled"). This corresponds to an option
            in `agent_config_options.yaml` for the 'qna_generator'.
        mock_llm_client_for_adk_agent: An optional mock LLM client instance.

    Returns:
        Optional[BaseAgent]: An instance of the QnA Generator Agent if enabled,
                             otherwise `None`.
    """
    # The 'qna_generator' options in agent_config_options.yaml might have
    # prompt_fragments, but for this agent, the selection_id ("enabled"/"disabled")
    # primarily acts as a toggle for its creation.
    # We call get_prompt_fragment for consistency or future use, but don't append it.
    _ = get_prompt_fragment('qna_generator', selection_id) # Not used, but shows pattern

    if selection_id == "disabled":
        logger.info("Q&A Generation is disabled by user configuration. Skipping QnaGeneratorAgent creation.")
        return None

    # If not disabled, proceed to create the agent.
    # The base prompt is used directly as the instruction.
    return LlmAgent(
        name="QnaGeneratorAgent", # Name can be static as there's only one functional version
        model="gemini-1.5-pro-preview-0409", # Placeholder, will be mocked
        instruction=QNA_GENERATOR_BASE_PROMPT_TEMPLATE, # Pass the PromptTemplate instance
        # Input keys expected: document_analysis_json_str
        output_key="qna_list_json_str", # LLM will output a JSON string
        llm=mock_llm_client_for_adk_agent
    )

if __name__ == '__main__':
    if not logging.getLogger().hasHandlers():
        logging.basicConfig(level=logging.INFO)

    logger_main = logging.getLogger(__name__) # Use a logger instance for __main__
    dummy_llm = "DUMMY_LLM_CLIENT"

    logger_main.info("--- Testing QnaGeneratorAgent Creation ---")

    # Test with "enabled"
    enabled_qna_agent = create_qna_generator_agent("enabled", mock_llm_client_for_adk_agent=dummy_llm)
    if enabled_qna_agent:
        logger_main.info(f"Created agent: {enabled_qna_agent.name}")
        if isinstance(enabled_qna_agent.instruction, PromptTemplate):
             logger_main.info(f"Instruction template:\n{enabled_qna_agent.instruction.template[:300]}...")
        else:
            logger_main.info(f"Instruction text:\n{enabled_qna_agent.instruction[:300]}...")
    else:
        logger_main.error("Failed to create QnaGeneratorAgent when 'enabled'.")

    # Test with "disabled"
    disabled_qna_agent = create_qna_generator_agent("disabled", mock_llm_client_for_adk_agent=dummy_llm)
    if disabled_qna_agent is None:
        logger_main.info("Correctly returned None for QnaGeneratorAgent when 'disabled'.")
    else:
        logger_main.error(f"Incorrectly created an agent when 'disabled': {disabled_qna_agent}")

    # Example state for rendering
    mock_state_qna = {
        "document_analysis_json_str": '{"slides": [{"slide_number": 1, "text": "Key topic A"}, {"slide_number": 2, "text": "Important detail B"}], "error": null}'
    }
    if enabled_qna_agent and isinstance(enabled_qna_agent.instruction, PromptTemplate):
        rendered_qna_prompt = enabled_qna_agent.instruction.render(**mock_state_qna)
        logger_main.info("\n--- Rendered Prompt Example (QnaGeneratorAgent) ---")
        logger_main.info(rendered_qna_prompt)

    logger_main.info("--- End of QnaGeneratorAgent __main__ test ---")
