from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel, AnyHttpUrl
from typing import List, Optional, Dict, Any
import uvicorn
from scraper import fetch_shl_catalog_data, process_shl_catalog
from recommendation_engine import get_recommendations
from utils import validate_url
import json
import os
from database import get_assessments, get_recent_queries, init_db

app = FastAPI(
    title="SHL Assessment Recommendation API",
    description="""
    API for recommending SHL assessments based on job descriptions or queries.
    
    Features:
    - Semantic search for relevant assessments based on job descriptions or queries
    - Filtering by test type, duration, remote testing support, and adaptive testing
    - Query history tracking and recommendation storage
    
    Available test types:
    - Cognitive: Assessments measuring reasoning abilities, problem-solving, and critical thinking
    - Personality: Assessments evaluating behavioral traits, work style, and character attributes
    - Skill: Technical skill evaluations like programming, Microsoft Office, languages, etc.
    - Situational Judgment: Assessments measuring decision-making in workplace scenarios
    """,
    version="1.1.0"
)

class Assessment(BaseModel):
    name: str
    url: str
    remote_testing: str
    adaptive_support: str
    duration: str
    test_type: str

class RecommendationResponse(BaseModel):
    recommendations: List[Assessment]

def load_assessment_data():
    """Load or scrape assessment data from SHL catalog"""
    try:
        # Initialize database
        init_db()
        
        # Try to get assessments from database first
        db_assessments = get_assessments()
        if db_assessments:
            return db_assessments
        
        # If database is empty, try to load from JSON file
        if os.path.exists("shl_assessments.json"):
            with open("shl_assessments.json", "r") as f:
                return json.load(f)
        
        # If no cache, scrape the data
        raw_data = fetch_shl_catalog_data("https://www.shl.com/solutions/products/product-catalog/")
        if not raw_data:
            raise HTTPException(status_code=500, detail="Failed to fetch SHL catalog data")
            
        assessments = process_shl_catalog(raw_data)
        
        # Cache the processed data
        with open("shl_assessments.json", "w") as f:
            json.dump(assessments, f)
            
        return assessments
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading assessment data: {str(e)}")

@app.get("/api/recommendations", response_model=RecommendationResponse)
async def get_recommendation(
    query: Optional[str] = Query(None, description="Natural language query or job description text"),
    url: Optional[str] = Query(None, description="URL to a job description"),
    test_types: Optional[str] = Query(None, description="Comma-separated list of test types to filter by (e.g., 'Cognitive,Personality')"),
    max_duration: Optional[int] = Query(None, description="Maximum assessment duration in minutes"),
    remote_testing: Optional[bool] = Query(None, description="Filter for remote testing support"),
    adaptive_support: Optional[bool] = Query(None, description="Filter for adaptive testing support")
):
    """Get SHL assessment recommendations based on input query or URL with optional filtering"""
    
    # Validate input
    if not query and not url:
        raise HTTPException(status_code=400, detail="Either query or url parameter must be provided")
    
    if url and not validate_url(url):
        raise HTTPException(status_code=400, detail="Invalid URL format")
    
    # Load assessment data
    assessments = load_assessment_data()
    
    # Get recommendations
    input_text = url if url else query
    is_url = True if url else False
    
    # Make sure input_text is not None
    if input_text is None:
        raise HTTPException(status_code=400, detail="Missing query or URL parameter")
    
    # Fetch more recommendations initially to allow for filtering
    recommendations = get_recommendations(
        input_text,
        assessments,
        is_url=is_url,
        max_results=20,  # Increased to account for filtering
        save_to_db=True  # Save query to database
    )
    
    # Process filters if any are provided
    if any([test_types, max_duration is not None, remote_testing is not None, adaptive_support is not None]):
        filtered_recommendations = recommendations.copy()
        
        # Filter by test types
        if test_types:
            test_type_list = [t.strip() for t in test_types.split(',')]
            filtered_recommendations = [rec for rec in filtered_recommendations 
                                     if rec.get('test_type') in test_type_list]
        
        # Filter by max duration
        if max_duration is not None:
            from data_processor import extract_duration
            temp_filtered = []
            for rec in filtered_recommendations:
                duration_minutes = extract_duration(rec.get('duration', 'Unknown'))
                # Include if duration is unknown or within the limit
                if duration_minutes is None or duration_minutes <= max_duration:
                    temp_filtered.append(rec)
            filtered_recommendations = temp_filtered
        
        # Filter by remote testing
        if remote_testing is not None:
            required_value = "Yes" if remote_testing else "No"
            filtered_recommendations = [rec for rec in filtered_recommendations 
                                     if rec.get('remote_testing') == required_value]
        
        # Filter by adaptive support
        if adaptive_support is not None:
            required_value = "Yes" if adaptive_support else "No"
            filtered_recommendations = [rec for rec in filtered_recommendations 
                                     if rec.get('adaptive_support') == required_value]
        
        recommendations = filtered_recommendations
    
    if not recommendations:
        return RecommendationResponse(recommendations=[])
    
    # Convert to response model format
    return RecommendationResponse(recommendations=recommendations)

class UserQueryResponse(BaseModel):
    id: int
    query_text: str
    query_type: str
    is_url: bool
    created_at: str
    recommendations: List[Dict[str, Any]] = []

class QueriesResponse(BaseModel):
    queries: List[UserQueryResponse]

@app.get("/api/queries", response_model=QueriesResponse)
async def get_queries(limit: int = Query(10, description="Maximum number of queries to retrieve")):
    """Get recent user queries and their recommendations"""
    
    # Get recent queries from database
    queries = get_recent_queries(limit=limit)
    
    if not queries:
        return QueriesResponse(queries=[])
    
    return QueriesResponse(queries=queries)

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "SHL Assessment Recommendation API",
        "endpoints": {
            "GET /api/recommendations": "Get assessment recommendations based on query or URL with optional filtering",
            "GET /api/queries": "Get recent user queries and their recommendations"
        },
        "filters": {
            "test_types": "Comma-separated list of test types (Cognitive, Personality, Skill, Situational Judgment)",
            "max_duration": "Maximum assessment duration in minutes",
            "remote_testing": "Boolean filter for remote testing support",
            "adaptive_support": "Boolean filter for adaptive testing support"
        },
        "example": "/api/recommendations?query=Java developers&test_types=Cognitive,Skill&max_duration=60&remote_testing=true",
        "database": "PostgreSQL",
        "documentation": "/docs"
    }

def run():
    """Run the FastAPI server"""
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=False)

if __name__ == "__main__":
    run()
