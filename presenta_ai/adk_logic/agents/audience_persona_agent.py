import yaml # For the dummy get_prompt_fragment
import os # For the dummy get_prompt_fragment path

from google.adk.agents import LlmAgent
from google.adk.prompts import PromptTemplate

# Placeholder for the actual config loading utility
# This dummy version is to make the agent file runnable standalone for now.
# It will be replaced by a call to a utility in presenta_ai/utils/config_loader.py
def _dummy_get_prompt_fragment(agent_key: str, selection_id: str) -> str:
    try:
        config_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "config",
            "agent_config_options.yaml"
        )
        config_path = os.path.normpath(config_path)

        if not os.path.exists(config_path):
            config_path = os.path.join(
                "presenta_ai",
                "config",
                "agent_config_options.yaml"
            )
            config_path = os.path.normpath(config_path)
            if not os.path.exists(config_path):
                config_path = os.path.join(
                    "config",
                    "agent_config_options.yaml"
                )
                if not os.path.exists(config_path):
                    raise FileNotFoundError(f"Config file not found at attempted paths near {os.getcwd()}")

        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        options = config.get("agent_options", {}).get(agent_key, {}).get("options", [])
        for option in options:
            if option.get("id") == selection_id:
                return option.get("prompt_fragment", "")
    except Exception as e:
        print(f"DummyError loading prompt fragment for {agent_key}/{selection_id}: {e}. Using default.")
        if agent_key == "audience_persona" and selection_id == "skeptical":
            return "You are a skeptical individual. Constantly demand evidence and data to back up the presentation's claims, and review from a perspective that asks sharp questions about any unconvincing points. Pay special attention to cost-effectiveness and risks."
    return "Default prompt fragment (error in dummy loader)."


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
    """
    # In the future, this will call:
    # from presenta_ai.utils.config_loader import get_prompt_fragment
    # prompt_fragment = get_prompt_fragment('audience_persona', selection_id)
    prompt_fragment = _dummy_get_prompt_fragment('audience_persona', selection_id)

    base_instruction_text = AUDIENCE_PERSONA_BASE_PROMPT_TEMPLATE.template

    final_instruction_text = f"{base_instruction_text}\n\n# Your review policy for this session (embody this persona)\n{prompt_fragment}"

    return LlmAgent(
        name=f"AudiencePersonaAgent_{selection_id}", # Make name unique per configuration
        model="gemini-1.5-pro-preview-0409", # Placeholder, will be mocked
        instruction=final_instruction_text,
        # Input keys expected: document_analysis_json_str, presentation_goal, audience_profile.role, audience_profile.interests
        output_key="audience_persona_review_text",
        llm=mock_llm_client_for_adk_agent
    )

if __name__ == '__main__':
    # Test the dummy fragment loader and agent creation
    dummy_llm = "DUMMY_LLM_CLIENT"

    print("--- Testing AudiencePersonaAgent Creation ---")
    skeptical_agent = create_audience_persona_agent("skeptical", mock_llm_client_for_adk_agent=dummy_llm)
    print(f"Created agent: {skeptical_agent.name}")
    print(f"Instruction starts with: {skeptical_agent.instruction[:150]}...")
    print(f"Instruction ends with: ...{skeptical_agent.instruction[-150:]}\n")

    newbie_agent = create_audience_persona_agent("newbie", mock_llm_client_for_adk_agent=dummy_llm)
    print(f"Created agent: {newbie_agent.name}")
    print(f"Instruction starts with: {newbie_agent.instruction[:150]}...")
    print(f"Instruction ends with: ...{newbie_agent.instruction[-150:]}\n")

    mock_state = {
        "document_analysis_json_str": '{"slides": [{"slide_number": 1, "text": "Intro"}]}',
        "presentation_goal": "To teach.",
        "audience_profile": {"role": "beginner", "interests": "basics"}
    }
    rendered_base_prompt = AUDIENCE_PERSONA_BASE_PROMPT_TEMPLATE.render(**mock_state)
    print("\n--- Rendered Base Prompt Example (Audience Persona) ---")
    print(rendered_base_prompt)
