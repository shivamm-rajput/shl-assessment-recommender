# SHL Assessment Recommendation System

An intelligent system that recommends appropriate SHL assessments based on job descriptions or natural language queries. This application helps hiring managers identify suitable assessment tools for evaluating job candidates, making the hiring process more efficient and effective.

## Features

- **Semantic Search**: Utilizes Google's Gemini API for semantic matching between job descriptions and assessment characteristics
- **Advanced Filtering**: Filter recommendations by test type, maximum duration, remote testing capability, and adaptive testing support
- **Multiple Input Methods**: Process natural language queries, job description text, or job posting URLs
- **Query History**: Track past queries and their recommendations for future reference
- **Robust Data Collection**: Enhanced scraping capabilities with fallback mechanisms for reliable assessment data

## Technology Stack

- **Frontend**: Streamlit for interactive web interface
- **Backend API**: FastAPI for RESTful API endpoints
- **Database**: PostgreSQL for data persistence
- **AI Integration**: Google Gemini API for semantic search and recommendations
- **Web Scraping**: Trafilatura and BeautifulSoup for data collection

## Installation

1. Clone the repository:
```bash
git clone https://github.com/YOUR_USERNAME/shl-assessment-recommender.git
cd shl-assessment-recommender
```

2. Install the required packages:
```bash
pip install -r requirements.txt
```

3. Set up the environment variables:
```bash
# Add your Google API key for Gemini API
export GOOGLE_API_KEY=your_api_key_here

# Database settings (if using your own PostgreSQL instance)
export DATABASE_URL=postgresql://username:password@localhost:5432/shl_db
```

## Usage

1. Start the application:
```bash
python run.py
```

2. Access the web interface at `http://localhost:5000`
3. Access the API at `http://localhost:8000` with API documentation at `http://localhost:8000/docs`

## API Endpoints

- `GET /api/recommendations` - Get assessment recommendations based on query or URL with optional filtering
- `GET /api/queries` - Get recent user queries and their recommendations

### Example API Request

```
GET /api/recommendations?query=Java developers&test_types=Cognitive,Skill&max_duration=60&remote_testing=true
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.