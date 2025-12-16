from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
from Experiments.rag import get_balanced_recommendations

app = FastAPI()

class QueryRequest(BaseModel):
    query: str

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/recommend")
async def recommend(request: QueryRequest):
    try:
        print(f"\nReceived query: {request.query[:100]}...")
        recommendations = get_balanced_recommendations(request.query, top_k=10)
        formatted = []
        for rec in recommendations:
            assessment = {
                "url": rec['url'],
                "name": rec['name'],
                "description": rec['description'],
                "duration": rec['duration'],
                "test_type": rec['test_type'],
                "adaptive_support": rec['adaptive_support'],
                "remote_support": rec['remote_support']
            }
            formatted.append(assessment)
        print(f"Returning {len(formatted)} recommendations")
        return {"recommended_assessments": formatted}
    except Exception as e:
        print(f"Error in recommendation: {e}")
        return {"recommended_assessments": []}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
