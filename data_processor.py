import json
import os
from typing import List, Dict, Any, Optional
import re

def load_assessment_data(file_path: str = "shl_assessments.json") -> List[Dict[str, Any]]:
    """
    Load assessment data from a JSON file.
    
    Args:
        file_path: Path to the JSON file containing assessment data
        
    Returns:
        List of assessment dictionaries or empty list if file not found
    """
    try:
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                return json.load(f)
        return []
    except Exception as e:
        print(f"Error loading assessment data: {str(e)}")
        return []

def save_assessment_data(assessments: List[Dict[str, Any]], file_path: str = "shl_assessments.json") -> bool:
    """
    Save assessment data to a JSON file.
    
    Args:
        assessments: List of assessment dictionaries
        file_path: Path to save the JSON file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with open(file_path, "w") as f:
            json.dump(assessments, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving assessment data: {str(e)}")
        return False

def extract_duration(text: str) -> Optional[int]:
    """
    Extract duration in minutes from a text description.
    
    Args:
        text: Text containing duration information
        
    Returns:
        Duration in minutes or None if not found
    """
    # Look for patterns like "30 minutes", "30 mins", "30min"
    patterns = [
        r'(\d+)\s*(?:minute|min)s?',
        r'(\d+)\s*hour',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            duration = int(match.group(1))
            # Convert hours to minutes if needed
            if 'hour' in pattern:
                duration *= 60
            return duration
    
    return None

def parse_test_type(text: str) -> str:
    """
    Parse the test type from a description.
    
    Args:
        text: Text to analyze for test type indicators
        
    Returns:
        Identified test type or "Unknown"
    """
    text = text.lower()
    
    if any(term in text for term in ['cognitive', 'reasoning', 'intelligence', 'aptitude']):
        return "Cognitive"
    elif any(term in text for term in ['personality', 'behavior', 'behaviour', 'preference']):
        return "Personality"
    elif any(term in text for term in ['skill', 'coding', 'technical', 'programming']):
        return "Skill"
    elif any(term in text for term in ['situation', 'judgment', 'judgement', 'scenario']):
        return "Situational Judgment"
    else:
        return "Unknown"

def enrich_assessment_data(assessments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Enrich assessment data with additional information derived from existing fields.
    
    Args:
        assessments: List of assessment dictionaries
        
    Returns:
        List of enriched assessment dictionaries
    """
    enriched = []
    
    for assessment in assessments:
        # Create a copy of the assessment
        enriched_assessment = assessment.copy()
        
        # Extract duration if not present
        if 'duration' not in enriched_assessment or not enriched_assessment['duration']:
            description = enriched_assessment.get('description', '')
            duration = extract_duration(description)
            if duration:
                enriched_assessment['duration'] = f"{duration} minutes"
            else:
                enriched_assessment['duration'] = "Varies"
        
        # Determine test type if not present
        if 'test_type' not in enriched_assessment or not enriched_assessment['test_type']:
            description = enriched_assessment.get('description', '')
            name = enriched_assessment.get('name', '')
            combined_text = f"{name} {description}"
            enriched_assessment['test_type'] = parse_test_type(combined_text)
        
        # Set default values for missing fields
        if 'remote_testing' not in enriched_assessment or not enriched_assessment['remote_testing']:
            enriched_assessment['remote_testing'] = "Yes"  # Most modern assessments support remote testing
            
        if 'adaptive_support' not in enriched_assessment or not enriched_assessment['adaptive_support']:
            enriched_assessment['adaptive_support'] = "No"  # Default to no adaptive support
        
        enriched.append(enriched_assessment)
    
    return enriched

def filter_assessments_by_time(
    assessments: List[Dict[str, Any]], 
    max_duration: int
) -> List[Dict[str, Any]]:
    """
    Filter assessments by maximum duration.
    
    Args:
        assessments: List of assessment dictionaries
        max_duration: Maximum duration in minutes
        
    Returns:
        List of assessments within time limit
    """
    filtered = []
    
    for assessment in assessments:
        duration_str = assessment.get('duration', '')
        duration_match = re.search(r'(\d+)', duration_str)
        
        if duration_match:
            duration = int(duration_match.group(1))
            if duration <= max_duration:
                filtered.append(assessment)
        else:
            # If duration can't be determined, include it anyway
            filtered.append(assessment)
    
    return filtered

def filter_assessments_by_type(
    assessments: List[Dict[str, Any]], 
    test_types: List[str]
) -> List[Dict[str, Any]]:
    """
    Filter assessments by test type.
    
    Args:
        assessments: List of assessment dictionaries
        test_types: List of test types to include
        
    Returns:
        List of assessments matching specified test types
    """
    if not test_types:
        return assessments
        
    return [
        assessment for assessment in assessments
        if assessment.get('test_type', '') in test_types
    ]
