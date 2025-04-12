import streamlit as st
import pandas as pd
import os
import json
from scraper import fetch_shl_catalog_data, process_shl_catalog
from recommendation_engine import get_recommendations
from utils import display_recommendations, validate_url
import time
import requests
from database import get_assessments, get_recent_queries, init_db

# Page configuration
st.set_page_config(
    page_title="SHL Assessment Recommendation System",
    page_icon="📊",
    layout="wide"
)

# Cache the data fetching to avoid repeated scraping
@st.cache_data(ttl=3600)
def load_assessment_data():
    try:
        # Try to load from cache file first
        if os.path.exists("shl_assessments.json"):
            with open("shl_assessments.json", "r") as f:
                return json.load(f)
        
        # If no cache, scrape the data
        raw_data = fetch_shl_catalog_data("https://www.shl.com/solutions/products/product-catalog/")
        if not raw_data:
            st.error("Failed to fetch SHL catalog data. Please try again later.")
            return None
            
        assessments = process_shl_catalog(raw_data)
        
        # Cache the processed data
        with open("shl_assessments.json", "w") as f:
            json.dump(assessments, f)
            
        return assessments
    except Exception as e:
        st.error(f"Error loading assessment data: {str(e)}")
        return None

# Main application
def main():
    st.title("SHL Assessment Recommendation System")
    st.subheader("Find the right assessments for your hiring needs")
    
    # Initialize database with assessment data
    try:
        init_db()
    except Exception as e:
        st.error(f"Database initialization error: {str(e)}")
    
    # Load assessment data
    with st.spinner("Loading SHL assessment catalog..."):
        # Try to get assessments from database first
        db_assessments = get_assessments()
        
        if db_assessments:
            assessments = db_assessments
        else:
            # Fall back to JSON file if database is empty
            assessments = load_assessment_data()
    
    if not assessments:
        st.error("Unable to load assessment data. Please refresh the page or try again later.")
        return
    
    # Create tabs for the main interface
    tab1, tab2 = st.tabs(["Find Assessments", "Recent Queries"])
    
    with tab1:
        # Input section
        st.markdown("### Enter Job Description or Query")
        input_type = st.radio(
            "Input Type",
            ["Natural Language Query", "Job Description Text", "Job Description URL"]
        )
        
        user_input = ""
        if input_type == "Natural Language Query" or input_type == "Job Description Text":
            user_input = st.text_area(
                "Enter your query or job description:",
                height=150,
                placeholder="Example: I am hiring for Java developers who can also collaborate effectively with my business teams. Looking for an assessment(s) that can be completed in 40 minutes."
            )
        else:  # URL input
            user_input = st.text_input(
                "Enter job description URL:",
                placeholder="https://example.com/job-description"
            )
            
            if user_input and not validate_url(user_input):
                st.error("Please enter a valid URL")
                
        # Advanced filtering options
        with st.expander("Advanced Filtering Options", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                # Test type filter
                test_types = ['Cognitive', 'Personality', 'Skill', 'Situational Judgment']
                selected_test_types = st.multiselect(
                    "Test Types",
                    options=test_types,
                    default=[]
                )
                
                # Remote testing filter
                remote_testing = st.radio(
                    "Remote Testing",
                    ["Any", "Required", "Not Required"],
                    index=0
                )
            
            with col2:
                # Max duration filter
                max_duration = st.slider(
                    "Maximum Duration (minutes)",
                    min_value=10,
                    max_value=120,
                    value=60,
                    step=5
                )
                
                # Adaptive support filter
                adaptive_support = st.radio(
                    "Adaptive Testing",
                    ["Any", "Required", "Not Required"],
                    index=0
                )
        
        # Sample queries for demonstration
        with st.expander("Sample queries"):
            st.markdown("""
            - I am hiring for Java developers who can also collaborate effectively with my business teams. Looking for an assessment(s) that can be completed in 40 minutes.
            - Looking to hire mid-level professionals who are proficient in Python, SQL and Java Script. Need an assessment package that can test all skills with max duration of 60 minutes.
            - Here is a JD text, can you recommend some assessment that can help me screen applications. Time limit is less than 30 minutes.
            - I am hiring for an analyst and wants applications to screen using Cognitive and personality tests, what options are available within 45 mins.
            """)
        
        # API Information
        with st.expander("API Usage Information"):
            st.markdown("""
            ### API Endpoint
            GET `/api/recommendations`
            
            ### Parameters
            - `query`: (string) The job description or natural language query
            - `url`: (string, optional) URL to a job description
            
            ### Example Request
            ```
            GET /api/recommendations?query=Java developers with good communication skills
            ```
            
            ### Example Response
            ```json
            {
                "recommendations": [
                    {
                        "name": "Development Assessment",
                        "url": "https://www.shl.com/solutions/products/development-assessment/",
                        "remote_testing": "Yes",
                        "adaptive_support": "Yes",
                        "duration": "40 minutes",
                        "test_type": "Cognitive"
                    },
                    ...
                ]
            }
            ```
            """)
        
        # Recommendation process
        col1, col2 = st.columns([1, 4])
        with col1:
            search_button = st.button("Get Recommendations", type="primary", use_container_width=True)
        
        if search_button and user_input:
            with st.spinner("Analyzing your request and finding relevant assessments..."):
                # Track time for evaluation purposes
                start_time = time.time()
                
                # Process input and get recommendations
                recommendations = get_recommendations(
                    user_input, 
                    assessments, 
                    is_url=(input_type == "Job Description URL"),
                    max_results=20,  # Increase max results to account for filtering
                    save_to_db=True  # Save to database
                )
                
                # Apply filters to recommendations if any are selected
                filtered_recommendations = recommendations.copy()
                filter_applied = False
                
                # Test type filter
                if selected_test_types:
                    filtered_recommendations = [rec for rec in filtered_recommendations 
                                               if rec.get('test_type') in selected_test_types]
                    filter_applied = True
                
                # Remote testing filter
                if remote_testing != "Any":
                    required_value = "Yes" if remote_testing == "Required" else "No"
                    filtered_recommendations = [rec for rec in filtered_recommendations 
                                               if rec.get('remote_testing') == required_value]
                    filter_applied = True
                
                # Adaptive support filter
                if adaptive_support != "Any":
                    required_value = "Yes" if adaptive_support == "Required" else "No"
                    filtered_recommendations = [rec for rec in filtered_recommendations 
                                               if rec.get('adaptive_support') == required_value]
                    filter_applied = True
                
                # Max duration filter
                if max_duration < 120:  # Only apply if not at max value
                    from data_processor import extract_duration
                    
                    # Filter by duration
                    temp_filtered = []
                    for rec in filtered_recommendations:
                        duration_minutes = extract_duration(rec.get('duration', 'Unknown'))
                        # Include if duration is unknown or within the limit
                        if duration_minutes is None or duration_minutes <= max_duration:
                            temp_filtered.append(rec)
                    filtered_recommendations = temp_filtered
                    filter_applied = True
                
                process_time = time.time() - start_time
                
                # Display recommendations
                if filtered_recommendations:
                    # Show filter information if filters were applied
                    if filter_applied:
                        original_count = len(recommendations)
                        filtered_count = len(filtered_recommendations)
                        st.info(f"Filtered from {original_count} to {filtered_count} assessments based on your criteria")
                    
                    st.success(f"Found {len(filtered_recommendations)} relevant assessments in {process_time:.2f} seconds")
                    display_recommendations(filtered_recommendations)
                    
                    # Show filter summary
                    if filter_applied:
                        filter_summary = []
                        if selected_test_types:
                            filter_summary.append(f"Test Types: {', '.join(selected_test_types)}")
                        if remote_testing != "Any":
                            filter_summary.append(f"Remote Testing: {remote_testing}")
                        if adaptive_support != "Any":
                            filter_summary.append(f"Adaptive Testing: {adaptive_support}")
                        if max_duration < 120:
                            filter_summary.append(f"Max Duration: {max_duration} minutes")
                        
                        with st.expander("Applied Filters"):
                            for item in filter_summary:
                                st.markdown(f"- {item}")
                    
                    # Show API equivalent
                    with st.expander("See API equivalent request"):
                        api_url = f"/api/recommendations?query={user_input}"
                        if input_type == "Job Description URL":
                            api_url = f"/api/recommendations?url={user_input}"
                        
                        # Add filter parameters
                        if selected_test_types:
                            api_url += f"&test_types={','.join(selected_test_types)}"
                        if max_duration < 120:
                            api_url += f"&max_duration={max_duration}"
                        if remote_testing != "Any":
                            api_url += f"&remote_testing={'true' if remote_testing == 'Required' else 'false'}"
                        if adaptive_support != "Any":
                            api_url += f"&adaptive_support={'true' if adaptive_support == 'Required' else 'false'}"
                            
                        st.code(f"GET {api_url}")
                else:
                    if filter_applied and recommendations:
                        st.warning("No assessments match your filter criteria. Try adjusting your filters.")
                    else:
                        st.warning("No matching assessments found. Try adjusting your query.")
    
    with tab2:
        st.markdown("### Recent Search Queries")
        
        # Get recent queries from database
        recent_queries = get_recent_queries(limit=10)
        
        if recent_queries:
            for i, query in enumerate(recent_queries):
                with st.expander(f"Query {i+1}: {query['query_text'][:100]}..." if len(query['query_text']) > 100 else f"Query {i+1}: {query['query_text']}"):
                    st.markdown(f"**Query Type:** {'URL' if query['is_url'] else 'Text'}")
                    st.markdown(f"**Date:** {query['created_at']}")
                    
                    # Check if recommendations are included in the query
                    if 'recommendations' in query and query['recommendations']:
                        st.markdown("**Recommendations:**")
                        
                        # Create a DataFrame for recommendations
                        recommendation_data = []
                        for rec in query['recommendations']:
                            # Get assessment details
                            from database import get_assessment_by_id
                            assessment = get_assessment_by_id(rec['assessment_id'])
                            if assessment:
                                assessment['rank'] = rec['rank']
                                assessment['relevance_score'] = rec['relevance_score']
                                recommendation_data.append(assessment)
                        
                        if recommendation_data:
                            # Convert to DataFrame
                            df = pd.DataFrame(recommendation_data)
                            
                            # Display as table
                            st.table(df[['name', 'test_type', 'duration', 'rank', 'relevance_score']])
        else:
            st.info("No recent queries found. Try searching for some assessments!")
    
    # Information section at the bottom
    st.markdown("---")
    st.markdown("### About This Tool")
    st.markdown("""
    This tool helps hiring managers find the right SHL assessments for their recruitment needs. 
    Enter a natural language query or job description, and the system will recommend the most relevant assessments 
    from SHL's product catalog based on semantic matching.
    
    Data is sourced from the [SHL Product Catalog](https://www.shl.com/solutions/products/product-catalog/).
    """)

if __name__ == "__main__":
    main()
