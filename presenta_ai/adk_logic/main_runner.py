"""
Main orchestrator for the Presenta-AI review process using the Google ADK.

This module defines the primary asynchronous function `run_review_process`
that sets up and executes a sequence of AI agents to analyze a presentation.
It leverages mock clients for GCS and LLM interactions, making it suitable
for local development and testing. The sequence includes document analysis,
logic critique, audience persona review, Q&A generation (optional), and
final report synthesis.
"""
import asyncio
import json
import logging
from typing import Dict, Any, Callable, List, Optional

from google.adk.agents import Runner, BaseAgent, SequentialAgent # LlmAgent, Session, State not directly used here but are fundamental ADK concepts
from google.adk.sessions import InMemorySessionService

# Application-specific imports
from presenta_ai.utils.mock_gcs_client import MockGCSClient
from presenta_ai.utils.mock_llm_client import MockVertexAIClient
# Data models for state and results
from presenta_ai.adk_logic.data_models import (
    AudienceProfile,
    PresentaAiState,
    DocumentAnalysisResult,
    FinalReport,
    QnAPair # Added QnAPair
)

from .agents.document_analyzer_agent import create_document_analyzer_agent
from .agents.logic_critic_agent import create_logic_critic_agent
from .agents.audience_persona_agent import create_audience_persona_agent
from .agents.report_synthesizer_agent import create_report_synthesizer_agent # Import new agent
from .agents.qna_generator_agent import create_qna_generator_agent # Import new agent

# Ensure logging is configured at the module level
if not logging.getLogger().hasHandlers():
    logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mock_gcs_client = MockGCSClient()
mock_llm_client = MockVertexAIClient()
session_service = InMemorySessionService()

async def run_review_process(
    gcs_file_path: str,
    presentation_goal: str,
    audience_profile_dict: Dict[str, str],
    selected_configs: Dict[str, str],
    progress_callback: Callable[[str], None]
) -> Dict[str, Any]:
    """
    Orchestrates the full AI presentation review process using a sequential agent workflow.

    Args:
        gcs_file_path (str): The GCS path to the presentation file.
        presentation_goal (str): The user-defined goal of the presentation.
        audience_profile_dict (Dict[str, str]): A dictionary describing the audience
            (e.g., {"role": "...", "interests": "..."}).
        selected_configs (Dict[str, str]): User-selected configurations for each agent's
            behavior (e.g., {"logic_critic": "strict", "qna_generator": "enabled"}).
        progress_callback (Callable[[str], None]): A callback function to send progress
            updates to the UI or logger.

    Returns:
        Dict[str, Any]: A dictionary containing the final review report or an error message.
                        Typically, this will be `{"final_report": FinalReport.model_dump()}`.
    """
    logger.info("Starting run_review_process with full agent workflow...")
    progress_callback("Initializing full review process...")

    # 1. Create all agent instances using their respective factory functions.
    #    The mock LLM client is passed to each agent that requires LLM interaction.
    doc_analyzer_agent = create_document_analyzer_agent(mock_llm_client_for_adk_agent=mock_llm_client)

    logic_critic_selection = selected_configs.get("logic_critic", "strict") # Default to "strict" if not provided
    logic_critic_agent = create_logic_critic_agent(
        selection_id=logic_critic_selection,
        mock_llm_client_for_adk_agent=mock_llm_client
    )

    audience_persona_selection = selected_configs.get("audience_persona", "skeptical")
    audience_persona_agent = create_audience_persona_agent(
        selection_id=audience_persona_selection,
        mock_llm_client_for_adk_agent=mock_llm_client
    )

    qna_generator_selection = selected_configs.get("qna_generator", "disabled")
    qna_generator_agent = create_qna_generator_agent( # This might return None
        selection_id=qna_generator_selection,
        mock_llm_client_for_adk_agent=mock_llm_client
    )

    report_synthesizer_agent = create_report_synthesizer_agent(
        mock_llm_client_for_adk_agent=mock_llm_client
    )

    # 2. Construct the list of sub-agents for the SequentialAgent.
    #    The Q&A generator agent is added conditionally based on user selection.
    #    The ReportSynthesizerAgent is always last to compile the final report.
    sub_agents_list: List[BaseAgent] = [
        doc_analyzer_agent,
        logic_critic_agent,
        audience_persona_agent,
    ]
    if qna_generator_agent: # qna_generator_agent will be None if "disabled"
        sub_agents_list.append(qna_generator_agent)
    sub_agents_list.append(report_synthesizer_agent)

    # The root_sequential_agent defines the order of execution.
    root_sequential_agent = SequentialAgent(
        name="FullPresentationReviewWorkflow",
        sub_agents=sub_agents_list
    )

    # The Runner executes the root agent and manages the session.
    runner = Runner(
        agent=root_sequential_agent,
        session_service=session_service,
        app_name="PresentaAI_Full_Reviewer" # Unique name for this ADK application
    )

    # 3. Prepare Initial State for the ADK session.
    #    This state is passed to the first agent and is updated by each subsequent agent.
    audience = AudienceProfile(**audience_profile_dict)
    initial_state_data = PresentaAiState(
        gcs_file_path=gcs_file_path, # Provided by user
        presentation_goal=presentation_goal,
        audience_profile=audience,
        selected_configs=selected_configs,
    )
    initial_state_dict = initial_state_data.model_dump()

    session_id = f"full_review_session_{asyncio.get_event_loop().time()}"
    user_id = "test_user_full_workflow"

    logger.info(f"Creating session '{session_id}' for user '{user_id}' with initial state: {initial_state_dict}")

    initial_message_to_agent = "Start comprehensive presentation review."

    progress_callback("Starting comprehensive presentation review workflow...")
    logger.info(f"Running full sequential agent workflow for session '{session_id}'")

    # 4. Execute the ADK Runner.
    #    The runner processes the initial message through the sequential agent workflow.
    #    Events are streamed back, allowing for progress tracking.
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        message=initial_message_to_agent, # Initial trigger message for the workflow
        initial_state=initial_state_dict # Provide the initial state for the new session
    ):
        logger.info(f"ADK Event: Type='{event.type}', Author='{event.author}', EventID='{event.id}'")
        # Provide progress updates based on which agent has completed its turn.
        if event.is_final_response(): # Check if it's a final response from an agent
            if event.author == doc_analyzer_agent.name:
                progress_callback(f"'{doc_analyzer_agent.name}' completed analysis.")
            elif event.author == logic_critic_agent.name:
                progress_callback(f"'{logic_critic_agent.name}' ({logic_critic_selection} mode) completed critique.")
            elif event.author == audience_persona_agent.name:
                progress_callback(f"'{audience_persona_agent.name}' ({audience_persona_selection} mode) completed persona review.")
            elif qna_generator_agent and event.author == qna_generator_agent.name:
                progress_callback(f"'{qna_generator_agent.name}' completed Q&A generation.")
            elif event.author == report_synthesizer_agent.name:
                progress_callback(f"'{report_synthesizer_agent.name}' completed final report synthesis.")
            elif event.author == root_sequential_agent.name: # This signifies the end of the entire sequence
                logger.info(f"Full review workflow completed. Final content from workflow: {event.content}")
                progress_callback("Comprehensive review workflow complete.")
                break # Exit the loop once the root sequential agent is done.

    # 5. Retrieve the final state from the session after the workflow has run.
    updated_session = await session_service.get_session(
        app_name=runner.app_name, user_id=user_id, session_id=session_id
    )
    final_state = PresentaAiState(**updated_session.state) # Re-parse the state dictionary into Pydantic model
    logger.info(f"Final state after full workflow execution: {final_state.model_dump_json(indent=2)}")

    # Parse various JSON string outputs from the state into their respective Pydantic models.
    parsed_doc_analysis = None
    if final_state.document_analysis_json_str:
        try:
            parsed_doc_analysis = DocumentAnalysisResult.model_validate_json(final_state.document_analysis_json_str)
        except Exception as e:
            logger.error(f"Error parsing DocumentAnalysisResult JSON from state: {e}")
            parsed_doc_analysis = DocumentAnalysisResult(slides=[], error=str(e)) # Create a default error object
    # It can be useful to store the parsed model back into the state if the state object is passed around further,
    # but for this function, we primarily use it for constructing the final return.
    # final_state.document_analysis = parsed_doc_analysis

    parsed_qna_list: Optional[List[QnAPair]] = None
    if final_state.qna_list_json_str:
        try:
            qna_data_list = json.loads(final_state.qna_list_json_str)
            parsed_qna_list = [QnAPair.model_validate(item) for item in qna_data_list]
        except Exception as e:
            logger.error(f"Error parsing QnAPair List JSON from state: {e}")

    parsed_final_report: Optional[FinalReport] = None
    if final_state.final_report_json_str:
        try:
            parsed_final_report = FinalReport.model_validate_json(final_state.final_report_json_str)
            if parsed_final_report and parsed_qna_list and parsed_final_report.qna_list is None:
                logger.info("Merging externally generated QnA list into the final report.")
                parsed_final_report.qna_list = parsed_qna_list
        except Exception as e:
            logger.error(f"Error parsing FinalReport JSON: {e}")

    # 6. Return Results
    if parsed_final_report:
        return {"final_report": parsed_final_report.model_dump()}
    else:
        logger.warning("Final report was not generated by ReportSynthesizerAgent. Returning individual components if available.")
        results_payload = {
            "document_analysis": parsed_doc_analysis.model_dump() if parsed_doc_analysis else None,
            "logic_critic_review": final_state.logic_critic_review_text,
            "audience_persona_review": final_state.audience_persona_review_text,
            "qna_list": [q.model_dump() for q in parsed_qna_list] if parsed_qna_list else None,
            "error_message": "ReportSynthesizerAgent failed to produce a final report."
        }
        results_payload = {k: v for k, v in results_payload.items() if v is not None}
        if not results_payload or all(v is None for k,v in results_payload.items() if k != "error_message"):
             return {"error": "Full review process failed to produce any meaningful output."}
        return results_payload


async def main_test():
    def simple_progress_callback(message: str):
        print(f"[Progress]: {message}")

    mock_gcs_file_path = "gs://mock-bucket/presentations/full_workflow_test.pdf"
    mock_presentation_goal = "To test the full ADK agent workflow."
    mock_audience_profile = {"role": "Testers", "interests": "Functionality and completeness."}
    mock_selected_configs = {
        "logic_critic": "strict",
        "audience_persona": "newbie",
        "qna_generator": "enabled" # Test with QnA enabled
    }

    mock_gcs_client.upload_blob_from_string(
        blob_name="presentations/full_workflow_test.pdf",
        data_string="Dummy PDF content for full_workflow_test.",
        bucket_name="mock-bucket"
    )

    logger.info("--- Running main_test for Full Sequential Agent Workflow ---")
    results = await run_review_process(
        gcs_file_path=mock_gcs_file_path,
        presentation_goal=mock_presentation_goal,
        audience_profile_dict=mock_audience_profile,
        selected_configs=mock_selected_configs,
        progress_callback=simple_progress_callback
    )
    logger.info("\n--- main_test Full Sequential Workflow Results ---")
    logger.info(json.dumps(results, indent=2))

    # Test with QnA disabled
    logger.info("\n--- Running main_test with QnA disabled ---")
    mock_selected_configs_qna_disabled = {
        "logic_critic": "supportive",
        "audience_persona": "skeptical",
        "qna_generator": "disabled"
    }
    results_qna_disabled = await run_review_process(
        gcs_file_path=mock_gcs_file_path,
        presentation_goal=mock_presentation_goal,
        audience_profile_dict=mock_audience_profile,
        selected_configs=mock_selected_configs_qna_disabled,
        progress_callback=simple_progress_callback
    )
    logger.info("\n--- main_test QnA Disabled Workflow Results ---")
    logger.info(json.dumps(results_qna_disabled, indent=2))
    logger.info("--- End of main_runner.py main_test ---")

if __name__ == "__main__":
    asyncio.run(main_test())
