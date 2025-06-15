"""
Mock LLM (Vertex AI) client for local development and testing of Presenta-AI.

This module provides `MockVertexAIClient` which simulates the behavior of an
LLM client (specifically mimicking aspects of `google.generativeai.GenerativeModel`
or a Vertex AI equivalent). It includes mock response objects (`MockPart`,
`MockContent`, `MockCandidate`, `MockFullLlmResponse`) to emulate the structure
expected by client code, particularly by the ADK's `LlmAgent`.

The `generate_content` method implements routing logic based on keywords found
in the input prompt text. This allows it to return different canned responses
tailored to specific agents (e.g., DocumentAnalyzerAgent, LogicCriticAgent)
or features (e.g., AI Auto-Composition). This is crucial for testing the
end-to-end flow of the application without actual LLM calls.
"""
import json
import logging
from typing import Optional, Dict, Any, List # Removed NamedTuple as it wasn't used

# Attempt to import Pydantic models for type-safe response generation,
# with fallbacks if not available (e.g., during isolated testing of this mock).
try:
    from presenta_ai.adk_logic.data_models import DocumentAnalysisResult, SlideContent, FinalReport, QnAPair, SlideReview
except ImportError:
    logging.warning("MockLLMClient: Could not import data_models. Using placeholder classes for response generation if Pydantic models are expected by callers.")
    class DocumentAnalysisResult: pass # type: ignore
    class SlideContent: pass # type: ignore
    class FinalReport: pass # type: ignore
    class QnAPair: pass # type: ignore
    class SlideReview: pass # type: ignore

# Module-level logger
logger = logging.getLogger(__name__)

class MockPart:
    """Mocks a 'Part' of an LLM response, typically containing text."""
    def __init__(self, text_content: str):
        self.text = text_content

class MockContent:
    """Mocks the 'Content' part of an LLM candidate, containing one or more 'Parts'."""
    def __init__(self, text_content: Optional[str] = None, json_content: Optional[Dict[str, Any]] = None):
        if json_content:
            # If JSON content is provided, serialize it to a string for the Part.
            self.parts = [MockPart(text_content=json.dumps(json_content))]
        elif text_content:
            self.parts = [MockPart(text_content=text_content)]
        else:
            self.parts = [MockPart(text_content="")] # Default to an empty part
        self.role = "model" # Standard role for LLM responses

class MockCandidate:
    """Mocks a 'Candidate' from an LLM response, containing content and metadata."""
    def __init__(self, text_content: Optional[str] = None, json_content: Optional[Dict[str, Any]] = None):
        self.content = MockContent(text_content=text_content, json_content=json_content)
        self.finish_reason = 1 # Corresponds to a "STOP" finish reason
        self.safety_ratings = [] # Placeholder for safety ratings
        self.token_count = 0 # Placeholder for token count

class MockFullLlmResponse:
    """
    Mocks the full response object from an LLM, like `GenerateContentResponse`.
    Contains candidates and provides a convenient `.text` property.
    """
    def __init__(self, text_content: Optional[str] = None, json_content: Optional[Dict[str, Any]] = None):
        self.candidates = [MockCandidate(text_content=text_content, json_content=json_content)]
        # The .text property is often a shortcut to the first candidate's first part's text.
        if self.candidates and self.candidates[0].content.parts:
            self._text_property = self.candidates[0].content.parts[0].text
        else:
            self._text_property = "" # Default to empty string if no content

    @property
    def text(self) -> str:
        """Provides direct access to the text content of the first candidate's first part."""
        return self._text_property

    def to_dict(self): # Common method in some Google SDK response objects
        """Provides a dictionary representation of the mock response."""
        # Simplified; a real to_dict would be more comprehensive.
        return {
            "candidates": [{"content": {"parts": [{"text": part.text for part in self.candidates[0].content.parts}],"role": self.candidates[0].content.role},"finish_reason": self.candidates[0].finish_reason,"safety_ratings": self.candidates[0].safety_ratings,"token_count": self.candidates[0].token_count,}],
            "prompt_feedback": None, # Placeholder for prompt feedback
        }

class MockVertexAIClient:
    """
    A mock LLM client simulating Vertex AI (Gemini) API calls for Presenta-AI.

    This client's `generate_content` method uses keyword-based routing on the
    input prompt text to determine which canned response to return, allowing
    for simulation of different agent behaviors.
    """
    def __init__(self):
        """Initializes the mock client and ensures basic logging is set up."""
        # Ensure logging is configured if this client is used before app-wide setup.
        if not logging.getLogger().hasHandlers(): # Check if root logger has handlers
             logging.basicConfig(level=logging.INFO)
        # self.logger = logging.getLogger(__name__) # Using module-level logger

    def generate_content(self,
                         contents: Any, # Can be string or list of Content-like objects
                         model: Optional[str] = None,
                         generation_config: Optional[Dict[str, Any]] = None,
                         safety_settings: Optional[Dict[str, Any]] = None,
                         tools: Optional[List[Any]] = None, # For future tool calling simulation
                         stream: bool = False,
                         # Internal hints used by this mock for more precise routing:
                         _mock_routing_hint_prompt_text: Optional[str] = None,
                         _mock_routing_hint_gcs_file_path: Optional[str] = None
                        ) -> MockFullLlmResponse:
        """
        Simulates a call to an LLM's `generate_content` method.

        It determines the type of response to generate based on keywords found
        in the `effective_prompt_text_for_logic` (derived from `contents` or
        the `_mock_routing_hint_prompt_text` override).

        Args:
            contents: The prompt content, can be a string or a list of Content-like objects.
            model: The model name (ignored by mock, but logged).
            generation_config: Generation parameters (ignored by mock).
            safety_settings: Safety settings (ignored by mock).
            tools: Tools for function calling (ignored by mock for now).
            stream: Whether to stream the response (ignored by mock, always non-stream).
            _mock_routing_hint_prompt_text: An override for the prompt text used in routing logic.
            _mock_routing_hint_gcs_file_path: A hint for GCS file path, used by some routes.

        Returns:
            MockFullLlmResponse: A mock LLM response object.
        """
        logger.info(f"MockVertexAIClient: generate_content called for model '{model}'. Stream: {stream}")

        # Determine the effective prompt text for routing logic.
        # Prioritize the explicit hint if provided.
        effective_prompt_text_for_logic = _mock_routing_hint_prompt_text
        if not effective_prompt_text_for_logic:
            # Attempt to extract text from 'contents' if it's a list of Content-like objects
            if isinstance(contents, list) and contents and hasattr(contents[0], 'parts') and \
               contents[0].parts and hasattr(contents[0].parts[0], 'text'):
                effective_prompt_text_for_logic = contents[0].parts[0].text
            elif isinstance(contents, str): # Or if 'contents' is just a string
                 effective_prompt_text_for_logic = contents
        effective_prompt_text_for_logic = effective_prompt_text_for_logic or "" # Ensure it's a string

        logger.info(f"MockVertexAIClient: Effective prompt for routing (first 100 chars): '{effective_prompt_text_for_logic[:100]}...'")
        if _mock_routing_hint_gcs_file_path:
            logger.info(f"MockVertexAIClient: GCS file hint provided: {_mock_routing_hint_gcs_file_path}")

        # --- Routing Logic for Mock Responses based on keywords in the prompt ---
        if "propose the most suitable AI review team composition" in effective_prompt_text_for_logic and "Available Configuration Options" in effective_prompt_text_for_logic:
            logger.info("MockVertexAIClient: Routing to AI Auto-Composition mock response.")
            mock_auto_comp_dict = {
                "logic_critic": "supportive",
                "audience_persona": "newbie",
                "qna_generator": "enabled"
            }
            self.logger.info(f"MockVertexAIClient: Auto-Composition JSON: {json.dumps(mock_auto_comp_dict)}")
            return MockFullLlmResponse(json_content=mock_auto_comp_dict)

        elif "DocumentAnalyzerAgent" in effective_prompt_text_for_logic or \
           ("analyze this presentation" in effective_prompt_text_for_logic and _mock_routing_hint_gcs_file_path):
            self.logger.info("MockVertexAIClient: Routing to DocumentAnalyzerAgent mock response.")
            mock_slides_data = [
                {"slide_number": 1, "text": "LLM mock: Intro slide analysis.", "title": "Introduction", "notes": "Key points: A, B, C."},
                {"slide_number": 2, "text": "LLM mock: Market analysis slide.", "title": "Market Overview", "notes": "Data from Source X."},
            ]
            if DocumentAnalysisResult.__name__ == 'DocumentAnalysisResult' and SlideContent.__name__ == 'SlideContent' and hasattr(DocumentAnalysisResult, 'model_dump'):
                 mock_response_dict = DocumentAnalysisResult(slides=[SlideContent(**s_data) for s_data in mock_slides_data]).model_dump()
            else:
                mock_response_dict = { "slides": mock_slides_data, "error": None }
            self.logger.info(f"MockVertexAIClient: DocumentAnalysis JSON: {json.dumps(mock_response_dict)[:100]}...")
            return MockFullLlmResponse(json_content=mock_response_dict)

        elif "LogicCriticAgent" in effective_prompt_text_for_logic:
            self.logger.info("MockVertexAIClient: Routing to LogicCriticAgent mock response.")
            critique_text = "This is a mock logic critique. "
            if "extremely demanding critic" in effective_prompt_text_for_logic:
                critique_text += "The arguments presented lack sufficient evidence."
            elif "supportive mentor" in effective_prompt_text_for_logic:
                critique_text += "The presentation has a good flow. Consider adding a case study."
            else:
                critique_text += "The logical flow seems generally sound."
            self.logger.info(f"MockVertexAIClient: LogicCritique text: '{critique_text[:100]}...'")
            return MockFullLlmResponse(text_content=critique_text)

        elif "AudiencePersonaAgent" in effective_prompt_text_for_logic:
            self.logger.info("MockVertexAIClient: Routing to AudiencePersonaAgent mock response.")
            persona_text = "This is a mock audience persona review. "
            if "skeptical individual" in effective_prompt_text_for_logic:
                persona_text += "As a skeptical audience member, I found the ROI projections overly optimistic."
            elif "no prior knowledge" in effective_prompt_text_for_logic:
                persona_text += "From a novice perspective, the jargon on slide 2 was a bit hard to follow."
            else:
                persona_text += "The presentation was engaging from my perspective."
            self.logger.info(f"MockVertexAIClient: AudiencePersona text: '{persona_text[:100]}...'")
            return MockFullLlmResponse(text_content=persona_text)

        elif "ReportSynthesizerAgent" in effective_prompt_text_for_logic or "synthesize these inputs into a single, structured final report" in effective_prompt_text_for_logic:
            self.logger.info("MockVertexAIClient: Routing to ReportSynthesizerAgent mock response.")
            mock_slide_reviews_data = [
                {"slide_number": 1, "evaluation": "Mock synthesized evaluation for slide 1.", "suggestion": "Mock suggestion for slide 1."},
            ]
            if FinalReport.__name__ == 'FinalReport' and SlideReview.__name__ == 'SlideReview' and hasattr(FinalReport, 'model_dump'):
                report_dict = FinalReport(
                    summary_review="This is a mock summary of the overall presentation review.",
                    storyline_review="The mock storyline review indicates a generally clear narrative.",
                    slide_by_slide_reviews=[SlideReview(**sr_data) for sr_data in mock_slide_reviews_data],
                    qna_list=None
                ).model_dump()
            else:
                report_dict = {"summary_review": "Fallback mock summary.","storyline_review": "Fallback mock storyline review.","slide_by_slide_reviews": mock_slide_reviews_data,"qna_list": None}
            self.logger.info(f"MockVertexAIClient: FinalReport JSON: {json.dumps(report_dict)[:100]}...")
            return MockFullLlmResponse(json_content=report_dict)

        elif "QnaGeneratorAgent" in effective_prompt_text_for_logic or "generates anticipated questions and their answers" in effective_prompt_text_for_logic:
            self.logger.info("MockVertexAIClient: Routing to QnaGeneratorAgent mock response.")
            mock_qna_data = [{"question": "What is the main market opportunity?", "answer": "The main market opportunity is X, valued at Y (mock)."}]
            if QnAPair.__name__ == 'QnAPair' and hasattr(QnAPair, 'model_dump'):
                 qna_list_dict = [QnAPair(**qa_data).model_dump() for qa_data in mock_qna_data]
            else:
                qna_list_dict = mock_qna_data
            self.logger.info(f"MockVertexAIClient: QnA List JSON: {json.dumps(qna_list_dict)[:100]}...")
            return MockFullLlmResponse(json_content=qna_list_dict)

        generic_text = f"Mock LLM response for: '{effective_prompt_text_for_logic[:60]}...'"
        self.logger.info(f"MockVertexAIClient: Returning generic text: '{generic_text}'")
        return MockFullLlmResponse(text_content=generic_text)

AUTO_COMPOSE_PROMPT_TEXT_FOR_MAIN = """
You are a wise project manager. Propose the most suitable AI review team composition...
# Presentation Goal
Test Goal: Get funding
# Audience Information
- Role: Investors
- Interests: ROI
# Available Configuration Options (in YAML format)
--- Start of YAML ---
agent_options:
  logic_critic:
    options: [{id: supportive}, {id: strict}]
  audience_persona:
    options: [{id: newbie}, {id: skeptical}]
  qna_generator:
    options: [{id: enabled}, {id: disabled}]
--- End of YAML ---
# Response Format (Output only the JSON object):
"""

# Constants for other agent tests (ensure these are defined if you copy-paste __main__)
REPORT_SYNTHESIZER_PROMPT_TEXT_FOR_MAIN = """
(ReportSynthesizerAgent) You are a skilled editor...
# Review 1: Comments from the Logic Critic
{{logic_critic_review_text}}
# Review 2: Comments from the Audience Persona
{{audience_persona_review_text}}
# Original Document Information (JSON String from DocumentAnalyzerAgent)
{{document_analysis_json_str}}
"""

QNA_GENERATOR_PROMPT_TEXT_FOR_MAIN = """
(QnaGeneratorAgent) You are an AI assistant that generates anticipated questions and their answers...
# Document Analysis Result (JSON String)
{{document_analysis_json_str}}
"""


class LocalPromptTemplateMockForMain:
    def __init__(self, template_str): self.template_str = template_str
    def render(self, **kwargs):
        res = self.template_str;
        for k, v in kwargs.items(): res = res.replace(f"{{{{{k}}}}}", str(v))
        return res

if __name__ == '__main__':
    if not logging.getLogger().hasHandlers():
        logging.basicConfig(level=logging.INFO)

    logger_main = logging.getLogger(__name__)
    mock_llm = MockVertexAIClient()

    logger_main.info("--- Testing MockLLMClient extended routes in __main__ ---")

    # Test AI Auto-Composition
    rendered_ac_prompt = AUTO_COMPOSE_PROMPT_TEXT_FOR_MAIN
    try:
        from google.generativeai.types import Content, Part # type: ignore
        ac_contents = [Content(parts=[Part(text=rendered_ac_prompt)], role="user")]
    except ImportError:
        ac_contents = [{"role": "user", "parts": [{"text": rendered_ac_prompt}]}] # type: ignore

    response_ac = mock_llm.generate_content(
        contents=ac_contents, model="gemini-1.5-pro-mock",
        _mock_routing_hint_prompt_text=rendered_ac_prompt
    )
    logger_main.info(f"AI Auto-Composition Mock Response (text): {response_ac.text}")
    try:
        parsed_ac = json.loads(response_ac.text)
        logger_main.info(f"Parsed Auto-Composition Response: {parsed_ac}")
        assert "logic_critic" in parsed_ac
    except Exception as e:
        logger_main.error(f"Error parsing Auto-Composition response: {e}")

    # Test ReportSynthesizerAgent
    rs_template = LocalPromptTemplateMockForMain(REPORT_SYNTHESIZER_PROMPT_TEXT_FOR_MAIN)
    rendered_rs_prompt = rs_template.render(
        logic_critic_review_text="Logic good.",
        audience_persona_review_text="Audience happy.",
        document_analysis_json_str='{"slides":[]}'
    )
    try:
        from google.generativeai.types import Content, Part # type: ignore
        rs_contents = [Content(parts=[Part(text=rendered_rs_prompt)], role="user")]
    except ImportError:
        rs_contents = [{"role": "user", "parts": [{"text": rendered_rs_prompt}]}] # type: ignore

    response_rs = mock_llm.generate_content(
        contents=rs_contents, model="gemini-1.5-pro-mock",
        _mock_routing_hint_prompt_text=rendered_rs_prompt
    )
    logger_main.info(f"Report Synthesizer Mock Response (text): {response_rs.text[:200]}...")
    if FinalReport.__name__ == 'FinalReport' and hasattr(FinalReport, 'model_validate_json'):
        try:
            parsed_rs = FinalReport.model_validate_json(response_rs.text)
            logger_main.info(f"Parsed Report Synthesizer Response: {parsed_rs.model_dump_json(indent=2)[:300]}...")
        except Exception as e:
            logger_main.error(f"Error parsing Report Synthesizer response: {e}")
    else:
        logger_main.warning("FinalReport model not fully available for parsing test.")

    # Test QnaGeneratorAgent
    qna_template = LocalPromptTemplateMockForMain(QNA_GENERATOR_PROMPT_TEXT_FOR_MAIN)
    rendered_qna_prompt = qna_template.render(document_analysis_json_str='{"slides":[{"text":"Topic X"}]}')
    try:
        from google.generativeai.types import Content, Part # type: ignore
        qna_contents = [Content(parts=[Part(text=rendered_qna_prompt)], role="user")]
    except ImportError:
        qna_contents = [{"role": "user", "parts": [{"text": rendered_qna_prompt}]}] # type: ignore

    response_qna = mock_llm.generate_content(
        contents=qna_contents, model="gemini-1.5-pro-mock",
        _mock_routing_hint_prompt_text=rendered_qna_prompt
    )
    logger_main.info(f"QnA Generator Mock Response (text): {response_qna.text[:200]}...")
    if QnAPair.__name__ == 'QnAPair' and hasattr(QnAPair, 'model_validate_json'):
        try:
            # QnA response is a list of QnAPair objects
            qna_list_data = json.loads(response_qna.text)
            parsed_qna_list = [QnAPair.model_validate(item) for item in qna_list_data]
            logger_main.info(f"Parsed QnA List (first item if any): {parsed_qna_list[0].model_dump_json() if parsed_qna_list else '[]'}")
        except Exception as e:
            logger_main.error(f"Error parsing QnA Generator response: {e}")
    else:
        logger_main.warning("QnAPair model not fully available for parsing test.")

    logger_main.info("--- End of MockLLMClient extended __main__ test ---")
