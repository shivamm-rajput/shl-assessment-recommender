from typing import List, Dict, Any, Set, Tuple
import numpy as np
import json
import os

def compute_recall_at_k(recommendations: List[Dict[str, Any]], relevant_assessments: Set[str], k: int) -> float:
    """
    Compute Recall@K for a single query.
    
    Args:
        recommendations: List of recommended assessments
        relevant_assessments: Set of relevant assessment IDs/names
        k: Number of top recommendations to consider
        
    Returns:
        Recall@K value
    """
    if not relevant_assessments:
        return 0.0
    
    # Get the top K recommendations
    top_k = recommendations[:k]
    
    # Count how many relevant assessments are in the top K
    relevant_in_top_k = sum(1 for rec in top_k if rec.get('name', '') in relevant_assessments)
    
    # Compute recall
    recall = relevant_in_top_k / len(relevant_assessments)
    
    return recall

def compute_average_precision_at_k(recommendations: List[Dict[str, Any]], relevant_assessments: Set[str], k: int) -> float:
    """
    Compute Average Precision@K for a single query.
    
    Args:
        recommendations: List of recommended assessments
        relevant_assessments: Set of relevant assessment IDs/names
        k: Number of top recommendations to consider
        
    Returns:
        Average Precision@K value
    """
    if not relevant_assessments or not recommendations:
        return 0.0
    
    # Limit to top K
    recommendations = recommendations[:k]
    
    # Track relevant items seen
    relevant_seen = 0
    precision_sum = 0.0
    
    # Calculate precision at each position where a relevant item is found
    for i, rec in enumerate(recommendations):
        # Check if the current recommendation is relevant
        is_relevant = rec.get('name', '') in relevant_assessments
        
        if is_relevant:
            relevant_seen += 1
            # Precision at current position
            precision_at_i = relevant_seen / (i + 1)
            precision_sum += precision_at_i
    
    # Compute average precision
    if relevant_seen == 0:
        return 0.0
    
    # Normalize by minimum of K and total relevant assessments
    ap = precision_sum / min(k, len(relevant_assessments))
    
    return ap

def evaluate_recommendations(
    test_queries: List[Dict[str, Any]],
    recommendation_function,
    assessments: List[Dict[str, Any]],
    k: int = 3
) -> Tuple[float, float]:
    """
    Evaluate recommendations using Mean Recall@K and MAP@K.
    
    Args:
        test_queries: List of test query dictionaries with 'query' and 'relevant' fields
        recommendation_function: Function that takes a query and returns recommendations
        assessments: List of assessment dictionaries
        k: Value of K for the metrics
        
    Returns:
        Tuple of (Mean Recall@K, MAP@K)
    """
    recall_values = []
    ap_values = []
    
    for test_query in test_queries:
        query = test_query.get('query', '')
        relevant_assessments = set(test_query.get('relevant', []))
        
        # Get recommendations for this query
        recommendations = recommendation_function(query, assessments)
        
        # Compute Recall@K
        recall = compute_recall_at_k(recommendations, relevant_assessments, k)
        recall_values.append(recall)
        
        # Compute AP@K
        ap = compute_average_precision_at_k(recommendations, relevant_assessments, k)
        ap_values.append(ap)
    
    # Compute mean values
    mean_recall = np.mean(recall_values) if recall_values else 0.0
    map_k = np.mean(ap_values) if ap_values else 0.0
    
    return mean_recall, map_k

def load_test_queries(file_path: str = "test_queries.json") -> List[Dict[str, Any]]:
    """
    Load test queries from a JSON file.
    
    Args:
        file_path: Path to the JSON file containing test queries
        
    Returns:
        List of test query dictionaries or default test queries if file not found
    """
    try:
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                return json.load(f)
        
        # Return default test queries if file not found
        return get_default_test_queries()
    except Exception as e:
        print(f"Error loading test queries: {str(e)}")
        return get_default_test_queries()

def get_default_test_queries() -> List[Dict[str, Any]]:
    """
    Get default test queries for evaluation.
    
    Returns:
        List of default test query dictionaries
    """
    return [
        {
            "query": "I am hiring for Java developers who can also collaborate effectively with my business teams. Looking for an assessment(s) that can be completed in 40 minutes.",
            "relevant": [
                "Verify for Programmers",
                "Verify - Verbal Reasoning",
                "Situational Judgement Test"
            ]
        },
        {
            "query": "Looking to hire mid-level professionals who are proficient in Python, SQL and Java Script. Need an assessment package that can test all skills with max duration of 60 minutes.",
            "relevant": [
                "Verify for Programmers",
                "SQL Assessment",
                "Verify - Inductive Reasoning"
            ]
        },
        {
            "query": "Here is a JD text, can you recommend some assessment that can help me screen applications. Time limit is less than 30 minutes.",
            "relevant": [
                "Verify - Numerical Reasoning",
                "Verify - Verbal Reasoning",
                "ADEPT-15 Personality Assessment"
            ]
        },
        {
            "query": "I am hiring for an analyst and wants applications to screen using Cognitive and personality tests, what options are available within 45 mins.",
            "relevant": [
                "Verify - Numerical Reasoning",
                "OPQ - Occupational Personality Questionnaire",
                "ADEPT-15 Personality Assessment",
                "Verify Interactive - Cognitive Ability"
            ]
        }
    ]

def save_evaluation_results(
    mean_recall: float,
    map_k: float,
    k: int = 3,
    file_path: str = "evaluation_results.json"
) -> bool:
    """
    Save evaluation results to a JSON file.
    
    Args:
        mean_recall: Mean Recall@K value
        map_k: MAP@K value
        k: Value of K used for the metrics
        file_path: Path to save the results
        
    Returns:
        True if successful, False otherwise
    """
    try:
        results = {
            "metrics": {
                f"mean_recall@{k}": mean_recall,
                f"map@{k}": map_k
            },
            "k": k,
            "timestamp": str(np.datetime64('now'))
        }
        
        with open(file_path, "w") as f:
            json.dump(results, f, indent=2)
        
        return True
    except Exception as e:
        print(f"Error saving evaluation results: {str(e)}")
        return False
