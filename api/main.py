from fastapi import FastAPI
from pydantic import BaseModel
import threading

app = FastAPI()

recommender_func = None


class QueryRequest(BaseModel):
    query: str


def load_recommender():
    global recommender_func
    from Experiments.rag import get_balanced_recommendations
    recommender_func = get_balanced_recommendations
    print("Recommender loaded successfully")


@app.on_event("startup")
def startup_event():
    thread = threading.Thread(target=load_recommender)
    thread.daemon = True
    thread.start()


@app.get("/health")
def health_check():
    if recommender_func is None:
        return {"status": "starting"}
    return {"status": "healthy"}


@app.post("/recommend")
def recommend(request: QueryRequest):
    if recommender_func is None:
        return {"error": "Model is still loading. Please wait."}

    try:
        recommendations = recommender_func(request.query, top_k=10)
        formatted = []

        for rec in recommendations:
            formatted.append({
                "url": rec["url"],
                "name": rec["name"],
                "description": rec["description"],
                "duration": rec["duration"],
                "test_type": rec["test_type"],
                "adaptive_support": rec["adaptive_support"],
                "remote_support": rec["remote_support"]
            })

        return {"recommended_assessments": formatted}

    except Exception as e:
        print(f"Recommendation error: {e}")
        return {"recommended_assessments": []}

