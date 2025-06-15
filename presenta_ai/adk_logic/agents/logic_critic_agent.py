"""
Agent responsible for critiquing the logical structure of a presentation.

This module defines the `LogicCriticAgent`, an LlmAgent that evaluates the
presentation's arguments, claims, and evidence based on the document analysis,
presentation goal, and audience profile. Its behavior (e.g., strictness)
can be configured via a `selection_id` which alters its prompt using
a fragment loaded from `agent_config_options.yaml`.
"""
import logging # For __main__ block

from google.adk.agents import LlmAgent
from google.adk.prompts import PromptTemplate
from presenta_ai.utils.config_loader import get_prompt_fragment # Import the new loader

LOGIC_CRITIC_BASE_PROMPT_TEMPLATE = PromptTemplate(
    """
    You are an expert in reviewing the logical structure of presentations.
    Based on the following document analysis (JSON string), presentation goal, and audience information,
    provide a detailed review of the overall storyline, the claims on each slide (if identifiable from analysis),
    the logical consistency of the supporting evidence, and the persuasiveness of the arguments.

    # Document Analysis Result (JSON String)
    {{document_analysis_json_str}}

    # Presentation Goal
    {{presentation_goal}}

    # Audience Information
    Role: {{audience_profile.role}}
    Interests: {{audience_profile.interests}}

    Your review should be textual.
    """
)

def create_logic_critic_agent(selection_id: str, mock_llm_client_for_adk_agent=None) -> LlmAgent:
    """
    Factory function to create the Logic Critic Agent.

    This agent reviews the logical flow, consistency of arguments, and
    persuasiveness of a presentation. The specific critique style (e.g., strict,
    supportive) is determined by the `selection_id`, which loads a corresponding
    prompt fragment.

    Args:
        selection_id (str): The identifier for the desired agent behavior
            (e.g., "strict", "supportive"), corresponding to an option in
            `agent_config_options.yaml` for the 'logic_critic'.
        mock_llm_client_for_adk_agent: An optional mock LLM client instance.

    Returns:
        LlmAgent: An instance of the Logic Critic Agent.
    """
    prompt_fragment = get_prompt_fragment('logic_critic', selection_id) # Use the real config loader

    base_instruction_text = LOGIC_CRITIC_BASE_PROMPT_TEMPLATE.template

    final_instruction_text = f"{base_instruction_text}\n\n# Your review policy for this session\n{prompt_fragment}"

    return LlmAgent(
        name=f"LogicCriticAgent_{selection_id}",
        model="gemini-1.5-pro-preview-0409",
        instruction=final_instruction_text,
        output_key="logic_critic_review_text",
        llm=mock_llm_client_for_adk_agent
    )

if __name__ == '__main__':
    # This __main__ block will now rely on utils.config_loader being correct
    # and agent_config_options.yaml being in the expected location relative to config_loader.py
    # or the CWD if fallbacks in config_loader are used.
    if not logging.getLogger().hasHandlers(): # Ensure logging is configured for direct runs
        logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__) # Use a logger for __main__ output

    dummy_llm = "DUMMY_LLM_CLIENT" # Placeholder for mock client instance

    logger.info("--- Testing LogicCriticAgent Creation with config_loader ---")
    strict_critic = create_logic_critic_agent("strict", mock_llm_client_for_adk_agent=dummy_llm)
    logger.info(f"Created agent: {strict_critic.name}")
    logger.info(f"Instruction starts with: {strict_critic.instruction[:150]}...")
    # logger.info(f"Instruction ends with: ...{strict_critic.instruction[-150:]}\n") # Full log can be long

    supportive_critic = create_logic_critic_agent("supportive", mock_llm_client_for_adk_agent=dummy_llm)
    logger.info(f"Created agent: {supportive_critic.name}")
    logger.info(f"Instruction starts with: {supportive_critic.instruction[:150]}...")
    # logger.info(f"Instruction ends with: ...{supportive_critic.instruction[-150:]}\n")

    mock_state = {
        "document_analysis_json_str": '{"slides": [{"slide_number": 1, "text": "Intro"}]}',
        "presentation_goal": "To inform.",
        "audience_profile": {"role": "students", "interests": "learning"}
    }

    # Test rendering of the base prompt (ADK LlmAgent does this internally with state)
    rendered_base_prompt = LOGIC_CRITIC_BASE_PROMPT_TEMPLATE.render(**mock_state)
    logger.info("\n--- Rendered Base Prompt Example ---")
    logger.info(rendered_base_prompt)
    logger.info("--- End of LogicCriticAgent __main__ test ---")
