# SHL Assessment Recommendation System

A GenAI-powered recommendation engine that maps Natural Language Queries and Job Descriptions (JDs) to relevant SHL Assessments.

## 🔗 Live Links
*   **API Endpoints:**  https://shl-assessment-recommender-backend-05je.onrender.com/health  and https://shl-assessment-recommender-backend-05je.onrender.com/recommend
*   **Frontend UI:** https://shl-assessment-recommender-hctvkr5qsd2ljiedxekwkc.streamlit.app/


##  Project Structure
This project follows a modular architecture:

```text
shl-recommendation-engine/
├── api/                  # FastAPI Backend (Endpoints matched to Appendix 2)
│   └── main.py
├── frontend/             # Streamlit User Interface
│   └── app.py
├── data/                 # Data Storage
│   └── shl_data.json     # Scraped catalog (377+ items)
├── experiments/          # Core RAG Logic & Embeddings
│   └── rag.py
├── scraper/              # Data Ingestion Pipeline
│   └── scraper.py
├── evaluation/           # Accuracy Metrics & CSV Generation
│   └── evaluate.py
└── requirements.txt      # Dependencies

 Setup & Installation
1. Install Dependencies
code:
pip install -r requirements.txt

2. Data Ingestion
The dataset is already included in data/shl_data.json. To re-crawl the SHL catalog:
python -m scraper.scraper
This script uses offset-based pagination to ensure full catalog coverage (377 items).

3. Run the Backend (API)
Run this command from the root directory:
Bash
uvicorn api.main:app --reload
The API will start at http://localhost:8000.

4. Run the Frontend (UI)
code:
streamlit run frontend/app.py

Technical Approach
1. Data Pipeline (scraper/)
We built a custom crawler that navigates SHL's pagination logic. It cleans HTML content and extracts metadata (Duration, Adaptive Support) while strictly filtering out "Pre-packaged Job Solutions" as per requirements.
2. Retrieval Engine (experiments/rag.py)
Model: Uses sentence-transformers/all-mpnet-base-v2 for state-of-the-art semantic embedding.
Vector Store: ChromaDB is used for low-latency retrieval.
Hybrid Logic:
Semantic Search: Finds conceptually related tests (e.g., "Developer" -> "Java Assessment").
Keyword Boosting: Prioritizes exact title matches to improve recall.
Balancing: Detects queries requiring soft skills (e.g., "Manager") and forces a mix of "Knowledge" and "Personality" assessments.
3. API & Deployment (api/)
The solution is exposed via a FastAPI backend adhering to the strict JSON schema defined in the assessment guidelines.
Evaluation
Metric: Mean Recall@10
Result: The system achieves high accuracy by combining vector similarity with metadata filtering.

