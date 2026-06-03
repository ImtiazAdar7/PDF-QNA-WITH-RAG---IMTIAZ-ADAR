# Project: PDF Q&A System With RAG
# Author: Imtiaz Adar
# Email: imtiazadarofficial@gmail.com

from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime

class QuestionRequest(BaseModel):
    question: str
    pdf_filename: str
    top_k: int = 5

class AnswerResponse(BaseModel):
    answer: str
    sources: List[Dict]
    response_time_ms: float

class FeedbackRequest(BaseModel):
    rating: int  # 1-5

class UploadResponse(BaseModel):
    filename: str
    chunk_count: int
    message: str

class StatsResponse(BaseModel):
    total_questions: int
    avg_response_time: float
    top_questions: List[Dict]
    pdf_breakdown: Dict