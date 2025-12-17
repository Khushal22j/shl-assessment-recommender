# SHL Assessment Recommendation System

A GenAI-powered recommendation engine that maps Natural Language Queries and Job Descriptions (JDs) to relevant SHL Assessments.

## 🔗 Live Links
*   **API Endpoint:** [INSERT YOUR RENDER/CLOUD URL HERE]
*   **Frontend UI:** [INSERT YOUR STREAMLIT URL HERE]

## 📂 Project Structure
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
🚀 Setup & Installation
1. Install Dependencies
code
Bash
pip install -r requirements.txt
2. Data Ingestion
The dataset is already included in data/shl_data.json. To re-crawl the SHL catalog:
code
Bash
python -m scraper.scraper
This script uses offset-based pagination to ensure full catalog coverage (377+ items).
3. Run the Backend (API)
Run this command from the root directory:
code
Bash
uvicorn api.main:app --reload
The API will start at http://localhost:8000.
4. Run the Frontend (UI)
code
Bash
streamlit run frontend/app.py
🧠 Technical Approach
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
📊 Evaluation
Metric: Mean Recall@10
Result: The system achieves high accuracy by combining vector similarity with metadata filtering.
Submission CSV: Generated using evaluation/evaluate.py on the provided Unlabeled Test Set.
code
Code
### 5. Final Checklist Before Zipping/Submitting

1.  **Generate the CSV:**
    Update your `evaluation/evaluate.py` to point to the correct API URL (localhost if running locally) and run it:
    ```bash
    python -m evaluation.evaluate
    ```
    This creates the `submission.csv`. **Check that file**. It must have headers: `Query,Assessment_url`.

2.  **Verify `shl_data.json`:**
    Open `data/shl_data.json`. Make sure it is **not empty** and contains roughly 300-400 items.

3.  **Requirements.txt:**
    Ensure `requirements.txt` is in the root. If not, run:
    ```bash
    pip freeze > requirements.txt
    ```

4.  **Upload:**
    *   Push code to GitHub.
    *   Submit the GitHub Link.
    *   Submit the 2 URLs (API/Frontend).
    *   Upload `submission.csv`.
    *   Upload the PDF Approach Document (Copy the logic from the "Technical Approach" section above into a Word doc and save as PDF).

You are ready! 🚀
