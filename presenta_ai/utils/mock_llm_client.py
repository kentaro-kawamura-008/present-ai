import json
import logging
from typing import Optional, Dict, Any, NamedTuple, List

try:
    from presenta_ai.adk_logic.data_models import DocumentAnalysisResult, SlideContent
except ImportError:
    logging.warning("Could not import data_models directly, using placeholder for MockLLMClient if needed.")
    class DocumentAnalysisResult: pass # type: ignore
    class SlideContent: pass # type: ignore


class MockPart:
    def __init__(self, text_content: str):
        self.text = text_content

class MockContent:
    def __init__(self, text_content: Optional[str] = None, json_content: Optional[Dict[str, Any]] = None):
        if json_content:
            self.parts = [MockPart(text_content=json.dumps(json_content))]
        elif text_content:
            self.parts = [MockPart(text_content=text_content)]
        else:
            self.parts = [MockPart(text_content="")]
        self.role = "model"

class MockCandidate:
    def __init__(self, text_content: Optional[str] = None, json_content: Optional[Dict[str, Any]] = None):
        self.content = MockContent(text_content=text_content, json_content=json_content)
        self.finish_reason = 1
        self.safety_ratings = []
        self.token_count = 0

class MockFullLlmResponse:
    def __init__(self, text_content: Optional[str] = None, json_content: Optional[Dict[str, Any]] = None):
        self.candidates = [MockCandidate(text_content=text_content, json_content=json_content)]
        if self.candidates and self.candidates[0].content.parts:
            self._text_property = self.candidates[0].content.parts[0].text
        else:
            self._text_property = ""

    @property
    def text(self) -> str:
        return self._text_property

    def to_dict(self):
        return {
            "candidates": [{"content": {"parts": [{"text": part.text for part in self.candidates[0].content.parts}],"role": self.candidates[0].content.role},"finish_reason": self.candidates[0].finish_reason,"safety_ratings": self.candidates[0].safety_ratings,"token_count": self.candidates[0].token_count,}],
            "prompt_feedback": None,
        }

class MockVertexAIClient:
    def __init__(self):
        # Ensure logger is configured when an instance is created
        if not logging.getLogger().hasHandlers(): # Check if root logger has handlers
             logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def generate_content(self,
                         contents: Any,
                         model: Optional[str] = None,
                         generation_config: Optional[Dict[str, Any]] = None,
                         safety_settings: Optional[Dict[str, Any]] = None,
                         tools: Optional[List[Any]] = None,
                         stream: bool = False,
                         _mock_routing_hint_prompt_text: Optional[str] = None,
                         _mock_routing_hint_gcs_file_path: Optional[str] = None
                        ) -> MockFullLlmResponse:
        self.logger.info(f"MockVertexAIClient: generate_content called for model '{model}'. Stream: {stream}")

        effective_prompt_text_for_logic = _mock_routing_hint_prompt_text
        if not effective_prompt_text_for_logic:
            if isinstance(contents, list) and contents and hasattr(contents[0], 'parts') and \
               contents[0].parts and hasattr(contents[0].parts[0], 'text'):
                effective_prompt_text_for_logic = contents[0].parts[0].text
            elif isinstance(contents, str):
                 effective_prompt_text_for_logic = contents
        effective_prompt_text_for_logic = effective_prompt_text_for_logic or ""

        self.logger.info(f"MockVertexAIClient: Effective prompt for routing: '{effective_prompt_text_for_logic[:100]}...'")
        if _mock_routing_hint_gcs_file_path:
            self.logger.info(f"MockVertexAIClient: GCS file hint: {_mock_routing_hint_gcs_file_path}")

        # --- Routing Logic for Mock Responses ---
        if "DocumentAnalyzerAgent" in effective_prompt_text_for_logic or \
           ("analyze this presentation" in effective_prompt_text_for_logic and _mock_routing_hint_gcs_file_path):
            self.logger.info("MockVertexAIClient: Routing to DocumentAnalyzerAgent mock response.")
            mock_slides_data = [
                {"slide_number": 1, "text": "LLM mock: Intro slide analysis.", "title": "Introduction", "notes": "Key points: A, B, C."},
                {"slide_number": 2, "text": "LLM mock: Market analysis slide.", "title": "Market Overview", "notes": "Data from Source X."},
                {"slide_number": 3, "text": "LLM mock: Solution details.", "title": "Proposed Solution", "notes": "Highlight benefits."}
            ]
            # Check if the actual Pydantic models were imported or if placeholders are being used
            if DocumentAnalysisResult.__name__ == 'DocumentAnalysisResult' and SlideContent.__name__ == 'SlideContent' and hasattr(DocumentAnalysisResult, 'model_dump'):
                 mock_response_dict = DocumentAnalysisResult(
                     slides=[SlideContent(**s_data) for s_data in mock_slides_data]
                 ).model_dump()
            else:
                mock_response_dict = { "slides": mock_slides_data, "error": None } # Fallback
            self.logger.info(f"MockVertexAIClient: DocumentAnalysis JSON: {json.dumps(mock_response_dict)[:100]}...")
            return MockFullLlmResponse(json_content=mock_response_dict)

        elif "LogicCriticAgent" in effective_prompt_text_for_logic:
            self.logger.info("MockVertexAIClient: Routing to LogicCriticAgent mock response.")
            critique_text = "This is a mock logic critique. "
            if "extremely demanding critic" in effective_prompt_text_for_logic:
                critique_text += "The arguments presented lack sufficient evidence, and the conclusion on slide 5 does not logically follow from the premises on slide 4. Consider adding statistical data to support your claims."
            elif "supportive mentor" in effective_prompt_text_for_logic:
                critique_text += "The presentation has a good flow, especially the introduction. To further strengthen your argument on slide 3, perhaps include a case study."
            else:
                critique_text += "The logical flow seems generally sound, but could be improved with more specific examples."
            self.logger.info(f"MockVertexAIClient: LogicCritique text: '{critique_text[:100]}...'")
            return MockFullLlmResponse(text_content=critique_text)

        elif "AudiencePersonaAgent" in effective_prompt_text_for_logic:
            self.logger.info("MockVertexAIClient: Routing to AudiencePersonaAgent mock response.")
            persona_text = "This is a mock audience persona review. "
            if "skeptical individual" in effective_prompt_text_for_logic:
                persona_text += "As a skeptical audience member, I found the ROI projections overly optimistic. Where is the data backing the adoption rate assumption?"
            elif "no prior knowledge" in effective_prompt_text_for_logic:
                persona_text += "From a novice perspective, the jargon on slide 2 was a bit hard to follow. Could you explain 'synergistic disintermediation' in simpler terms?"
            else:
                persona_text += "The presentation was engaging from my perspective."
            self.logger.info(f"MockVertexAIClient: AudiencePersona text: '{persona_text[:100]}...'")
            return MockFullLlmResponse(text_content=persona_text)

        generic_text = f"Mock LLM response for: '{effective_prompt_text_for_logic[:60]}...'"
        self.logger.info(f"MockVertexAIClient: Returning generic text: '{generic_text}'")
        return MockFullLlmResponse(text_content=generic_text)

LOGIC_CRITIC_STRICT_PROMPT_TEXT_FOR_MAIN = """
(LogicCriticAgent_strict) You are an extremely demanding critic...
# Document Analysis Result (JSON String)
{{document_analysis_json_str}}
# Presentation Goal
{{presentation_goal}}
# Audience Information
Role: {{audience_profile.role}}
Interests: {{audience_profile.interests}}
"""

AUDIENCE_PERSONA_SKEPTICAL_PROMPT_TEXT_FOR_MAIN = """
(AudiencePersonaAgent_skeptical) You are a skeptical individual...
# Document Analysis Result (JSON String)
{{document_analysis_json_str}}
# Presentation Goal
{{presentation_goal}}
# Audience Information
Role: {{audience_profile.role}}
Interests: {{audience_profile.interests}}
"""

class LocalPromptTemplateMockForMain:
    def __init__(self, template_str): self.template_str = template_str
    def render(self, **kwargs):
        res = self.template_str
        for k, v in kwargs.items(): res = res.replace(f"{{{{{k}}}}}", str(v))
        return res

if __name__ == '__main__':
    # Ensure logging is configured for __main__ execution
    if not logging.getLogger().hasHandlers():
        logging.basicConfig(level=logging.INFO)

    logger_main = logging.getLogger(__name__) # Use a logger instance for __main__

    mock_llm = MockVertexAIClient()

    logger_main.info("--- Testing MockLLMClient in __main__ ---")

    # Test LogicCriticAgent
    lc_template = LocalPromptTemplateMockForMain(LOGIC_CRITIC_STRICT_PROMPT_TEXT_FOR_MAIN)
    rendered_lc_prompt = lc_template.render(
        document_analysis_json_str='{"slides":[]}',
        presentation_goal="Test LC",
        audience_profile={"role":"tester","interests":"testing"}
    )
    try:
        from google.generativeai.types import Content, Part # type: ignore
        lc_contents = [Content(parts=[Part(text=rendered_lc_prompt)], role="user")]
    except ImportError:
        logger_main.warning("google.generativeai.types not available for LC test. Using dicts.")
        lc_contents = [{"role": "user", "parts": [{"text": rendered_lc_prompt}]}] # type: ignore

    response_lc = mock_llm.generate_content(
        contents=lc_contents, model="gemini-1.5-pro-mock",
        _mock_routing_hint_prompt_text=rendered_lc_prompt
    )
    logger_main.info(f"Logic Critic Mock Response: {response_lc.text}")

    # Test AudiencePersonaAgent
    ap_template = LocalPromptTemplateMockForMain(AUDIENCE_PERSONA_SKEPTICAL_PROMPT_TEXT_FOR_MAIN)
    rendered_ap_prompt = ap_template.render(
        document_analysis_json_str='{"slides":[]}',
        presentation_goal="Test AP",
        audience_profile={"role":"persona_tester","interests":"persona_testing"}
    )
    try:
        from google.generativeai.types import Content, Part # type: ignore
        ap_contents = [Content(parts=[Part(text=rendered_ap_prompt)], role="user")]
    except ImportError:
        logger_main.warning("google.generativeai.types not available for AP test. Using dicts.")
        ap_contents = [{"role": "user", "parts": [{"text": rendered_ap_prompt}]}] # type: ignore

    response_ap = mock_llm.generate_content(
        contents=ap_contents, model="gemini-1.5-pro-mock",
        _mock_routing_hint_prompt_text=rendered_ap_prompt
    )
    logger_main.info(f"Audience Persona Mock Response: {response_ap.text}")

    logger_main.info("--- End of MockLLMClient __main__ test ---")
