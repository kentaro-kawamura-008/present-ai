import yaml # For the dummy get_prompt_fragment
import os # For the dummy get_prompt_fragment path

from google.adk.agents import LlmAgent
from google.adk.prompts import PromptTemplate

# Placeholder for the actual config loading utility
# This dummy version is to make the agent file runnable standalone for now.
# It will be replaced by a call to a utility in presenta_ai/utils/config_loader.py
def _dummy_get_prompt_fragment(agent_key: str, selection_id: str) -> str:
    # Construct the path to the YAML file relative to this script's directory
    # This is fragile and depends on where this script is located relative to config.
    # A proper solution would use a more robust path resolution or pass config data.
    try:
        config_path = os.path.join(
            os.path.dirname(__file__), # adk_logic/agents/
            "..", # adk_logic/
            "config",
            "agent_config_options.yaml"
        )
        config_path = os.path.normpath(config_path)

        if not os.path.exists(config_path):
            # Fallback if running from a different working directory (e.g. project root)
             config_path = os.path.join(
                "presenta_ai", # Assuming 'presenta_ai' is the project root in PYTHONPATH
                "config",
                "agent_config_options.yaml"
            )
             config_path = os.path.normpath(config_path)
             if not os.path.exists(config_path):
                 config_path = os.path.join( # If CWD is presenta_ai
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
        if agent_key == "logic_critic" and selection_id == "strict":
            return "You are an extremely demanding critic. Do not overlook even the smallest logical contradiction, and point it out specifically and incisively. Your feedback must always be paired with a concrete suggestion for improvement."
    return "Default prompt fragment (error in dummy loader)."


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
    """
    # In the future, this will call:
    # from presenta_ai.utils.config_loader import get_prompt_fragment
    # prompt_fragment = get_prompt_fragment('logic_critic', selection_id)
    prompt_fragment = _dummy_get_prompt_fragment('logic_critic', selection_id)

    # The LlmAgent's instruction can be a string or a PromptTemplate.
    # If it's a string, ADK implicitly wraps it.
    # If it's a PromptTemplate, ADK uses it directly.
    # Here, we construct the final instruction string first.

    # The base prompt is already a PromptTemplate. We need its text.
    base_instruction_text = LOGIC_CRITIC_BASE_PROMPT_TEMPLATE.template # Access the template string

    final_instruction_text = f"{base_instruction_text}\n\n# Your review policy for this session\n{prompt_fragment}"

    return LlmAgent(
        name=f"LogicCriticAgent_{selection_id}", # Make name unique per configuration
        model="gemini-1.5-pro-preview-0409", # Placeholder, will be mocked
        instruction=final_instruction_text, # Pass the fully constructed string
        # Input keys expected by the combined prompt:
        # document_analysis_json_str, presentation_goal, audience_profile.role, audience_profile.interests
        # These will be pulled from the ADK State by the LlmAgent.
        # Note: For nested dictionary access like 'audience_profile.role',
        # ensure the state has 'audience_profile' as a dictionary.
        # The PresentaAiState Pydantic model handles this structure.
        output_key="logic_critic_review_text",
        llm=mock_llm_client_for_adk_agent
    )

if __name__ == '__main__':
    # Test the dummy fragment loader and agent creation
    dummy_llm = "DUMMY_LLM_CLIENT"

    print("--- Testing LogicCriticAgent Creation ---")
    strict_critic = create_logic_critic_agent("strict", mock_llm_client_for_adk_agent=dummy_llm)
    print(f"Created agent: {strict_critic.name}")
    print(f"Instruction starts with: {strict_critic.instruction[:150]}...")
    print(f"Instruction ends with: ...{strict_critic.instruction[-150:]}\n")

    supportive_critic = create_logic_critic_agent("supportive", mock_llm_client_for_adk_agent=dummy_llm)
    print(f"Created agent: {supportive_critic.name}")
    print(f"Instruction starts with: {supportive_critic.instruction[:150]}...")
    print(f"Instruction ends with: ...{supportive_critic.instruction[-150:]}\n")

    # Test how PromptTemplate handles nested access (it does it via dot notation in template)
    # Example state:
    mock_state = {
        "document_analysis_json_str": '{"slides": [{"slide_number": 1, "text": "Intro"}]}',
        "presentation_goal": "To inform.",
        "audience_profile": {"role": "students", "interests": "learning"}
    }

    # Render the base prompt manually for checking (ADK LlmAgent does this internally)
    rendered_base_prompt = LOGIC_CRITIC_BASE_PROMPT_TEMPLATE.render(**mock_state)
    print("\n--- Rendered Base Prompt Example ---")
    print(rendered_base_prompt)

    # The final instruction string (which strict_critic.instruction would be)
    # would be this rendered base prompt + the fragment.
    # The LlmAgent internally will take its final_instruction_text,
    # treat it as a template, and render it using keys from the ADK State.
