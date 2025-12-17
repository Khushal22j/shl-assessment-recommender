import json
import chromadb
from sentence_transformers import SentenceTransformer
import os
import re
import google.generativeai as genai
from typing import List, Dict, Tuple
from collections import defaultdict
import numpy as np
import gc  # <--- IMPORTANT: Added for memory management

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "Data", "shl_data.json")

# IMPORTANT: Using the Lite model (80MB) instead of the Base model (450MB)
MODEL_NAME = 'all-MiniLM-L6-v2'
GEMINI_MODEL = "gemini-1.5-flash-latest"

# IMPORTANT: Reduced batch size to prevent Out of Memory (OOM) crashes on Render Free Tier
BATCH_SIZE = 5 
VECTOR_SEARCH_RESULTS = 50

print("Initializing SHL Assessment Recommender...")

print("Loading embedding model...")
# Force CPU device to avoid looking for GPU drivers
model = SentenceTransformer(MODEL_NAME, device='cpu')

client = chromadb.Client()

try:
    collection = client.get_collection(name="shl_assessments")
    print("Loaded existing vector database")
except:
    collection = client.create_collection(name="shl_assessments")
    print("Created new vector database")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel(GEMINI_MODEL)
    print("Gemini API configured")
else:
    print("No Gemini API key found. Using rule-based analysis.")
    gemini_model = None

SKILL_KEYWORDS = {
    'sql': ['sql', 'database', 'mysql', 'postgresql', 'oracle', 'query', 'rdbms'],
    'excel': ['excel', 'spreadsheet', 'pivot', 'vlookup'],
    'python': ['python', 'pandas', 'numpy', 'django', 'flask'],
    'java': ['java', 'j2ee', 'jdk', 'spring', 'hibernate', 'javafx'],
    'javascript': ['javascript', 'js', 'node.js', 'react', 'angular', 'vue'],
    'testing': ['testing', 'qa', 'quality assurance', 'selenium', 'test case'],
    'cloud': ['cloud', 'aws', 'azure', 'gcp', 'amazon web services'],
    'data_analysis': ['data analysis', 'analytics', 'statistics', 'bi', 'business intelligence'],
    'web': ['html', 'css', 'frontend', 'backend', 'web development'],
    'sales': ['sales', 'selling', 'salesforce', 'customer acquisition', 'revenue'],
    'marketing': ['marketing', 'brand', 'campaign', 'digital marketing', 'seo', 'social media'],
    'communication': ['communication', 'english', 'verbal', 'written', 'presentation'],
    'leadership': ['leadership', 'management', 'lead', 'manager', 'supervisor'],
    'admin': ['admin', 'administrative', 'clerical', 'secretarial', 'office'],
    'banking': ['bank', 'financial', 'finance', 'banking', 'accounting', 'teller'],
    'customer_service': ['customer service', 'support', 'helpdesk', 'client service'],
    'analyst': ['analyst', 'analysis', 'reporting', 'metrics', 'kpi'],
    'developer': ['developer', 'programmer', 'coder', 'software engineer'],
    'manager': ['manager', 'management', 'supervisor', 'director'],
    'consultant': ['consultant', 'consulting', 'advisor', 'advisory'],
    'content': ['content', 'writer', 'writing', 'copy', 'editor', 'seo'],
}

EXPERIENCE_LEVELS = {
    'entry': ['entry', 'new', 'graduate', 'fresher', 'junior', '0-2', '0-1', 'beginner', 'basic', 'fundamental'],
    'mid': ['mid', 'intermediate', '3-5', '2-4', 'experienced'],
    'senior': ['senior', 'lead', 'principal', 'expert', 'advanced', '5+', '6+', '7+', '8+', '10+']
}

TEST_TYPE_MAPPING = {
    'K': 'Knowledge & Skills',
    'P': 'Personality & Behavior',
    'A': 'Ability & Aptitude',
    'S': 'Simulations',
    'B': 'Biodata & Situational Judgement',
    'C': 'Competencies',
    'D': 'Development & 360',
    'E': 'Assessment Exercises'
}

def extract_query_keywords(query: str) -> Dict:
    query_lower = query.lower()
    found_skills = []
    for skill, keywords in SKILL_KEYWORDS.items():
        if any(keyword in query_lower for keyword in keywords):
            found_skills.append(skill)

    experience_level = 'mid'
    for level, indicators in EXPERIENCE_LEVELS.items():
        if any(indicator in query_lower for indicator in indicators):
            experience_level = level
            break

    duration = None
    duration_patterns = [
        (r'(\d+)\s*min', 1),
        (r'(\d+)\s*minutes', 1),
        (r'(\d+)\s*hour', 60),
        (r'(\d+)\s*hours', 60),
        (r'30-40', 35),
        (r'40-50', 45),
        (r'50-60', 55),
    ]

    for pattern, multiplier in duration_patterns:
        match = re.search(pattern, query_lower)
        if match:
            try:
                duration = int(match.group(1)) * multiplier
                break
            except:
                pass

    test_type_pref = {'K': 50, 'P': 50}
    technical_skills = ['sql', 'python', 'java', 'javascript', 'testing', 'cloud', 'data_analysis']
    if any(skill in found_skills for skill in technical_skills):
        test_type_pref = {'K': 70, 'P': 30}

    managerial_skills = ['leadership', 'manager', 'communication', 'sales', 'marketing']
    if any(skill in found_skills for skill in managerial_skills):
        test_type_pref = {'K': 40, 'P': 60}

    return {
        'skills': found_skills,
        'experience_level': experience_level,
        'duration': duration,
        'test_type_pref': test_type_pref,
        'original_query': query
    }

def score_skill_match(query_skills: List[str], candidate: Dict) -> float:
    if not query_skills:
        return 0

    candidate_text = f"{candidate['name']} {candidate['description']}".lower()
    candidate_skills = candidate.get('skills', '').lower()
    score = 0

    for skill in query_skills:
        if skill in SKILL_KEYWORDS:
            for keyword in SKILL_KEYWORDS[skill]:
                if keyword in candidate_text:
                    if keyword in candidate['name'].lower():
                        score += 30
                    elif keyword in candidate['description'].lower():
                        score += 20
                    elif keyword in candidate_skills:
                        score += 15

    return min(score, 100)

def score_experience_match(query_level: str, candidate: Dict) -> float:
    candidate_name = candidate['name'].lower()
    level_keywords = EXPERIENCE_LEVELS.get(query_level, [])
    score = 0

    for keyword in level_keywords:
        if keyword in candidate_name:
            score += 25

    if query_level == 'entry':
        if any(term in candidate_name for term in EXPERIENCE_LEVELS['senior']):
            score -= 30
    elif query_level == 'senior':
        if any(term in candidate_name for term in EXPERIENCE_LEVELS['entry']):
            score -= 30

    return score

def score_duration_match(query_duration: int, candidate_duration: int) -> float:
    if not query_duration:
        return 0

    diff = abs(query_duration - candidate_duration)
    if diff == 0:
        return 30
    elif diff <= 10:
        return 20
    elif diff <= 20:
        return 10
    elif diff <= 30:
        return 5
    else:
        return -10

def score_test_type_match(query_test_pref: Dict, candidate_types) -> float:
    if not candidate_types:
        return 0

    if isinstance(candidate_types, str):
        cand_types = [t.strip() for t in candidate_types.split(',')]
    elif isinstance(candidate_types, list):
        cand_types = [str(t).strip() for t in candidate_types]
    else:
        cand_types = [str(candidate_types).strip()]

    score = 0
    for test_type, weight in query_test_pref.items():
        if test_type in cand_types:
            score += weight * 0.5

    return score

def score_keyword_density(query: str, candidate: Dict) -> float:
    query_words = set([w.lower() for w in query.split() if len(w) > 3])
    candidate_text = f"{candidate['name']} {candidate['description']}".lower()
    candidate_words = set(candidate_text.split())
    overlap = len(query_words.intersection(candidate_words))
    if len(query_words) > 0:
        return (overlap / len(query_words)) * 40
    return 0

def enrich_assessment_data(item: Dict) -> Dict:
    enriched = item.copy()
    text = f"{item['name']} {item['description']}".lower()
    found_skills = []

    for skill, keywords in SKILL_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            found_skills.append(skill)

    enriched['skills'] = ', '.join(found_skills[:5])
    test_type = item.get('test_type', [])
    if isinstance(test_type, list):
        enriched['test_type'] = ', '.join([str(t) for t in test_type if t])
    else:
        enriched['test_type'] = str(test_type)

    try:
        enriched['duration'] = int(item.get('duration', 30))
    except:
        enriched['duration'] = 30

    return enriched

def ingest_data():
    if not os.path.exists(DATA_PATH):
        print(f"Error: shl_data.json not found at {DATA_PATH}")
        return 0

    print("Loading assessment data...")

    try:
        with open(DATA_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except UnicodeDecodeError:
        with open(DATA_PATH, 'r', encoding='latin-1') as f:
            data = json.load(f)

    print(f"Loaded {len(data)} assessments")

    enriched_data = [enrich_assessment_data(item) for item in data]
    ids, documents, metadatas = [], [], []

    print("Preparing documents for embedding...")

    for i, item in enumerate(enriched_data):
        doc_text = f"""
        Name: {item['name']}
        Description: {item['description']}
        Skills: {item.get('skills', '')}
        Test Type: {item.get('test_type', '')}
        Duration: {item.get('duration', 30)} minutes
        """
        ids.append(str(i))
        documents.append(doc_text.strip())
        metadatas.append({
            'name': item['name'],
            'url': item['url'],
            'description': item['description'][:300],
            'duration': item['duration'],
            'test_type': item['test_type'],
            'adaptive_support': item.get('adaptive_support', 'No'),
            'remote_support': item.get('remote_support', 'Yes'),
            'skills': item.get('skills', '')
        })

    print("Creating embeddings (Optimized for Low RAM)...")

    # IMPORTANT: Optimized Loop for Low Memory Environments
    for start_idx in range(0, len(ids), BATCH_SIZE):
        end_idx = min(start_idx + BATCH_SIZE, len(ids))
        
        # Get small batch of documents
        batch_docs = documents[start_idx:end_idx]
        
        # Encode batch
        embeddings = model.encode(batch_docs)
        
        # Convert to list if it's a numpy array
        if hasattr(embeddings, 'tolist'):
            embeddings = embeddings.tolist()

        # Add to ChromaDB
        collection.add(
            ids=ids[start_idx:end_idx],
            embeddings=embeddings,
            metadatas=metadatas[start_idx:end_idx],
            documents=batch_docs
        )
        
        print(f"Processed {end_idx}/{len(ids)} assessments")
        
        # MEMORY CLEANUP: Crucial for free tier
        del embeddings
        del batch_docs
        gc.collect()

    print(f"Vector database created with {collection.count()} items")
    return collection.count()

def balance_recommendations(scored_candidates: List[Tuple], query_analysis: Dict, top_k: int = 10) -> List[Dict]:
    if not scored_candidates:
        return []

    candidates_by_type = defaultdict(list)
    for score, candidate in scored_candidates:
        test_types = candidate.get('test_type', '')
        if isinstance(test_types, str):
            cand_types = [t.strip() for t in test_types.split(',') if t.strip()]
        elif isinstance(test_types, list):
            cand_types = [str(t).strip() for t in test_types]
        else:
            cand_types = []

        for t in cand_types:
            candidates_by_type[t].append((score, candidate))

    test_pref = query_analysis.get('test_type_pref', {'K': 50, 'P': 50})
    selected = []
    seen_urls = set()

    for test_type, weight in sorted(test_pref.items(), key=lambda x: x[1], reverse=True):
        if test_type in candidates_by_type:
            num_from_type = max(1, int(top_k * (weight / 100)))
            for score, candidate in candidates_by_type[test_type][:num_from_type]:
                if candidate['url'] not in seen_urls and len(selected) < top_k:
                    selected.append(candidate)
                    seen_urls.add(candidate['url'])

    if len(selected) < top_k:
        for score, candidate in sorted(scored_candidates, key=lambda x: x[0], reverse=True):
            if candidate['url'] not in seen_urls and len(selected) < top_k:
                selected.append(candidate)
                seen_urls.add(candidate['url'])

    return selected[:top_k]

def get_balanced_recommendations(query: str, top_k: int = 10) -> List[Dict]:
    if not query or len(query.strip()) < 3:
        return []

    print(f"Processing query: '{query[:80]}...'")
    query_analysis = extract_query_keywords(query)
    print(f"Analysis: {len(query_analysis['skills'])} skills, {query_analysis['experience_level']} level")

    query_embedding = model.encode([query]).tolist()

    try:
        results = collection.query(
            query_embeddings=query_embedding,
            n_results=VECTOR_SEARCH_RESULTS,
            include=["metadatas", "distances", "documents"]
        )
    except Exception as e:
        print(f"Vector search error: {e}")
        return []

    if not results['metadatas'] or not results['metadatas'][0]:
        print("No results from vector search")
        return []

    scored_candidates = []
    for i, candidate in enumerate(results['metadatas'][0]):
        total_score = 0
        distance = results['distances'][0][i]
        total_score += (1.0 / (1.0 + distance) if distance > 0 else 1.0) * 30
        total_score += score_skill_match(query_analysis['skills'], candidate)
        total_score += score_experience_match(query_analysis['experience_level'], candidate)
        total_score += score_duration_match(query_analysis['duration'], candidate.get('duration', 30))
        total_score += score_test_type_match(query_analysis['test_type_pref'], candidate.get('test_type', ''))
        total_score += score_keyword_density(query, candidate)
        scored_candidates.append((total_score, candidate))

    scored_candidates.sort(key=lambda x: x[0], reverse=True)
    balanced_results = balance_recommendations(scored_candidates, query_analysis, top_k)

    final_recommendations = []
    for candidate in balanced_results:
        test_type_list = [t.strip() for t in str(candidate.get('test_type', '')).split(',') if t.strip()]
        final_recommendations.append({
            'name': candidate.get('name', ''),
            'url': candidate.get('url', ''),
            'description': candidate.get('description', ''),
            'duration': candidate.get('duration', 30),
            'test_type': test_type_list if test_type_list else ['K'],
            'adaptive_support': candidate.get('adaptive_support', 'No'),
            'remote_support': candidate.get('remote_support', 'Yes')
        })

    print(f"Generated {len(final_recommendations)} balanced recommendations")
    return final_recommendations

if __name__ == "__main__":
    print("SHL ASSESSMENT RECOMMENDATION SYSTEM")
    count = ingest_data()
    if count > 0:
        print("System initialized successfully")
    else:
        print("Failed to initialize system")
