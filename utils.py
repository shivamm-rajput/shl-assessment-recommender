import streamlit as st
import pandas as pd
from typing import List, Dict, Any, Optional
import re
import requests
from urllib.parse import urlparse

def validate_url(url: str) -> bool:
    """
    Validate if a string is a proper URL.
    
    Args:
        url: URL string to validate
        
    Returns:
        True if valid URL, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def extract_duration_minutes(duration_str: str) -> Optional[int]:
    """
    Extract minutes from duration string.
    
    Args:
        duration_str: String representation of duration
        
    Returns:
        Duration in minutes or None if parsing fails
    """
    if not duration_str:
        return None
    
    # Handle hour format
    hour_pattern = re.search(r'(\d+)\s*hour', duration_str, re.IGNORECASE)
    if hour_pattern:
        return int(hour_pattern.group(1)) * 60
    
    # Handle minute format
    minute_pattern = re.search(r'(\d+)', duration_str)
    if minute_pattern:
        return int(minute_pattern.group(1))
    
    return None

def display_recommendations(recommendations: List[Dict[str, Any]]) -> None:
    """
    Display recommendations in a Streamlit table with proper formatting.
    
    Args:
        recommendations: List of assessment dictionaries to display
    """
    if not recommendations:
        st.warning("No recommendations found.")
        return
    
    # Convert to pandas DataFrame for display
    df = pd.DataFrame(recommendations)
    
    # Select and rename columns for display
    if 'description' in df.columns:
        df = df.drop(columns=['description'])
    
    # Rename columns for better display
    column_mapping = {
        'name': 'Assessment Name',
        'url': 'Link',
        'remote_testing': 'Remote Testing',
        'adaptive_support': 'Adaptive/IRT Support',
        'duration': 'Duration',
        'test_type': 'Test Type'
    }
    
    df = df.rename(columns=column_mapping)
    
    # Sort by duration if available
    if 'Duration' in df.columns:
        df['Duration_minutes'] = df['Duration'].apply(extract_duration_minutes)
        df = df.sort_values('Duration_minutes')
        df = df.drop(columns=['Duration_minutes'])
    
    # Create clickable links
    def make_clickable(val):
        return f'<a href="{val}" target="_blank">{val}</a>'
    
    if 'Link' in df.columns:
        df['Link'] = df['Link'].apply(make_clickable)
    
    # Create Assessment Name with link
    if 'Assessment Name' in df.columns and 'Link' in df.columns:
        df['Assessment Name'] = df.apply(
            lambda row: f'<a href="{row["Link"]}" target="_blank">{row["Assessment Name"]}</a>', 
            axis=1
        )
        df = df.drop(columns=['Link'])
    
    # Display the table
    st.markdown(df.to_html(escape=False, index=False), unsafe_allow_html=True)
    
    # Show download option
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        "Download Recommendations as CSV",
        csv,
        "shl_recommendations.csv",
        "text/csv",
        key='download-csv'
    )

def format_api_url(base_url: str, endpoint: str, params: Dict[str, Any]) -> str:
    """
    Format an API URL with parameters.
    
    Args:
        base_url: Base URL
        endpoint: API endpoint
        params: Dictionary of query parameters
        
    Returns:
        Formatted URL string
    """
    url = f"{base_url}{endpoint}?"
    param_strings = []
    
    for key, value in params.items():
        if value:
            param_strings.append(f"{key}={value}")
    
    return url + "&".join(param_strings)

def test_api_connection(url: str) -> Dict[str, Any]:
    """
    Test connection to API endpoint.
    
    Args:
        url: API URL to test
        
    Returns:
        Response data or error information
    """
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return {"success": True, "status_code": response.status_code, "data": response.json()}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e)}
