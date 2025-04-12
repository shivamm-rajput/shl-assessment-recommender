import os
import google.generativeai as genai
from typing import List, Dict, Union, Optional
import json
import numpy as np
from scraper import get_website_text_content
import re
from database import save_query_and_recommendations

# Configure Google Gemini API
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

def extract_time_constraint(query: str) -> Optional[int]:
    """
    Extract time constraint from a query if present.
    
    Args:
        query: The user query or job description
        
    Returns:
        Maximum duration in minutes or None if not specified
    """
    time_patterns = [
        r'(\d+)\s*min',  # 30 min, 30min
        r'(\d+)\s*minute',  # 30 minutes, 30 minute
        r'less than\s*(\d+)',  # less than 30
        r'within\s*(\d+)',  # within 30
        r'under\s*(\d+)',  # under 30
        r'max.*?(\d+)\s*min',  # max duration of 30 min
        r'maximum.*?(\d+)\s*min',  # maximum of 30 min
        r'no more than\s*(\d+)',  # no more than 30
    ]
    
    for pattern in time_patterns:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except:
                pass
    
    return None

def get_embedding(text: str) -> Optional[List[float]]:
    """
    Get embedding vector for a text using Google Gemini API.
    
    Args:
        text: Text to generate embeddings for
        
    Returns:
        Embedding vector or None if API call fails
    """
    try:
        if not GOOGLE_API_KEY:
            print("Warning: GOOGLE_API_KEY not set. Using fallback recommendation method.")
            return None
            
        model = genai.GenerativeModel('embedding-001')
        embedding = model.embed_content(text)
        return embedding.embedding
    except Exception as e:
        print(f"Error generating embedding: {str(e)}")
        return None

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors.
    
    Args:
        vec1: First vector
        vec2: Second vector
        
    Returns:
        Cosine similarity score (0-1)
    """
    dot_product = np.dot(vec1, vec2)
    norm_vec1 = np.linalg.norm(vec1)
    norm_vec2 = np.linalg.norm(vec2)
    
    if norm_vec1 == 0 or norm_vec2 == 0:
        return 0
        
    return dot_product / (norm_vec1 * norm_vec2)

def fallback_relevance_score(query: str, assessment: Dict[str, str]) -> float:
    """
    Calculate relevance score using keyword matching as fallback when API is unavailable.
    
    Args:
        query: The user query
        assessment: Assessment dictionary
        
    Returns:
        Relevance score (0-1)
    """
    query = query.lower()
    description = assessment.get("description", "").lower()
    name = assessment.get("name", "").lower()
    
    # Define key technical skills and role types to look for
    tech_skills = ["java", "python", "javascript", "js", "sql", "c#", "c++", "react", 
                  "angular", "node", "excel", "data analysis", "coding"]
    
    role_types = ["developer", "engineer", "analyst", "manager", "leader", "executive", 
                 "technical", "business", "data", "hr", "sales", "marketing"]
    
    test_types = {
        "cognitive": ["reasoning", "logic", "problem solving", "analytical", "critical thinking"],
        "personality": ["behavior", "attitude", "team fit", "communication", "collaboration"],
        "skill": ["coding", "technical", "practical", "hands-on"],
        "situational": ["judgment", "scenario", "decision making"]
    }
    
    # Base score
    score = 0.0
    
    # Check for technical skill matches
    for skill in tech_skills:
        if skill in query:
            if skill in name or skill in description:
                score += 0.2
    
    # Check for role type matches
    for role in role_types:
        if role in query:
            if role in name or role in description:
                score += 0.15
    
    # Check for test type preferences
    for test_type, keywords in test_types.items():
        test_mentioned = any(keyword in query for keyword in keywords)
        test_relevant = (test_type.lower() in assessment.get("test_type", "").lower())
        
        if test_mentioned and test_relevant:
            score += 0.25
    
    # Duration check
    time_constraint = extract_time_constraint(query)
    if time_constraint:
        assessment_duration = assessment.get("duration", "")
        match = re.search(r'(\d+)', assessment_duration)
        if match:
            duration_minutes = int(match.group(1))
            if duration_minutes <= time_constraint:
                score += 0.3
            else:
                score -= 0.1  # Penalty for exceeding time constraint
    
    # Remote testing preference
    if "remote" in query.lower() and assessment.get("remote_testing", "").lower() == "yes":
        score += 0.1
    
    # Cap the score at 1.0
    return min(score, 1.0)

def llm_recommendation(query: str, assessments: List[Dict[str, str]], max_results: int = 10) -> List[Dict[str, str]]:
    """
    Use Gemini API to directly recommend assessments based on the query.
    
    Args:
        query: The user query or job description
        assessments: List of assessment dictionaries
        max_results: Maximum number of results to return
        
    Returns:
        List of recommended assessments
    """
    try:
        if not GOOGLE_API_KEY:
            print("Warning: GOOGLE_API_KEY not set. Cannot use LLM recommendations.")
            return []
            
        # Prepare assessment data for the prompt
        assessment_data = "\n".join([
            f"Assessment {i+1}:\nName: {a['name']}\nDescription: {a.get('description', 'N/A')}\n"
            f"Test Type: {a.get('test_type', 'N/A')}\nDuration: {a.get('duration', 'N/A')}\n"
            f"Remote Testing: {a.get('remote_testing', 'N/A')}\nAdaptive Support: {a.get('adaptive_support', 'N/A')}\n"
            for i, a in enumerate(assessments[:30])  # Limit to 30 assessments to fit in context window
        ])
        
        # Create the prompt
        prompt = f"""
        Your task is to recommend the most relevant SHL assessments for the following job requirement or query:
        
        Query: {query}
        
        Available Assessments:
        {assessment_data}
        
        Based on the query, identify the top {min(max_results, 10)} most relevant assessments from the list. 
        Consider factors such as:
        1. Skills and competencies mentioned in the query
        2. Time constraints if specified
        3. Test type requirements (cognitive, personality, skill-based, etc.)
        4. Remote testing needs if mentioned
        
        Provide your recommendations as a JSON array of assessment indices (1-based).
        For example: [3, 15, 7, 21, 4] means assessments 3, 15, 7, 21, and 4 are recommended in that order.
        
        Return only the JSON array, no additional text.
        """
        
        # Call Gemini API
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        
        # Parse the response to extract the recommended indices
        response_text = response.text
        
        # Find the JSON array in the response
        match = re.search(r'\[.*?\]', response_text, re.DOTALL)
        if not match:
            return []
            
        try:
            indices = json.loads(match.group(0))
            
            # Convert 1-based indices to 0-based and filter valid indices
            indices = [i-1 for i in indices if 1 <= i <= len(assessments)]
            
            # Return the recommended assessments
            return [assessments[i] for i in indices[:max_results]]
        except json.JSONDecodeError:
            return []
            
    except Exception as e:
        print(f"Error in LLM recommendation: {str(e)}")
        return []

def get_recommendations(
    input_text: str, 
    assessments: List[Dict[str, str]], 
    is_url: bool = False,
    max_results: int = 10,
    save_to_db: bool = True
) -> List[Dict[str, str]]:
    """
    Get assessment recommendations based on user input.
    
    Args:
        input_text: The user query, job description, or URL
        assessments: List of assessment dictionaries
        is_url: Whether the input is a URL to a job description
        max_results: Maximum number of results to return
        save_to_db: Whether to save the query and results to the database
        
    Returns:
        List of recommended assessments
    """
    try:
        # Handle URL input by extracting text content
        if is_url:
            job_description = get_website_text_content(input_text)
            if not job_description:
                return []
            query = job_description
        else:
            query = input_text
        
        # Extract time constraint if present
        time_constraint = extract_time_constraint(query)
        
        # Try LLM-based recommendation first
        llm_results = llm_recommendation(query, assessments, max_results)
        if llm_results:
            # Save to database if requested
            if save_to_db:
                save_query_and_recommendations(input_text, is_url, llm_results)
            return llm_results
        
        # Fallback to embedding-based search if LLM recommendation fails
        if GOOGLE_API_KEY:
            # Get query embedding
            query_embedding = get_embedding(query)
            
            if query_embedding:
                # Get embeddings for all assessments
                results = []
                for assessment in assessments:
                    # Create a text representation of the assessment
                    assessment_text = f"{assessment['name']} {assessment.get('description', '')}"
                    
                    # Get embedding
                    assessment_embedding = get_embedding(assessment_text)
                    
                    if assessment_embedding:
                        # Calculate similarity
                        similarity = cosine_similarity(query_embedding, assessment_embedding)
                        
                        # Apply duration filter if time constraint exists
                        if time_constraint:
                            duration_match = re.search(r'(\d+)', assessment.get('duration', ''))
                            if duration_match:
                                assessment_duration = int(duration_match.group(1))
                                if assessment_duration > time_constraint:
                                    similarity *= 0.5  # Reduce score for assessments that exceed time limit
                        
                        # Add similarity score to the assessment dictionary
                        assessment_with_score = assessment.copy()
                        assessment_with_score["score"] = similarity
                        
                        results.append((assessment_with_score, similarity))
                
                # Sort by similarity score
                results.sort(key=lambda x: x[1], reverse=True)
                
                # Get top results
                top_results = [result[0] for result in results[:max_results]]
                
                # Save to database if requested
                if save_to_db:
                    save_query_and_recommendations(input_text, is_url, top_results)
                
                return top_results
        
        # Fallback to keyword matching if embedding-based search is unavailable
        results = []
        for assessment in assessments:
            relevance = fallback_relevance_score(query, assessment)
            
            # Add relevance score to the assessment dictionary
            assessment_with_score = assessment.copy()
            assessment_with_score["score"] = relevance
            
            results.append((assessment_with_score, relevance))
        
        # Sort by relevance score
        results.sort(key=lambda x: x[1], reverse=True)
        
        # Filter by time constraint if specified
        if time_constraint:
            filtered_results = []
            for assessment, score in results:
                duration_match = re.search(r'(\d+)', assessment.get('duration', ''))
                if duration_match and int(duration_match.group(1)) <= time_constraint:
                    filtered_results.append((assessment, score))
            
            # If we have filtered results, use them; otherwise, fall back to unfiltered
            if filtered_results:
                results = filtered_results
        
        # Get top results
        top_results = [result[0] for result in results[:max_results]]
        
        # Save to database if requested
        if save_to_db:
            save_query_and_recommendations(input_text, is_url, top_results)
        
        return top_results
        
    except Exception as e:
        print(f"Error in recommendation engine: {str(e)}")
        return []
