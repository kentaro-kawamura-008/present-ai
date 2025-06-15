"""
Main Streamlit application for Presenta-AI.

This application provides a user interface for uploading presentations,
configuring an AI-powered review team, and viewing the generated feedback.
It integrates with backend logic defined in `adk_logic` and utilities in `utils`.
"""
import streamlit as st
import os
import asyncio
import json
from typing import Optional, Dict, Any # For type hinting in _get_auto_composition_from_backend

try:
    from utils.mock_gcs_client import MockGCSClient
    from adk_logic.main_runner import run_review_process
    from utils.config_loader import load_agent_config_options, get_agent_config_yaml_string
    from adk_logic.prompts.auto_compose_prompt import get_auto_compose_prompt
    from utils.mock_llm_client import MockVertexAIClient
except ImportError as e:
    st.error(f"Failed to import necessary modules: {e}. Ensure 'presenta_ai' is in PYTHONPATH if running from a subdirectory.")
    # Minimal Fallback implementations for UI to partially load and show errors.
    class MockGCSClient:
        def bucket(self, *args, **kwargs): return self
        def blob(self, *args, **kwargs): return self
        def upload_from_string(self, *args, **kwargs): st.warning("Dummy GCS Client: upload_from_string called.")
    async def run_review_process(*args, **kwargs):
        st.warning("Dummy `run_review_process` active due to import error.")
        # Using dict() constructor for maximum explicitness to avoid parsing issues.
        final_report_dummy = dict(
            summary_review="Dummy summary (ImportError).",
            storyline_review="Dummy storyline (ImportError).",
            slide_by_slide_reviews=[],
            qna_list=[]
        )
        return dict(
            error="Backend not available due to import error.",
            final_report=final_report_dummy
        )
    def load_agent_config_options(): st.warning("Dummy `load_agent_config_options` active."); return {"agent_options": {}}
    def get_agent_config_yaml_string(): st.warning("Dummy `get_agent_config_yaml_string` active."); return "dummy_yaml_content: {}"
    def get_auto_compose_prompt(*args, **kwargs): st.warning("Dummy `get_auto_compose_prompt` active."); return "Dummy auto-compose prompt"
    class MockVertexAIClient:
        def generate_content(self, *args, **kwargs):
            st.warning("Dummy `MockVertexAIClient` for auto-compose active.")
            return type('DummyResponse', (), {'text': '{"logic_critic": "strict", "audience_persona": "skeptical", "qna_generator": "disabled"}'})()


# Initialize session state variables
# These variables persist across user interactions.
default_session_vars = {
    'mock_gcs_client': MockGCSClient(), # Instance of the GCS client (mocked for now)
    'mock_llm_client_instance': MockVertexAIClient(), # Instance of LLM client for auto-compose
    'gcs_file_path': None, # Path to the uploaded file in GCS (simulated)
    'presentation_goal': "", # User-defined goal of the presentation
    'audience_profile': {"role": "", "interests": ""}, # User-defined audience profile
    'review_results': None, # Stores the results from the backend review process
    'processing': False, # Flag to indicate if a review is currently in progress
    'selected_configs': {},  # Stores user's choices for each agent's behavior
    'agent_options_config': None, # Caches the loaded agent configuration options (from YAML)
    'agent_config_yaml_str': None # Caches the raw YAML string of agent configurations
}
for var, default_val in default_session_vars.items():
    if var not in st.session_state:
                "storyline_review": "Dummy storyline: Narrative is understandable from dummy backend.",
                "slide_by_slide_reviews": [
                    {"slide_number": 1, "evaluation": "Dummy eval for slide 1 (dummy backend)", "suggestion": "Dummy suggestion for slide 1 (dummy backend)"},
                    {"slide_number": 2, "evaluation": "Dummy eval for slide 2 (dummy backend)", "suggestion": "Dummy suggestion for slide 2 (dummy backend)"}
                ],
                "qna_list": [
                    {"question": "Dummy Q1 from dummy backend?", "answer": "Dummy A1 from dummy backend."},
                ]
            }
        }
    def load_agent_config_options(): return {"agent_options": {}}
    def get_agent_config_yaml_string(): return "dummy_yaml: {}"
    def get_auto_compose_prompt(*args, **kwargs): return "Dummy auto-compose prompt"
    class MockVertexAIClient:
        def generate_content(self, *args, **kwargs): return type('DummyResponse', (), {'text': '{"logic_critic": "strict"}'})()


# Initialize session state variables
default_session_vars = {
    'mock_gcs_client': MockGCSClient(),
    'mock_llm_client_instance': MockVertexAIClient(),
    'gcs_file_path': None,
    'presentation_goal': "",
    'audience_profile': {"role": "", "interests": ""},
    'review_results': None,
    'processing': False,
    'selected_configs': {},
    'agent_options_config': None,
    'agent_config_yaml_str': None
}
for var, default_val in default_session_vars.items():
    if var not in st.session_state:
        st.session_state[var] = default_val

if st.session_state.agent_options_config is None:
    try:
        st.session_state.agent_options_config = load_agent_config_options()
        st.session_state.agent_config_yaml_str = get_agent_config_yaml_string()
    except Exception as e:
        st.error(f"Failed to load agent_config_options.yaml: {e}")
        st.session_state.agent_options_config = {"agent_options": {}}
        st.session_state.agent_config_yaml_str = "error_loading_yaml: {}"

async def _get_auto_composition_from_backend(prompt_str: str) -> Optional[Dict[str, str]]:
    try:
        try: from google.generativeai.types import Content, Part # type: ignore
        except ImportError: Content, Part = dict, dict # type: ignore Fallback if type hints are not available

        contents_for_llm = ([Content(parts=[Part(text=prompt_str)], role="user")] # type: ignore
                           if Content is not dict else [{"role": "user", "parts": [{"text": prompt_str}]}])

        response = st.session_state.mock_llm_client_instance.generate_content(
            contents=contents_for_llm, model="gemini-1.5-pro-mock",
            _mock_routing_hint_prompt_text=prompt_str
        )
        if response and response.text:
            suggestions = json.loads(response.text)
            return suggestions if isinstance(suggestions, dict) else None
        return None
    except Exception as e: st.error(f"Error in auto-composition LLM call: {e}"); return None

def render_team_summary_sidebar():
    with st.sidebar:
        st.header("✨ Team Summary ✨")

        agent_options_config = st.session_state.agent_options_config.get("agent_options", {})
        selected_configs = st.session_state.selected_configs

        if not agent_options_config or not selected_configs:
            st.caption("Configure your team to see summary.")
            return

        total_cost_factor = 0.0
        focus_keywords = []

        for agent_key, selected_option_id in selected_configs.items():
            agent_config = agent_options_config.get(agent_key)
            if agent_config:
                options = agent_config.get("options", [])
                for option in options:
                    if option.get("id") == selected_option_id:
                        total_cost_factor += option.get("cost_factor", 0.0)
                        # Use the option's label for display, fallback to ID
                        focus_keywords.append(option.get("label", selected_option_id))
                        break

        st.metric(label="Est. Cost Factor", value=f"{total_cost_factor:.1f}")

        if focus_keywords:
            st.subheader("Review Focus:")
            for keyword in focus_keywords:
                st.markdown(f"- {keyword}")
        else:
            st.caption("No specific focus determined from selections.")

def main():
    st.set_page_config(layout="wide", page_title="Presenta-AI", initial_sidebar_state="expanded")
    st.title("Presenta-AI") # Changed title back to English
    st.write("Welcome to Presenta-AI! Your AI-powered presentation reviewer.")

    render_team_summary_sidebar() # Renders the sidebar with team composition summary

    # Main layout with two columns for input and configuration
    col1, col2 = st.columns(2)

    with col1:
        st.header("1. Presentation Details")
        uploaded_file = st.file_uploader("Upload your presentation", type=["pptx", "pdf"])
        if uploaded_file:
            # Process file only if it's a new file
            if st.session_state.get('last_uploaded_filename') != uploaded_file.name:
                st.session_state.gcs_file_path = f"gs://mock_bucket/uploads/{uploaded_file.name}" # Simulate a GCS path
                st.session_state.last_uploaded_filename = uploaded_file.name
                st.info(f"File '{uploaded_file.name}' ready. Path: {st.session_state.gcs_file_path}")
                # Simulate GCS upload for the mock flow
                try:
                    file_bytes = uploaded_file.getvalue()
                    # The mock GCS client expects a string, latin-1 is forgiving for binary data.
                    # A real GCS client would handle bytes directly.
                    file_content_str = file_bytes.decode('latin-1')
                    bucket = st.session_state.mock_gcs_client.bucket("mock_bucket")
                    blob = bucket.blob(f"uploads/{uploaded_file.name}")
                    blob.upload_from_string(file_content_str)
                except Exception as e:
                    st.error(f"Error during mock GCS upload: {e}")

        st.session_state.presentation_goal = st.text_area("Goal:", value=st.session_state.presentation_goal, height=100, help="What is the primary objective of this presentation?")
        st.subheader("Audience")
        st.session_state.audience_profile["role"] = st.text_input("Role:", value=st.session_state.audience_profile["role"], help="E.g., Technical Managers, Potential Investors, New Recruits")
        st.session_state.audience_profile["interests"] = st.text_area("Interests:", value=st.session_state.audience_profile["interests"], height=100, help="E.g., Technical details, ROI, Company culture, Product features")

    with col2:
        st.header("2. Configure AI Review Team")

        # AI Auto-Composition Button
        if st.button("🤖 AI Auto-Compose Team", help="Let AI suggest a team configuration based on your goal and audience.", use_container_width=True):
            if st.session_state.presentation_goal and st.session_state.audience_profile["role"] and st.session_state.audience_profile["interests"]: # Check for all parts of audience profile
                if st.session_state.agent_config_yaml_str and not st.session_state.agent_config_yaml_str.startswith("error"):
                    prompt_str = get_auto_compose_prompt(
                        presentation_goal=st.session_state.presentation_goal,
                        audience_profile=st.session_state.audience_profile,
                        config_options_yaml_str=st.session_state.agent_config_yaml_str
                    )
                    # Run the async helper function to get suggestions
                    suggestions = asyncio.run(_get_auto_composition_from_backend(prompt_str))
                    if suggestions:
                        st.session_state.selected_configs.update(suggestions) # Apply suggestions
                        st.success("AI team composition suggested and applied!")
                        st.experimental_rerun() # Rerun to update radio button selections
                else:
                    st.error("Agent configuration YAML not available for AI Auto-Composition.")
            else:
                st.warning("Please provide Presentation Goal and full Audience Profile (Role & Interests) for optimal AI Auto-Composition.")
        st.markdown("---") # Visual separator

        # Manual Agent Configuration
        agent_options = st.session_state.agent_options_config.get("agent_options", {})
        # If agent_options failed to load, and selected_configs is empty, populate with some defaults
        if not agent_options and not st.session_state.selected_configs:
            st.session_state.selected_configs = {
                "logic_critic": "strict",
                "audience_persona": "skeptical",
                "qna_generator": "enabled"
            }

        for agent_key, config in agent_options.items():
            st.subheader(config.get("name", agent_key.replace("_", " ").title())) # Make agent key more readable if name missing
            st.caption(config.get("description", ""))
            options_list = config.get("options", [])
            if not options_list: continue

            opt_ids = [opt["id"] for opt in options_list]
            opt_labels = {opt["id"]: opt.get("label", opt["id"]) for opt in options_list} # Use label from config, fallback to id

            if agent_key not in st.session_state.selected_configs or st.session_state.selected_configs[agent_key] not in opt_ids:
                st.session_state.selected_configs[agent_key] = opt_ids[0] # Default to first if not set or invalid

            selected_id = st.radio(
                f"Policy for {config.get('name', agent_key)}:", options=opt_ids,
                format_func=lambda id_val: opt_labels.get(id_val, id_val),
                key=f"{agent_key}_sel_radio_{st.session_state.selected_configs[agent_key]}", # Make key reactive to changes
                index=opt_ids.index(st.session_state.selected_configs[agent_key]),
                horizontal=True
            )
            if selected_id != st.session_state.selected_configs[agent_key]:
                 st.session_state.selected_configs[agent_key] = selected_id
                 st.experimental_rerun()

            for opt in options_list:
                if opt.get("id") == st.session_state.selected_configs[agent_key]:
                    st.help(f"{opt_labels.get(opt['id'])}: {opt.get('description')}")
            st.markdown("---")

    st.markdown("---")
    st.header("3. Start Review")
    if st.button("Analyze Presentation", type="primary", disabled=st.session_state.processing, use_container_width=True):
        if not st.session_state.gcs_file_path: st.error("Upload a file.")
        elif not st.session_state.presentation_goal: st.error("Enter goal.")
        else:
            st.session_state.processing = True; st.session_state.review_results = None
            prog_area = st.empty()
            def prog_cb(msg: str): prog_area.info(msg)
            try:
                prog_cb("Starting review...")
                sel_conf = st.session_state.selected_configs
                # Ensure sel_conf is populated if it's empty AND agent_options were loaded
                if not sel_conf and agent_options:
                    sel_conf = {
                        key: config.get("options")[0].get("id")
                        for key, config in agent_options.items() if config.get("options")
                    }
                    st.session_state.selected_configs = sel_conf # Persist these defaults if used

                results = asyncio.run(run_review_process(
                    st.session_state.gcs_file_path, st.session_state.presentation_goal,
                    st.session_state.audience_profile, sel_conf, prog_cb
                ))
                st.session_state.review_results = results; prog_area.empty(); st.success("Review complete!")
            except Exception as e: st.error(f"Review error: {e}"); st.session_state.review_results = {"error": str(e)}
            finally: st.session_state.processing = False; st.experimental_rerun()

    if st.session_state.processing: st.info("Review in progress...")

    if st.session_state.review_results:
        st.header("4. Review Output")
        results = st.session_state.review_results
        if "error" in results and not results.get("final_report"): st.error(f"Error: {results['error']}")
        elif "final_report" in results and results["final_report"]:
            data = results["final_report"]
            tab_titles = ["Overall Assessment", "Slide-by-Slide Evaluation"]
            qna_list = data.get("qna_list")
            if qna_list: tab_titles.append("Anticipated Q&A")

            tabs = st.tabs(tab_titles)
            with tabs[0]:
                st.subheader("Summary Review"); st.markdown(data.get("summary_review","N/A"))
                st.subheader("Storyline Review"); st.markdown(data.get("storyline_review","N/A"))
            with tabs[1]:
                sbs_reviews = data.get("slide_by_slide_reviews",[])
                if sbs_reviews:
                    for r_item in sbs_reviews:
                        with st.expander(f"Slide {r_item.get('slide_number','?')} Review"):
                            st.markdown(f"**Evaluation:** {r_item.get('evaluation','N/A')}")
                            st.markdown(f"**Suggestion:** {r_item.get('suggestion','N/A')}")
                else: st.write("No slide-by-slide reviews available.")
            if qna_list: # Only attempt to access tabs[2] if qna_list exists
                with tabs[2]:
                    for qna_item in qna_list:
                        st.markdown(f"**Q:** {qna_item.get('question','N/A')}\n\n**A:** {qna_item.get('answer','N/A')}")
                        st.markdown("---") # Separator for Q&A items
        else: st.json(results) # Fallback for unexpected structure

if __name__ == "__main__":
    main()
