"""
Agent responsible for reviewing a presentation from a specific audience persona's perspective.

This module defines the `AudiencePersonaAgent`, an LlmAgent that evaluates a
presentation's understandability, engagement, and persuasiveness for a given
audience. The specific persona (e.g., skeptical, novice) is determined by a
`selection_id`, which modifies the agent's prompt using a fragment loaded
from `agent_config_options.yaml`.
"""
import logging # For __main__ block

from google.adk.agents import LlmAgent
from google.adk.prompts import PromptTemplate
from presenta_ai.utils.config_loader import get_prompt_fragment # Import the new loader

AUDIENCE_PERSONA_BASE_PROMPT_TEMPLATE = PromptTemplate(
    """
    You are an expert at reviewing a presentation by embodying a specified audience persona.
    Based on the following document analysis (JSON string), presentation goal, and your persona (derived from audience information),
    evaluate whether this presentation is understandable, engaging, and convincing for that audience.

    # Document Analysis Result (JSON String)
    {{document_analysis_json_str}}

    # Presentation Goal
    {{presentation_goal}}

    # Your Persona (Audience Information)
    Role: {{audience_profile.role}}
    Interests: {{audience_profile.interests}}

    Your review should be textual, reflecting the perspective of the specified audience.
    """
)

def create_audience_persona_agent(selection_id: str, mock_llm_client_for_adk_agent=None) -> LlmAgent:
    """
    Factory function to create the Audience Persona Agent.

    This agent steps into the shoes of a defined audience persona to review the
    presentation. The persona's characteristics (e.g., skeptical, novice) are
    set by the `selection_id`, which loads a corresponding prompt fragment.

    Args:
        selection_id (str): The identifier for the desired audience persona
            (e.g., "skeptical", "newbie"), corresponding to an option in
            `agent_config_options.yaml` for the 'audience_persona'.
        mock_llm_client_for_adk_agent: An optional mock LLM client instance.

    Returns:
        LlmAgent: An instance of the Audience Persona Agent.
    """
    prompt_fragment = get_prompt_fragment('audience_persona', selection_id) # Use the real config loader

    base_instruction_text = AUDIENCE_PERSONA_BASE_PROMPT_TEMPLATE.template

    final_instruction_text = f"{base_instruction_text}\n\n# Your review policy for this session (embody this persona)\n{prompt_fragment}"

    return LlmAgent(
        name=f"AudiencePersonaAgent_{selection_id}",
        model="gemini-1.5-pro-preview-0409",
        instruction=final_instruction_text,
        output_key="audience_persona_review_text",
        llm=mock_llm_client_for_adk_agent
    )

if __name__ == '__main__':
    if not logging.getLogger().hasHandlers(): # Ensure logging is configured for direct runs
        logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__) # Use a logger for __main__ output

    dummy_llm = "DUMMY_LLM_CLIENT" # Placeholder for mock client instance

    logger.info("--- Testing AudiencePersonaAgent Creation with config_loader ---")
    skeptical_agent = create_audience_persona_agent("skeptical", mock_llm_client_for_adk_agent=dummy_llm)
    logger.info(f"Created agent: {skeptical_agent.name}")
    logger.info(f"Instruction (skeptical) starts with: {skeptical_agent.instruction[:150]}...")

    newbie_agent = create_audience_persona_agent("newbie", mock_llm_client_for_adk_agent=dummy_llm)
    logger.info(f"Created agent: {newbie_agent.name}")
    logger.info(f"Instruction (newbie) starts with: {newbie_agent.instruction[:150]}...")

    mock_state = {
        "document_analysis_json_str": '{"slides": [{"slide_number": 1, "text": "Intro"}]}',
        "presentation_goal": "To teach.",
        "audience_profile": {"role": "beginner", "interests": "basics"}
    }
    rendered_base_prompt = AUDIENCE_PERSONA_BASE_PROMPT_TEMPLATE.render(**mock_state)
    logger.info("\n--- Rendered Base Prompt Example (Audience Persona) ---")
    logger.info(rendered_base_prompt)
    logger.info("--- End of AudiencePersonaAgent __main__ test ---")
