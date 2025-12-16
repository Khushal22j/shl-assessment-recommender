import json
import requests
from typing import List, Dict
import pandas as pd
from pathlib import Path

API_URL = "http://localhost:8000/recommend"
K = 10

def load_train_set() -> List[Dict]:
    train_data = [
        {
            "query": "I am hiring for Java developers who can also collaborate effectively with my business teams. Looking for an assessment(s) that can be completed in 40 minutes.",
            "ground_truth_urls": [
                "https://www.shl.com/solutions/products/product-catalog/view/automata-fix-new/",
                "https://www.shl.com/solutions/products/product-catalog/view/core-java-entry-level-new/",
                "https://www.shl.com/solutions/products/product-catalog/view/java-8-new/",
                "https://www.shl.com/solutions/products/product-catalog/view/core-java-advanced-level-new/",
                "https://www.shl.com/products/product-catalog/view/interpersonal-communications/"
            ]
        }
    ]

    try:
        excel_path = "Gen_AI Dataset.xlsx"
        if Path(excel_path).exists():
            df = pd.read_excel(excel_path, sheet_name="Train-Set")
            train_data = []
            for query, group in df.groupby("Query"):
                urls = group["Assessment_url"].tolist()
                train_data.append({
                    "query": query,
                    "ground_truth_urls": urls
                })
            print(f"Loaded {len(train_data)} train queries from Excel")
        else:
            print("Excel file not found. Using sample data.")
    except Exception as e:
        print(f"Error loading Excel: {e}. Using sample data.")

    return train_data

def calculate_recall_at_k(predicted_urls: List[str], ground_truth_urls: List[str], k: int) -> float:
    predicted_top_k = predicted_urls[:k]
    relevant_retrieved = len(set(predicted_top_k) & set(ground_truth_urls))
    total_relevant = len(ground_truth_urls)
    if total_relevant == 0:
        return 0.0
    return relevant_retrieved / total_relevant

def evaluate_model():
    train_data = load_train_set()
    print(f"Evaluating on {len(train_data)} train queries...")
    print("=" * 70)

    results = []
    total_recall = 0

    for i, item in enumerate(train_data, 1):
        query = item["query"]
        ground_truth = item["ground_truth_urls"]

        print(f"\nQuery {i}/{len(train_data)}:")
        print(f"   Query: {query[:80]}...")
        print(f"   Expected URLs: {len(ground_truth)}")

        try:
            response = requests.post(
                API_URL,
                json={"query": query},
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                predictions = data.get("recommended_assessments", [])
                predicted_urls = [p["url"] for p in predictions]
                recall = calculate_recall_at_k(predicted_urls, ground_truth, K)
                found = len(set(predicted_urls[:K]) & set(ground_truth))

                results.append({
                    "query": query[:50] + "...",
                    "ground_truth_count": len(ground_truth),
                    "found_count": found,
                    "recall@10": recall
                })

                total_recall += recall

                print(f"   Found {found}/{len(ground_truth)} relevant assessments")
                print(f"   Recall@{K}: {recall:.4f}")

                matches = set(predicted_urls[:K]) & set(ground_truth)
                if matches:
                    print(f"   Matches: {len(matches)}")
            else:
                print(f"   API Error: {response.status_code}")
                results.append({
                    "query": query[:50] + "...",
                    "ground_truth_count": len(ground_truth),
                    "found_count": 0,
                    "recall@10": 0
                })

        except Exception as e:
            print(f"   Exception: {e}")
            results.append({
                "query": query[:50] + "...",
                "ground_truth_count": len(ground_truth),
                "found_count": 0,
                "recall@10": 0
            })

    mean_recall = total_recall / len(train_data) if train_data else 0

    print("\n" + "=" * 70)
    print("EVALUATION RESULTS")
    print("=" * 70)

    results_df = pd.DataFrame(results)
    print(results_df.to_string(index=False))

    print(f"\nMEAN RECALL@{K}: {mean_recall:.4f}")
    print(f"OVERALL ACCURACY: {mean_recall * 100:.2f}%")

    results_df.to_csv("train_evaluation_results.csv", index=False)
    print("Detailed results saved to: train_evaluation_results.csv")

    return mean_recall, results_df

if __name__ == "__main__":
    mean_recall, results = evaluate_model()
