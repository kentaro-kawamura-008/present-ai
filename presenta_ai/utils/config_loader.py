"""
Utility for loading agent configuration options from a YAML file.

This module provides functions to load the `agent_config_options.yaml` file,
parse it into a Python dictionary, retrieve the raw YAML string, and extract
specific prompt fragments based on agent type and selected option.

It includes memoization to cache loaded configurations and avoid redundant
file I/O. It also features robust path resolution to locate the configuration
file, trying multiple common locations relative to the project structure.
"""
import yaml
import os
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Primary expected path: ../config/agent_config_options.yaml (relative to this file in utils/)
CONFIG_FILE_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "config", "agent_config_options.yaml")
)

_cached_config: Optional[Dict[str, Any]] = None
_cached_yaml_string: Optional[str] = None # Cache for the raw YAML string

def _resolve_config_path() -> Optional[str]:
    """
    Resolves the absolute path to the agent configuration YAML file.

    Tries the primary path first, then attempts common fallback locations:
    1. `config/agent_config_options.yaml` (if CWD is project root)
    2. `../config/agent_config_options.yaml` (if CWD is a subdirectory like `adk_logic` or `utils`)

    Returns:
        Optional[str]: The resolved absolute path if the file is found, otherwise None.
    """
    if os.path.exists(CONFIG_FILE_PATH):
        return CONFIG_FILE_PATH

    # Fallback 1: If current working directory is the project root ('presenta_ai')
    fallback_path_project_root_cwd = os.path.normpath("config/agent_config_options.yaml")
    if os.path.exists(fallback_path_project_root_cwd):
        logger.info(f"Using fallback configuration file path (CWD as project root): {fallback_path_project_root_cwd}")
        return fallback_path_project_root_cwd

    # Fallback 2: If current working directory is a subdirectory of 'presenta_ai' (e.g., 'utils', 'adk_logic')
    fallback_path_sub_dir_cwd = os.path.normpath(os.path.join("..", "config", "agent_config_options.yaml"))
    if os.path.exists(fallback_path_sub_dir_cwd):
        logger.info(f"Using fallback configuration file path (CWD possibly inside project subdirectory): {fallback_path_sub_dir_cwd}")
        return fallback_path_sub_dir_cwd

    logger.error(f"Primary configuration file not found: {CONFIG_FILE_PATH}. Fallbacks also failed. Current CWD: {os.getcwd()}")
    return None


def load_agent_config_options() -> Dict[str, Any]:
    """
    Loads the `agent_config_options.yaml` file and returns its content as a dictionary.

    Uses a memoization cache (`_cached_config`) to avoid redundant file reads.
    If the file cannot be found or parsed, it logs an error and returns an empty dictionary.

    Returns:
        Dict[str, Any]: The parsed YAML content, or an empty dictionary on failure.
    """
    global _cached_config
    if _cached_config is not None:
        return _cached_config

    actual_config_path = _resolve_config_path()
    if not actual_config_path:
        logger.error(f"Agent configuration file could not be resolved for load_agent_config_options. Checked: {CONFIG_FILE_PATH} and fallbacks.")
        _cached_config = {} # Cache empty dict to prevent re-attempts if file is truly missing
        return _cached_config

    try:
        with open(actual_config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        _cached_config = config_data if config_data else {} # Ensure not None if file is empty; cache {} if empty
        return _cached_config
    except Exception as e:
        logger.error(f"Error loading or parsing YAML configuration from {actual_config_path}: {e}")
        _cached_config = {} # Cache empty dict on error
        return _cached_config

def get_agent_config_yaml_string() -> str:
    """
    Loads and returns the raw string content of `agent_config_options.yaml`.

    Uses a memoization cache (`_cached_yaml_string`). If the file cannot be
    resolved or read, it logs an error and returns an error message string.

    Returns:
        str: The raw YAML string content, or an error message string on failure.
    """
    global _cached_yaml_string
    if _cached_yaml_string is not None:
        return _cached_yaml_string

    actual_config_path = _resolve_config_path()
    if not actual_config_path:
        logger.error("Cannot get YAML string: Agent configuration file could not be resolved.")
        _cached_yaml_string = "error: config_file_not_found" # Cache error string
        return _cached_yaml_string

    try:
        with open(actual_config_path, 'r') as f:
            yaml_string = f.read()
        _cached_yaml_string = yaml_string
        return yaml_string
    except Exception as e:
        logger.error(f"Error reading YAML configuration file as string from {actual_config_path}: {e}")
        error_str = f"error: could_not_read_config_file: {e}"
        _cached_yaml_string = error_str # Cache error string
        return error_str


def get_prompt_fragment(agent_key: str, selection_id: str) -> str:
    """
    Retrieves a specific prompt_fragment from the loaded agent configuration.

    Args:
        agent_key (str): The key for the agent (e.g., "logic_critic").
        selection_id (str): The 'id' of the selected option for that agent.

    Returns:
        str: The prompt fragment string, or an empty string if not found or on error.
    """
    config = load_agent_config_options()
    if not config: # Handles cases where config is {} due to load failure
        logger.warning(f"Prompt fragment not found for '{agent_key}/{selection_id}' due to config load failure or empty config.")
        return ""
    try:
        agent_config = config.get("agent_options", {}).get(agent_key, {})
        options: List[Dict[str, Any]] = agent_config.get("options", [])
        for option in options:
            if option.get("id") == selection_id:
                return option.get("prompt_fragment", "") # Default to "" if key missing
        logger.warning(f"Prompt fragment not found for agent_key='{agent_key}', selection_id='{selection_id}'.")
        return ""
    except Exception as e: # Catch any other potential errors during dict navigation
        logger.error(f"Error accessing prompt fragment for '{agent_key}/{selection_id}': {e}")
        return ""


if __name__ == '__main__':
# Ensure basic logging is configured if running standalone for testing
    if not logging.getLogger().hasHandlers():
        logging.basicConfig(level=logging.INFO)
    # Use the module's logger instance for __main__ as well
    module_logger = logging.getLogger(__name__) # This will be 'presenta_ai.utils.config_loader' if run as module part

    module_logger.info("--- Testing config_loader.py (extended) ---")

    # Test loading the whole config (already tested, but good to keep)
    full_config = load_agent_config_options()
    if full_config and full_config != {}: # Check against empty dict which load_agent_config_options now returns on error
        module_logger.info("Successfully loaded agent_config_options.yaml into dict.")
    else:
        module_logger.error("Failed to load agent_config_options.yaml into dict in test, or it was empty.")

    # Test getting the raw YAML string
    yaml_str = get_agent_config_yaml_string()
    if yaml_str and not yaml_str.startswith("error:"):
        module_logger.info("Successfully loaded agent_config_options.yaml as raw string.")
        module_logger.info(f"YAML string starts with:\n{yaml_str[:150]}...")
        # Basic check to see if it looks like YAML
        assert "agent_options:" in yaml_str
        assert "logic_critic:" in yaml_str
    else:
        module_logger.error(f"Failed to load agent_config_options.yaml as raw string. Content: {yaml_str}")

    # Test get_prompt_fragment (already tested, but good to keep)
    lc_strict_fragment = get_prompt_fragment("logic_critic", "strict")
    if lc_strict_fragment:
        module_logger.info(f"Logic Critic (Strict) Fragment (first 50 chars): '{lc_strict_fragment[:50]}...'")
    else:
        module_logger.error("Failed to get 'logic_critic/strict' fragment (or config was empty/not found).")

    module_logger.info("--- End of config_loader.py (extended) test ---")
