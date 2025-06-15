import streamlit as st
import os
import asyncio # Required for running async functions

# Assuming utils and adk_logic packages are in the same directory or Python path is set up
try:
    from utils.mock_gcs_client import MockGCSClient
    from adk_logic.main_runner import run_review_process # Import the backend function
except ImportError as e:
    st.error(f"Failed to import necessary modules: {e}. Ensure utils and adk_logic are in the Python path.")
    # Provide dummy/fallback implementations so the app can partially load
    class MockGCSClient:
        def upload_blob_from_string(self, *args, **kwargs): st.warning("Using dummy MockGCSClient.")
        def blob(self, *args, **kwargs):
            class DummyBlob:
                def upload_from_string(self, *args, **kwargs): pass
            return DummyBlob()
        def bucket(self, *args, **kwargs):
            class DummyBucket:
                def blob(self, *args, **kwargs):
                    class DummyBlob:
                        def upload_from_string(self, *args, **kwargs): pass
                    return DummyBlob()
            return DummyBucket()

    async def run_review_process(*args, **kwargs):
        st.warning("Using dummy run_review_process due to import error.")
        return {"error": "Backend not available due to import error."}

# Initialize mock GCS client (can be session-specific if needed)
if 'mock_gcs_client' not in st.session_state:
    st.session_state.mock_gcs_client = MockGCSClient()

# Initialize session state variables if they don't exist
default_session_vars = {
    'gcs_file_path': None,
    'presentation_goal': "",
    'audience_profile': {"role": "", "interests": ""},
    'review_results': None,
    'processing': False # To manage the state of the review button
}
for var, default_val in default_session_vars.items():
    if var not in st.session_state:
        st.session_state[var] = default_val

def ui_progress_callback(message: str):
    """Callback function to display progress messages in the Streamlit UI."""
    # This could be enhanced to use st.status or st.toast in newer Streamlit versions
    st.info(message)


def main():
    st.title("Presenta-AI")
    st.write("Welcome to Presenta-AI! Your AI-powered presentation reviewer.")

    # File Uploader
    uploaded_file = st.file_uploader(
        "Upload your presentation (.pptx or .pdf)",
        type=["pptx", "pdf"],
        accept_multiple_files=False
    )

    if uploaded_file is not None:
        # Process file only if it's a new file or hasn't been processed yet for this upload instance
        if st.session_state.get('last_uploaded_filename') != uploaded_file.name:
            st.success(f"File '{uploaded_file.name}' uploaded successfully.")
            file_bytes = uploaded_file.getvalue()
            try:
                # This is a simplification. Real GCS client handles bytes.
                # MockGCSClient's upload_blob_from_string expects string.
                file_content_str = file_bytes.decode('latin-1') # latin-1 is more forgiving for binary data
            except Exception:
                file_content_str = f"Content of {uploaded_file.name} (binary data)"

            mock_bucket_name = "mock_presenta_ai_bucket"
            mock_blob_name = f"uploads/{uploaded_file.name}"
            st.session_state.gcs_file_path = f"gs://{mock_bucket_name}/{mock_blob_name}"

            try:
                bucket = st.session_state.mock_gcs_client.bucket(mock_bucket_name)
                blob = bucket.blob(mock_blob_name)
                blob.upload_from_string(file_content_str)
                st.info(f"File simulated as uploaded to: {st.session_state.gcs_file_path}")
                st.session_state.last_uploaded_filename = uploaded_file.name
                st.session_state.review_results = None # Clear previous results
            except Exception as e:
                st.error(f"Error simulating GCS upload: {e}")
                st.session_state.gcs_file_path = None


    # Presentation Goal
    st.session_state.presentation_goal = st.text_area(
        "What is the main goal of your presentation?",
        value=st.session_state.presentation_goal
    )

    # Audience Profile
    st.subheader("Audience Profile")
    st.session_state.audience_profile["role"] = st.text_input(
        "Role/Position of the audience (e.g., Department Manager)",
        value=st.session_state.audience_profile["role"]
    )
    st.session_state.audience_profile["interests"] = st.text_area(
        "Main interests or knowledge level of the audience (e.g., ROI, market potential)",
        value=st.session_state.audience_profile["interests"]
    )

    st.markdown("---")

    # Start Review Button
    if st.button("Start Review", disabled=st.session_state.processing):
        if not st.session_state.gcs_file_path:
            st.error("Please upload a presentation file first.")
        elif not st.session_state.presentation_goal:
            st.error("Please enter the presentation goal.")
        elif not st.session_state.audience_profile["role"] and not st.session_state.audience_profile["interests"]:
            st.warning("Audience profile is not fully specified, but proceeding.")
        else:
            st.session_state.processing = True
            st.session_state.review_results = None # Clear previous results
            progress_bar_slot = st.empty() # For progress messages

            def scoped_progress_callback(message: str):
                progress_bar_slot.info(message)

            try:
                scoped_progress_callback("Starting review process...")
                # Mock selected_configs for now
                mock_selected_configs = {"logic_critic": "strict", "audience_persona": "skeptical", "qna_generator": "enabled"}

                # Run the async function using asyncio.run()
                # This is a blocking call in Streamlit's execution model.
                # For true async feeling in UI, more complex patterns like threads or st.experimental_rerun would be needed
                # but for now, this will work.
                results = asyncio.run(run_review_process(
                    gcs_file_path=st.session_state.gcs_file_path,
                    presentation_goal=st.session_state.presentation_goal,
                    audience_profile_dict=st.session_state.audience_profile,
                    selected_configs=mock_selected_configs,
                    progress_callback=scoped_progress_callback
                ))
                st.session_state.review_results = results
                progress_bar_slot.empty() # Clear progress message area
                st.success("Review process completed!")
            except Exception as e:
                st.error(f"An error occurred during the review process: {e}")
                st.session_state.review_results = {"error": str(e)}
            finally:
                st.session_state.processing = False
                st.experimental_rerun() # Rerun to update button state and display results

    if st.session_state.processing:
        st.info("Review in progress, please wait...")

    # Display Results
    if st.session_state.review_results:
        st.subheader("Review Results")
        if "error" in st.session_state.review_results:
            st.error(f"Error in review: {st.session_state.review_results['error']}")
        if "document_analysis" in st.session_state.review_results:
            st.write("Document Analysis:")
            st.json(st.session_state.review_results["document_analysis"])
        # Add more sections here as other review parts are implemented

    st.markdown("---")
    st.caption("Debug Info (Session State):")
    st.json({
        "gcs_file_path": st.session_state.gcs_file_path,
        "presentation_goal": st.session_state.presentation_goal,
        "audience_profile": st.session_state.audience_profile,
        "processing": st.session_state.processing,
        "last_uploaded_filename": st.session_state.get('last_uploaded_filename')
    })


if __name__ == "__main__":
    main()
