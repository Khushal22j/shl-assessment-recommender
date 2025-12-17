from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging
import contextlib

from Experiments.rag import get_balanced_recommendations, ingest_data, collection

# LIFESPAN MANAGER (The modern way to handle startup in FastAPI)
@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Load data if DB is empty
    logger.info("Checking Vector DB status...")
    if collection.count() == 0:
        logger.info("Vector DB is empty. Ingesting data...")
        ingest_data()
        logger.info("Data ingestion complete.")
    else:
        logger.info("Vector DB already populated.")
    yield
    # Shutdown logic (if any) goes here

app = FastAPI(
    title="SHL Assessment Recommender API",
    version="1.0.0",
    lifespan=lifespan # Attach the lifespan logic here
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
    test_type: str | list | None # updated to allow list
    adaptive_support: bool | str | None # updated to allow string 'Yes'/'No'
    remote_support: bool | str | None

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
                "duration": str(rec.get("duration")), # Ensure string for Pydantic
                "test_type": rec.get("test_type"),
                "adaptive_support": rec.get("adaptive_support"),
                "remote_support": rec.get("remote_support"),
            })

        logger.info(f"Returning {len(formatted)} recommendations")

        return {
            "recommended_assessments": formatted
        }

    except Exception as e:
        logger.error(f"Recommendation failed: {str(e)}") # Log the actual error
        raise HTTPException(
            status_code=500,
            detail="Internal server error while generating recommendations"
        )
