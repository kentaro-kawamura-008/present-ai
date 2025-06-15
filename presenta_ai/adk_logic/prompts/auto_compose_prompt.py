"""
Generates a prompt for an LLM to suggest an AI review team composition.

This module provides a function to construct a detailed prompt that asks an LLM
to act as a "wise project manager." Given a presentation's goal, audience profile,
and the available agent configurations (as a YAML string), the LLM is tasked
with proposing an optimal set of agent options. The response is expected in a
specific JSON format.
"""
from typing import Dict, Any
import logging # For __main__ block
import os # For __main__ block

# Logger for this module (not strictly necessary if only __main__ logs)
logger = logging.getLogger(__name__)

def get_auto_compose_prompt(
    presentation_goal: str,
    audience_profile: Dict[str, str], # e.g., {"role": "...", "interests": "..."}
    config_options_yaml_str: str
) -> str:
    """
    Generates the prompt for the LLM to suggest an AI review team composition.

    Args:
        presentation_goal (str): The goal of the presentation.
        audience_profile (Dict[str, str]): A dictionary containing 'role' and 'interests'
                                         of the target audience.
        config_options_yaml_str (str): The raw YAML string of agent configuration options,
                                         as loaded from `agent_config_options.yaml`.

    Returns:
        str: The fully formatted prompt string for the LLM.
    """

    # Format audience_profile for clear inclusion in the prompt
    audience_role_str = audience_profile.get('role', 'Not specified')
    audience_interests_str = audience_profile.get('interests', 'Not specified')
    audience_details_str = f"- Role: {audience_role_str}\n- Interests: {audience_interests_str}"

    prompt = f"""
You are a wise project manager. Propose the most suitable AI review team composition
for the following presentation goal and audience information.
For each agent, select exactly one `id` from the provided options that you believe
would be most effective.
For example, for a critical decision-making presentation to senior management,
"Strict Critique Mode" and "Skeptical Audience" might be appropriate.

Your response MUST be in JSON format, with the agent name (the key from the YAML,
e.g., 'logic_critic') as the key and the selected option's `id` as the value.
Do not include any other text or explanation outside the JSON object.

# Presentation Goal
{presentation_goal}

# Audience Information
{audience_details_str}

# Available Configuration Options (in YAML format)
--- Start of YAML ---
{config_options_yaml_str}
--- End of YAML ---

# Response Format (Output only the JSON object):
{{
  "logic_critic": "id_of_choice",
  "audience_persona": "id_of_choice",
  "qna_generator": "id_of_choice"
  // ... and so on for any other agents defined in the YAML under 'agent_options'
}}
"""
    return prompt

if __name__ == '__main__':
    # Configure basic logging for the __main__ execution
    if not logging.getLogger().handlers: # Check if root logger has handlers
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Use the module's logger for specific messages if preferred, or root logger via logging.info
    main_logger = logging.getLogger(__name__) # Specific logger for __main__ scope

    # Construct a path to the example config file for testing
    # This assumes this script is in adk_logic/prompts/
    # Path: adk_logic/prompts/ -> adk_logic/ -> .. (presenta_ai) -> config/
    example_config_path = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "config", "agent_config_options.yaml")
    )

    example_yaml_str = ""
    try:
        with open(example_config_path, 'r') as f:
            example_yaml_str = f.read()
        main_logger.info(f"Successfully loaded example YAML from: {example_config_path}")
    except FileNotFoundError:
        main_logger.error(f"Error: Could not find agent_config_options.yaml at {example_config_path} for the test.")
        # Fallback YAML string for testing if file not found
        example_yaml_str = """
agent_options:
  logic_critic:
    name: "Logic Critic"
    options:
      - id: "strict"
      - id: "supportive"
  audience_persona:
    name: "Audience Persona"
    options:
      - id: "skeptical"
      - id: "newbie"
  qna_generator:
    name: "Q&A Generator"
    options:
      - id: "enabled"
      - id: "disabled"
"""
        main_logger.info("Using fallback YAML string for testing.")


    test_goal = "To secure Series A funding for a new AI startup."
    test_audience = {"role": "Venture Capitalists", "interests": "Scalability, ROI, team strength, market disruption."}

    generated_prompt = get_auto_compose_prompt(test_goal, test_audience, example_yaml_str)

    # Using main_logger for consistency, or print for direct console output
    main_logger.info("\n--- Generated Auto-Compose Prompt ---")
    main_logger.info(generated_prompt) # Log the prompt (could be long)
    # print(generated_prompt) # Alternatively, print directly
    main_logger.info("--- End of Prompt ---")

    # Example of expected JSON output from LLM (for testing the prompt's clarity)
    main_logger.info("\nExpected LLM JSON output format (example):")
    example_json_output = {
        "logic_critic": "strict",
        "audience_persona": "skeptical",
        "qna_generator": "enabled"
    }
    main_logger.info(json.dumps(example_json_output, indent=2))
    # print(json.dumps(example_json_output, indent=2))
