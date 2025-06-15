import yaml
import os
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# Determine the absolute path to the config file relative to this util file.
# This assumes utils/ is a subdirectory of presenta_ai/ and config/ is also a subdirectory of presenta_ai/.
# presenta_ai/
# |-- utils/
# |   └── config_loader.py
# |-- config/
# |   └── agent_config_options.yaml
CONFIG_FILE_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "config", "agent_config_options.yaml")
)

# Memoization cache for the loaded config
_cached_config = None

def load_agent_config_options() -> Dict[str, Any]:
    """
    Loads the agent_config_options.yaml file and returns its content.
    Uses a simple memoization cache to avoid redundant file reads.
    """
    global _cached_config
    if _cached_config is not None:
        return _cached_config

    if not os.path.exists(CONFIG_FILE_PATH):
        logger.error(f"Configuration file not found: {CONFIG_FILE_PATH}")
        # Attempt a fallback path assuming CWD is project root 'presenta_ai'
        fallback_path = os.path.normpath("config/agent_config_options.yaml")
        if os.path.exists(fallback_path):
            current_config_path = fallback_path
            logger.info(f"Using fallback configuration file path: {current_config_path}")
        else:
            # Attempt another fallback: CWD is *inside* 'presenta_ai' (e.g. 'presenta_ai/adk_logic')
            # and the script needs to go up one level then to config.
            # This case is less likely if the module structure is used correctly.
            # For robustness, we primarily rely on the initial CONFIG_FILE_PATH calculation.
            # If still not found, this will be an issue.
            current_config_path = CONFIG_FILE_PATH # Stick to original for error message
            logger.error(f"Fallback configuration file also not found: {fallback_path}")
            raise FileNotFoundError(f"Agent configuration file not found at '{current_config_path}' or fallback '{fallback_path}'. CWD: {os.getcwd()}")
    else:
        current_config_path = CONFIG_FILE_PATH


    try:
        with open(current_config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        _cached_config = config_data
        return config_data
    except Exception as e:
        logger.error(f"Error loading or parsing YAML configuration from {current_config_path}: {e}")
        # In case of error, return an empty dict to prevent crashes, though functionality will be degraded.
        return {}


def get_prompt_fragment(agent_key: str, selection_id: str) -> str:
    """
    Retrieves a specific prompt_fragment from the loaded agent configuration.

    Args:
        agent_key (str): The key for the agent (e.g., "logic_critic").
        selection_id (str): The 'id' of the selected option for that agent.

    Returns:
        str: The prompt fragment string, or an empty string if not found.
    """
    config = load_agent_config_options()
    if not config: # If config loading failed
        logger.warning(f"Prompt fragment not found for '{agent_key}/{selection_id}' due to config load failure.")
        return ""

    try:
        agent_config = config.get("agent_options", {}).get(agent_key, {})
        options: List[Dict[str, Any]] = agent_config.get("options", [])

        for option in options:
            if option.get("id") == selection_id:
                return option.get("prompt_fragment", "")

        logger.warning(f"Prompt fragment not found for agent_key='{agent_key}', selection_id='{selection_id}'.")
        return "" # Return empty string if not found
    except Exception as e:
        logger.error(f"Error accessing prompt fragment for '{agent_key}/{selection_id}': {e}")
        return ""


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    logger.info("--- Testing config_loader.py ---")

    # Test loading the whole config
    full_config = load_agent_config_options()
    if full_config:
        logger.info("Successfully loaded agent_config_options.yaml:")
        # logger.info(json.dumps(full_config, indent=2)) # Using json for pretty print if needed
    else:
        logger.error("Failed to load agent_config_options.yaml in test.")

    logger.info("\n--- Testing get_prompt_fragment ---")

    # Test existing fragment
    lc_strict_fragment = get_prompt_fragment("logic_critic", "strict")
    if lc_strict_fragment:
        logger.info(f"Logic Critic (Strict) Fragment (first 50 chars): '{lc_strict_fragment[:50]}...'")
    else:
        logger.error("Failed to get 'logic_critic/strict' fragment.")

    ap_newbie_fragment = get_prompt_fragment("audience_persona", "newbie")
    if ap_newbie_fragment:
        logger.info(f"Audience Persona (Newbie) Fragment (first 50 chars): '{ap_newbie_fragment[:50]}...'")
    else:
        logger.error("Failed to get 'audience_persona/newbie' fragment.")

    # Test non-existing fragment
    non_existent_fragment = get_prompt_fragment("logic_critic", "non_existent_id")
    if not non_existent_fragment:
        logger.info("Correctly received empty string for non-existent fragment 'logic_critic/non_existent_id'.")
    else:
        logger.error("Incorrectly received a fragment for 'logic_critic/non_existent_id'.")

    qna_enabled_fragment = get_prompt_fragment("qna_generator", "enabled")
    if qna_enabled_fragment == "": # Expecting empty string as per YAML
        logger.info("Correctly received empty string for 'qna_generator/enabled' fragment.")
    else:
        logger.error(f"Received non-empty fragment for 'qna_generator/enabled': '{qna_enabled_fragment}'")

    # Test a non-existent agent key
    non_existent_agent_key_fragment = get_prompt_fragment("non_existent_agent", "strict")
    if not non_existent_agent_key_fragment:
        logger.info("Correctly received empty string for non-existent agent key 'non_existent_agent'.")
    else:
        logger.error("Incorrectly received a fragment for 'non_existent_agent'.")

    logger.info("--- End of config_loader.py test ---")
