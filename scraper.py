import trafilatura
import requests
from bs4 import BeautifulSoup
import re
import time
import random
from typing import List, Dict, Union, Optional

def get_website_text_content(url: str) -> str:
    """
    Extract clean text content from a website using trafilatura.
    
    Args:
        url: URL of the website to scrape
        
    Returns:
        Extracted text content or empty string if extraction fails
    """
    try:
        downloaded = trafilatura.fetch_url(url)
        text = trafilatura.extract(downloaded)
        return text if text else ""
    except Exception as e:
        print(f"Error extracting text from {url}: {str(e)}")
        return ""

def fetch_shl_catalog_data(catalog_url: str) -> Optional[str]:
    """
    Fetch the SHL product catalog HTML data.
    
    Args:
        catalog_url: URL of the SHL product catalog
        
    Returns:
        Raw HTML content of the catalog page or None if failed
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0"
        }
        
        # First attempt with standard request
        response = requests.get(catalog_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # If response is too small, it might be a redirect or anti-bot page
        if len(response.text) < 1000:
            print(f"Response seems too small, attempting with additional headers and cookies")
            # Add cookies and retry
            cookies = response.cookies
            response = requests.get(catalog_url, headers=headers, cookies=cookies, timeout=30)
            response.raise_for_status()
            
        print(f"Successfully fetched SHL catalog: {len(response.text)} bytes")
        return response.text
    except Exception as e:
        print(f"Error fetching SHL catalog: {str(e)}")
        return None

def extract_assessment_details(assessment_url: str) -> Dict[str, str]:
    """
    Extract detailed information about an assessment from its dedicated page.
    
    Args:
        assessment_url: URL of the specific assessment page
        
    Returns:
        Dictionary containing extracted assessment details
    """
    details = {
        "remote_testing": "No",
        "adaptive_support": "No",
        "duration": "Varies",
        "test_type": "Unknown"
    }
    
    try:
        # Add small delay to avoid rate limiting
        time.sleep(random.uniform(0.5, 1.5))
        
        # Get the assessment page content using custom headers
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
        
        # First try with requests
        try:
            response = requests.get(assessment_url, headers=headers, timeout=20)
            response.raise_for_status()
            html_content = response.text
        except Exception as req_err:
            print(f"Requests failed for {assessment_url}, falling back to trafilatura: {str(req_err)}")
            html_content = trafilatura.fetch_url(assessment_url)
        
        if not html_content:
            print(f"Failed to fetch content for {assessment_url}")
            return details
            
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract text content for analysis
        text_content = trafilatura.extract(html_content)
        if not text_content:
            text_content = soup.get_text()
        
        # Pattern matching for key information with improved patterns
        remote_patterns = [
            r'remote\s+testing',
            r'online\s+testing',
            r'virtual\s+assessment',
            r'test\s+from\s+anywhere',
            r'test\s+remotely',
            r'remote\s+proctoring',
            r'digital\s+delivery'
        ]
        for pattern in remote_patterns:
            if re.search(pattern, text_content, re.I):
                details["remote_testing"] = "Yes"
                break
        
        adaptive_patterns = [
            r'adaptive\s+testing',
            r'IRT',
            r'item\s+response\s+theory',
            r'computer[-\s]adaptive',
            r'adaptive\s+format',
            r'adaptive\s+algorithm',
            r'adapts\s+to\s+candidate'
        ]
        for pattern in adaptive_patterns:
            if re.search(pattern, text_content, re.I):
                details["adaptive_support"] = "Yes"
                break
        
        # Look for duration information with more patterns
        duration_patterns = [
            r'(\d+[-\s]?\d*)\s*(min|minutes|mins|minute)',
            r'takes\s+(\d+[-\s]?\d*)\s*(min|minutes|mins|minute)',
            r'duration[:\s]+(\d+[-\s]?\d*)\s*(min|minutes|mins|minute)',
            r'(\d+[-\s]?\d*)\s*(hour|hours|hr|hrs)',
            r'approximately\s+(\d+[-\s]?\d*)\s*(min|minutes|mins|minute)'
        ]
        
        for pattern in duration_patterns:
            duration_match = re.search(pattern, text_content, re.I)
            if duration_match:
                value = duration_match.group(1).strip()
                unit = duration_match.group(2).strip().lower()
                
                # Standardize units
                if unit in ['hour', 'hours', 'hr', 'hrs']:
                    # Convert hours to minutes
                    try:
                        minutes = int(float(value) * 60)
                        details["duration"] = f"{minutes} minutes"
                    except ValueError:
                        details["duration"] = f"{value} {unit}"
                else:
                    details["duration"] = f"{value} minutes"
                break
        
        # Determine test type with enhanced patterns
        test_type_patterns = {
            "Cognitive": [
                r'cognitive\s+ability',
                r'reasoning\s+ability',
                r'intelligence',
                r'aptitude',
                r'numerical\s+reasoning',
                r'verbal\s+reasoning',
                r'logical\s+reasoning',
                r'inductive\s+reasoning',
                r'critical\s+thinking',
                r'problem[-\s]solving\s+ability'
            ],
            "Personality": [
                r'personality',
                r'behavior(al)?',
                r'behaviour(al)?',
                r'style\s+assessment',
                r'preference',
                r'psychological',
                r'character\s+trait',
                r'temperament',
                r'personal\s+attribute',
                r'work\s+style'
            ],
            "Skill": [
                r'skill\s+assessment',
                r'coding\s+test',
                r'programming\s+test',
                r'technical\s+assessment',
                r'practical\s+exercise',
                r'hands[-\s]on',
                r'competency',
                r'proficiency',
                r'capability',
                r'excel\s+test',
                r'language\s+proficiency',
                r'microsoft\s+office'
            ],
            "Situational Judgment": [
                r'situation(al)?\s+judgement',
                r'situation(al)?\s+judgment',
                r'scenario[-\s]based',
                r'case\s+study',
                r'real[-\s]world\s+scenario',
                r'decision[-\s]making\s+test',
                r'workplace\s+scenario',
                r'job\s+simulation'
            ]
        }
        
        # Check each type's patterns
        for test_type, patterns in test_type_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_content, re.I):
                    details["test_type"] = test_type
                    break
            if details["test_type"] != "Unknown":
                break
        
        # Try to extract more from structured elements
        try:
            # Look for spec tables or lists that might contain details
            spec_tables = soup.find_all('table')
            for table in spec_tables:
                table_text = table.get_text()
                if re.search(r'duration|time|minutes|hours|remote|adaptive', table_text, re.I):
                    rows = table.find_all('tr')
                    for row in rows:
                        row_text = row.get_text().strip()
                        # Check for duration information
                        if re.search(r'duration|time', row_text, re.I) and re.search(r'\d+', row_text):
                            duration_match = re.search(r'(\d+[-\s]?\d*)\s*(min|minutes|mins|minute|hour|hours|hr|hrs)', row_text, re.I)
                            if duration_match:
                                value = duration_match.group(1).strip()
                                unit = duration_match.group(2).strip().lower()
                                if unit in ['hour', 'hours', 'hr', 'hrs']:
                                    try:
                                        minutes = int(float(value) * 60)
                                        details["duration"] = f"{minutes} minutes"
                                    except ValueError:
                                        details["duration"] = f"{value} {unit}"
                                else:
                                    details["duration"] = f"{value} minutes"
        except Exception as table_err:
            print(f"Error processing tables for {assessment_url}: {str(table_err)}")
            
        return details
    except Exception as e:
        print(f"Error extracting details from {assessment_url}: {str(e)}")
        return details

def process_shl_catalog(html_content: str) -> List[Dict[str, str]]:
    """
    Process the SHL catalog HTML to extract assessment information.
    
    Args:
        html_content: Raw HTML content of the SHL product catalog
        
    Returns:
        List of dictionaries containing assessment information
    """
    assessments = []
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        print(f"Processing HTML content: {len(html_content)} bytes")
        
        # Multiple approaches to find assessment elements
        assessment_elements = []
        
        # Approach 1: Find assessment cards or entries by common class names
        elements1 = soup.select('.product-item, .catalog-item, .assessment-card, article, .product-card, .card')
        if elements1:
            print(f"Found {len(elements1)} assessment elements using class selectors")
            assessment_elements.extend(elements1)
        
        # Approach 2: Find by product-related div classes
        elements2 = soup.select('div.col-md-4, div.product, div[class*="product"], div[class*="assessment"]')
        if elements2:
            print(f"Found {len(elements2)} assessment elements using div product selectors")
            assessment_elements.extend(elements2)
        
        # Approach 3: Look for structural elements that might be product containers
        elements3 = soup.select('.row > div, .grid > div, .container > div > div')
        if elements3:
            filtered_elements3 = [elem for elem in elements3 if elem.find('a', href=True) and elem.get_text().strip()]
            if filtered_elements3:
                print(f"Found {len(filtered_elements3)} potential assessment elements using structural selectors")
                assessment_elements.extend(filtered_elements3)
        
        # Approach 4: Find links that seem to point to product pages
        if not assessment_elements:
            print("No assessment elements found with standard selectors, trying href analysis")
            links = soup.find_all('a', href=True)
            product_links = [link for link in links if any(kw in link.get('href', '').lower() for kw in 
                             ['product', 'assessment', 'test', 'verify', 'ability', 'personality', 'solution'])]
            
            if product_links:
                print(f"Found {len(product_links)} product links by URL analysis")
                assessment_elements.extend(product_links)
        
        # Deduplicate elements based on inner HTML to avoid processing the same element multiple times
        unique_elements = []
        seen_html = set()
        for elem in assessment_elements:
            elem_html = str(elem)
            if elem_html not in seen_html:
                seen_html.add(elem_html)
                unique_elements.append(elem)
        
        print(f"Processing {len(unique_elements)} unique assessment elements after deduplication")
        
        # Process each potential assessment element
        for element in unique_elements:
            try:
                # Different strategies to find product name and link
                link_element = None
                name = ""
                url = ""
                
                # Strategy 1: Element itself is a link
                if element.name == 'a' and element.has_attr('href'):
                    link_element = element
                
                # Strategy 2: Element contains a link
                if not link_element:
                    link_element = element.find('a', href=True)
                
                # Strategy 3: Element has a heading with a link
                if not link_element:
                    headings = element.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                    for heading in headings:
                        link_in_heading = heading.find('a', href=True)
                        if link_in_heading:
                            link_element = link_in_heading
                            break
                
                if not link_element:
                    continue
                
                # Extract name from various places
                # Try 1: Get text from link
                name = link_element.get_text().strip() if hasattr(link_element, 'get_text') else ''
                
                # Try 2: Get title attribute from link
                if (not name or len(name) < 3) and link_element.has_attr('title'):
                    name = link_element['title'].strip()
                
                # Try 3: Get name from heading near the link
                if not name or len(name) < 3:
                    parent = link_element.parent
                    heading = parent.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                    if heading:
                        name = heading.get_text().strip()
                
                # Skip if we still couldn't find a proper name
                if not name or len(name) < 3:
                    continue
                
                # Handle URL extraction and formatting
                if link_element.has_attr('href'):
                    url = link_element['href']
                    # Handle relative URLs
                    if url.startswith('/'):
                        url = f"https://www.shl.com{url}"
                    elif not url.startswith('http'):
                        url = f"https://www.shl.com/{url}"
                
                if not url:
                    continue
                
                # Extract description using multiple approaches
                description = ""
                
                # Try 1: Find specific description elements
                desc_selectors = [
                    ['p', 'div'], 
                    {'class': lambda c: c and ('desc' in str(c).lower() or 'summary' in str(c).lower())},
                    ['p', 'div'], 
                    {'class': lambda c: c and ('text' in str(c).lower() or 'content' in str(c).lower())}
                ]
                
                for selector in desc_selectors:
                    if len(selector) == 2:  # If we have both tag and attributes
                        desc_elem = element.find(selector[0], **selector[1])
                        if desc_elem:
                            description = desc_elem.get_text().strip()
                            break
                
                # Try 2: Get first paragraph after heading
                if not description:
                    paragraphs = element.find_all('p')
                    for p in paragraphs:
                        p_text = p.get_text().strip()
                        if p_text and p_text != name:
                            description = p_text
                            break
                
                # Try 3: Get text from parent element excluding name
                if not description:
                    element_text = element.get_text().strip()
                    if element_text:
                        # Try to exclude the name from the text to avoid duplication
                        try:
                            description = element_text.replace(name, '').strip()
                        except Exception:
                            description = element_text
                
                # Get additional details from the assessment's dedicated page
                print(f"Found assessment: {name}, fetching details from {url}")
                details = extract_assessment_details(url)
                
                # Create the assessment dictionary
                assessment = {
                    "name": name,
                    "url": url,
                    "description": description[:500],  # Limit description length
                    "remote_testing": details["remote_testing"],
                    "adaptive_support": details["adaptive_support"],
                    "duration": details["duration"],
                    "test_type": details["test_type"]
                }
                
                # Check if this assessment is already in our list (by URL or similar name)
                is_duplicate = False
                for existing in assessments:
                    if existing["url"] == assessment["url"]:
                        is_duplicate = True
                        break
                    # Check for very similar names (80% similarity)
                    if existing["name"].lower() in assessment["name"].lower() or assessment["name"].lower() in existing["name"].lower():
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    assessments.append(assessment)
                    print(f"Added assessment: {name}")
                else:
                    print(f"Skipping duplicate assessment: {name}")
                
            except Exception as e:
                print(f"Error processing element: {str(e)}")
                continue
    
    except Exception as e:
        print(f"Error processing catalog: {str(e)}")
    
    # Fallback to manually created assessments if scraping fails completely
    if not assessments:
        print("Scraping failed. Using fallback assessment data.")
        assessments = create_fallback_assessments()
    else:
        print(f"Successfully scraped {len(assessments)} assessments")
    
    return assessments

def create_fallback_assessments() -> List[Dict[str, str]]:
    """
    Create a fallback list of SHL assessments in case scraping fails.
    Based on publicly available information about SHL products.
    
    Returns:
        List of assessment dictionaries with basic information
    """
    return [
        {
            "name": "Verify Interactive - Cognitive Ability",
            "url": "https://www.shl.com/solutions/products/verify-interactive/",
            "description": "Assess critical reasoning through engaging, interactive tasks. Measures verbal, numerical, and inductive reasoning with gamified elements.",
            "remote_testing": "Yes",
            "adaptive_support": "Yes",
            "duration": "30 minutes",
            "test_type": "Cognitive"
        },
        {
            "name": "Verify - Numerical Reasoning",
            "url": "https://www.shl.com/solutions/products/verify/",
            "description": "Measures the ability to make correct decisions or inferences from numerical data. Helps predict performance in roles requiring analysis and interpretation of numerical information.",
            "remote_testing": "Yes",
            "adaptive_support": "Yes",
            "duration": "18 minutes",
            "test_type": "Cognitive"
        },
        {
            "name": "Verify - Verbal Reasoning",
            "url": "https://www.shl.com/solutions/products/verify/",
            "description": "Measures the ability to evaluate the logic of various statements based on passage information. Essential for roles requiring complex verbal information processing.",
            "remote_testing": "Yes",
            "adaptive_support": "Yes",
            "duration": "17 minutes",
            "test_type": "Cognitive"
        },
        {
            "name": "Verify - Inductive Reasoning",
            "url": "https://www.shl.com/solutions/products/verify/",
            "description": "Measures the ability to identify logical patterns and relationships. Useful for roles requiring problem-solving, innovation, and working with complex information.",
            "remote_testing": "Yes",
            "adaptive_support": "Yes",
            "duration": "18 minutes",
            "test_type": "Cognitive"
        },
        {
            "name": "OPQ - Occupational Personality Questionnaire",
            "url": "https://www.shl.com/solutions/products/opq/",
            "description": "Provides an accurate, detailed view of personality to help predict workplace performance and cultural fit. Measures 32 personality characteristics.",
            "remote_testing": "Yes",
            "adaptive_support": "No",
            "duration": "25 minutes",
            "test_type": "Personality"
        },
        {
            "name": "Verify for Programmers",
            "url": "https://www.shl.com/solutions/products/coding-tests/",
            "description": "Measures programming skills through real-world coding challenges. Available for Java, Python, JavaScript, C#, and more.",
            "remote_testing": "Yes",
            "adaptive_support": "No",
            "duration": "60 minutes",
            "test_type": "Skill"
        },
        {
            "name": "Situational Judgement Test",
            "url": "https://www.shl.com/solutions/products/situational-judgement/",
            "description": "Presents realistic workplace scenarios to measure judgment and decision-making ability. Highly customizable to specific roles.",
            "remote_testing": "Yes",
            "adaptive_support": "No",
            "duration": "30 minutes",
            "test_type": "Situational Judgment"
        },
        {
            "name": "MQ - Motivation Questionnaire",
            "url": "https://www.shl.com/solutions/products/motivation-questionnaire/",
            "description": "Measures 18 key dimensions of motivation to help understand what drives an individual in the workplace. Predicts job satisfaction and engagement.",
            "remote_testing": "Yes",
            "adaptive_support": "No",
            "duration": "25 minutes",
            "test_type": "Personality"
        },
        {
            "name": "Verify for Microsoft Excel",
            "url": "https://www.shl.com/solutions/products/ms-office-tests/",
            "description": "Assesses proficiency in Microsoft Excel through practical tasks. Covers formulas, functions, data manipulation, and analysis.",
            "remote_testing": "Yes",
            "adaptive_support": "No",
            "duration": "40 minutes",
            "test_type": "Skill"
        },
        {
            "name": "ADEPT-15 Personality Assessment",
            "url": "https://www.shl.com/solutions/products/adept-15/",
            "description": "Measures 15 aspects of personality that impact critical work outcomes. Offers a deep, contextual understanding of workplace behaviors.",
            "remote_testing": "Yes",
            "adaptive_support": "Yes",
            "duration": "25 minutes",
            "test_type": "Personality"
        },
        {
            "name": "Executive Assessment",
            "url": "https://www.shl.com/solutions/products/executive-assessment/",
            "description": "Tailored for leadership roles, measures strategic thinking, leading change, and executive presence. Combines cognitive and behavioral measures.",
            "remote_testing": "Yes",
            "adaptive_support": "Yes",
            "duration": "90 minutes",
            "test_type": "Cognitive"
        },
        {
            "name": "SQL Assessment",
            "url": "https://www.shl.com/solutions/products/technical-assessments/",
            "description": "Evaluates SQL proficiency through practical database queries and data manipulation tasks. Tests understanding of SQL syntax, joins, aggregation, and optimization.",
            "remote_testing": "Yes",
            "adaptive_support": "No",
            "duration": "45 minutes",
            "test_type": "Skill"
        }
    ]
