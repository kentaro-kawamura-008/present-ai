import asyncio
import json
import logging
from typing import Dict, Any, Callable

from google.adk.agents import LlmAgent, Runner, BaseAgent, SequentialAgent # Added SequentialAgent
from google.adk.sessions import InMemorySessionService, Session, State
from google.adk.prompts import PromptTemplate

from presenta_ai.utils.mock_gcs_client import MockGCSClient
from presenta_ai.utils.mock_llm_client import MockVertexAIClient
from presenta_ai.adk_logic.data_models import (
    AudienceProfile,
    PresentaAiState,
    DocumentAnalysisResult,
    FinalReport, # Added for future use
    SlideReview # Added for future use
)

from .agents.document_analyzer_agent import create_document_analyzer_agent
from .agents.logic_critic_agent import create_logic_critic_agent # Import new agent
from .agents.audience_persona_agent import create_audience_persona_agent # Import new agent

logging.basicConfig(level=logging.INFO) # Ensure logging is configured
logger = logging.getLogger(__name__)

mock_gcs_client = MockGCSClient()
mock_llm_client = MockVertexAIClient()
session_service = InMemorySessionService()

async def run_review_process(
    gcs_file_path: str,
    presentation_goal: str,
    audience_profile_dict: Dict[str, str],
    selected_configs: Dict[str, str], # Will use this for selection_id
    progress_callback: Callable[[str], None]
) -> Dict[str, Any]:
    logger.info("Starting run_review_process...")
    progress_callback("Initializing review process...")

    # Create agent instances using factories
    # Pass the global mock_llm_client to each agent factory
    doc_analyzer_agent = create_document_analyzer_agent(mock_llm_client_for_adk_agent=mock_llm_client)

    # Use selection_id from selected_configs, with fallbacks if keys are missing
    logic_critic_selection = selected_configs.get("logic_critic", "strict") # Default to "strict"
    logic_critic_agent = create_logic_critic_agent(
        selection_id=logic_critic_selection,
        mock_llm_client_for_adk_agent=mock_llm_client
    )

    audience_persona_selection = selected_configs.get("audience_persona", "skeptical") # Default to "skeptical"
    audience_persona_agent = create_audience_persona_agent(
        selection_id=audience_persona_selection,
        mock_llm_client_for_adk_agent=mock_llm_client
    )

    # Define the root agent as a SequentialAgent
    # This will run doc_analyzer_agent, then logic_critic_agent, then audience_persona_agent in order.
    # Each agent will read from and write to the same session state.
    root_sequential_agent = SequentialAgent(
        name="PresentationReviewWorkflow",
        sub_agents=[
            doc_analyzer_agent,
            logic_critic_agent,
            audience_persona_agent
        ]
    )

    runner = Runner(
        agent=root_sequential_agent, # The SequentialAgent is now the root
        session_service=session_service,
        app_name="PresentaAI_Reviewer_Workflow"
    )

    audience = AudienceProfile(**audience_profile_dict)
    initial_state_data = PresentaAiState(
        gcs_file_path=gcs_file_path,
        presentation_goal=presentation_goal,
        audience_profile=audience,
        selected_configs=selected_configs,
    )
    initial_state_dict = initial_state_data.model_dump()

    session_id = f"review_session_workflow_{asyncio.get_event_loop().time()}"
    user_id = "test_user_workflow"

    logger.info(f"Creating session '{session_id}' for user '{user_id}' with initial state: {initial_state_dict}")

    initial_message_to_agent = "Start full presentation review." # Generic trigger for the workflow

    progress_callback("Starting presentation review workflow...")
    logger.info(f"Running sequential agent workflow for session '{session_id}'")

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        message=initial_message_to_agent,
        initial_state=initial_state_dict
    ):
        logger.info(f"ADK Event: {event.type} from {event.author} - {event.id}")
        # Progress can be more granular here by checking event.author or event.type
        if event.author == doc_analyzer_agent.name and event.is_final_response():
            progress_callback(f"{doc_analyzer_agent.name} completed.")
        elif event.author == logic_critic_agent.name and event.is_final_response():
            progress_callback(f"{logic_critic_agent.name} ({logic_critic_selection} mode) completed.")
        elif event.author == audience_persona_agent.name and event.is_final_response():
            progress_callback(f"{audience_persona_agent.name} ({audience_persona_selection} mode) completed.")

        if event.is_final_response() and event.author == root_sequential_agent.name: # Workflow completion
            logger.info(f"Sequential workflow completed. Final event content from workflow: {event.content}")
            progress_callback("Full review workflow complete.")
            break

    updated_session = await session_service.get_session(
        app_name=runner.app_name, user_id=user_id, session_id=session_id
    )
    final_state = PresentaAiState(**updated_session.state)

    logger.info(f"Final state after workflow execution: {final_state.model_dump_json(indent=2)}")

    # Parse DocumentAnalysisResult from the JSON string
    doc_analysis_json_str = final_state.document_analysis_json_str
    parsed_doc_analysis = None
    if doc_analysis_json_str:
        try:
            parsed_doc_analysis = DocumentAnalysisResult.model_validate_json(doc_analysis_json_str)
            logger.info(f"Successfully parsed DocumentAnalysisResult: {parsed_doc_analysis.model_dump_json(indent=2)}")
        except Exception as e:
            logger.error(f"Error parsing DocumentAnalysisResult JSON from state: {e}")
            parsed_doc_analysis = DocumentAnalysisResult(slides=[], error=str(e))
    else:
        logger.warning("No 'document_analysis_json_str' found in final state.")
        parsed_doc_analysis = DocumentAnalysisResult(slides=[], error="Output from DocumentAnalyzerAgent was missing.")

    # Construct the results dictionary
    # This will eventually be a FinalReport Pydantic model.
    # For now, returning individual pieces.
    results_payload = {
        "document_analysis": parsed_doc_analysis.model_dump() if parsed_doc_analysis else None,
        "logic_critic_review": final_state.logic_critic_review_text,
        "audience_persona_review": final_state.audience_persona_review_text,
        # "final_report" will be added when ReportSynthesizerAgent is integrated
    }

    # Clean up None values if any agent failed to produce output
    results_payload = {k: v for k, v in results_payload.items() if v is not None}
    if not results_payload:
        return {"error": "Full review process failed to produce any output."}

    return results_payload


async def main_test():
    def simple_progress_callback(message: str):
        print(f"[Progress]: {message}")

    mock_gcs_file_path = "gs://mock-bucket/presentations/main_runner_test.pdf"
    mock_presentation_goal = "To showcase sequential agent execution."
    mock_audience_profile = {"role": "Developers", "interests": "ADK and agent workflows."}
    # These selected_configs will now be used by the agent factories
    mock_selected_configs = {
        "logic_critic": "supportive",
        "audience_persona": "newbie",
        "qna_generator": "disabled" # QnA agent not yet implemented
    }

    mock_gcs_client.upload_blob_from_string(
        blob_name="presentations/main_runner_test.pdf",
        data_string="Dummy PDF content for main_runner_test.",
        bucket_name="mock-bucket"
    )

    logger.info("--- Running main_test for Sequential Agent Workflow ---")
    results = await run_review_process(
        gcs_file_path=mock_gcs_file_path,
        presentation_goal=mock_presentation_goal,
        audience_profile_dict=mock_audience_profile,
        selected_configs=mock_selected_configs,
        progress_callback=simple_progress_callback
    )
    logger.info("\n--- main_test Sequential Workflow Results ---")
    logger.info(json.dumps(results, indent=2))
    logger.info("--- End of main_test ---")

if __name__ == "__main__":
    asyncio.run(main_test())
