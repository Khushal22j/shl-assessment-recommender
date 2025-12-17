from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging

from Experiments.rag import get_balanced_recommendations

app = FastAPI(
    title="SHL Assessment Recommender API",
    version="1.0.0"
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("shl-api")

class QueryRequest(BaseModel):
    query: str

class Assessment(BaseModel):
    url: str
    name: str
    description: str
    duration: str | None
    test_type: str | None
    adaptive_support: bool | None
    remote_support: bool | None

class RecommendationResponse(BaseModel):
    recommended_assessments: list[Assessment]

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "shl-assessment-recommender"
    }

@app.post("/recommend", response_model=RecommendationResponse)
async def recommend(request: QueryRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        logger.info(f"Received query: {request.query[:100]}")

        recommendations = get_balanced_recommendations(
            request.query,
            top_k=10
        )

        formatted = []
        for rec in recommendations:
            formatted.append({
                "url": rec.get("url"),
                "name": rec.get("name"),
                "description": rec.get("description"),
                "duration": rec.get("duration"),
                "test_type": rec.get("test_type"),
                "adaptive_support": rec.get("adaptive_support"),
                "remote_support": rec.get("remote_support"),
            })

        logger.info(f"Returning {len(formatted)} recommendations")

        return {
            "recommended_assessments": formatted
        }

    except Exception:
        logger.exception("Recommendation failed")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while generating recommendations"
        )
