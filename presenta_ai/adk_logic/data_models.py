from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class AudienceProfile(BaseModel):
    role: str = Field(description="The role or position of the audience")
    interests: str = Field(description="The main interests or knowledge level of the audience")

class SlideContent(BaseModel):
    slide_number: int
    text: str
    title: Optional[str] = None
    notes: Optional[str] = None

class DocumentAnalysisResult(BaseModel):
    slides: List[SlideContent]
    error: Optional[str] = None

class SlideReview(BaseModel):
    slide_number: int
    evaluation: str
    suggestion: str

class QnAPair(BaseModel):
    question: str
    answer: str

class FinalReport(BaseModel):
    summary_review: str
    storyline_review: str
    slide_by_slide_reviews: List[SlideReview]
    qna_list: Optional[List[QnAPair]] = None

class PresentaAiState(BaseModel):
    # --- Initial Inputs ---
    gcs_file_path: str
    presentation_goal: str
    audience_profile: AudienceProfile
    selected_configs: Dict[str, str]

    # --- Intermediate Artifacts ---
    document_analysis: Optional[DocumentAnalysisResult] = None
    logic_critic_review_text: Optional[str] = None
    audience_persona_review_text: Optional[str] = None

    # --- Final Outputs ---
    final_report: Optional[FinalReport] = None
