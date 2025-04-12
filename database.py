import os
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import json

# Get database URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL")

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Create declarative base model
Base = declarative_base()

class Assessment(Base):
    """Model for SHL assessment data"""
    __tablename__ = "assessments"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    url = Column(String(512))
    description = Column(Text)
    remote_testing = Column(String(50))
    adaptive_support = Column(String(50))
    duration = Column(String(50))
    test_type = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "description": self.description,
            "remote_testing": self.remote_testing,
            "adaptive_support": self.adaptive_support,
            "duration": self.duration,
            "test_type": self.test_type
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create model from dictionary"""
        return cls(
            name=data.get("name", ""),
            url=data.get("url", ""),
            description=data.get("description", ""),
            remote_testing=data.get("remote_testing", ""),
            adaptive_support=data.get("adaptive_support", ""),
            duration=data.get("duration", ""),
            test_type=data.get("test_type", "")
        )

class UserQuery(Base):
    """Model for storing user queries and results"""
    __tablename__ = "user_queries"
    
    id = Column(Integer, primary_key=True)
    query_text = Column(Text, nullable=False)
    query_type = Column(String(50))  # 'text' or 'url'
    is_url = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Store recommendations as relationship
    recommendations = relationship("QueryRecommendation", back_populates="query")
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "query_text": self.query_text,
            "query_type": self.query_type,
            "is_url": self.is_url,
            "created_at": self.created_at.isoformat(),
            "recommendations": [rec.to_dict() for rec in self.recommendations]
        }

class QueryRecommendation(Base):
    """Model for storing recommendations for a query"""
    __tablename__ = "query_recommendations"
    
    id = Column(Integer, primary_key=True)
    query_id = Column(Integer, ForeignKey("user_queries.id"))
    assessment_id = Column(Integer, ForeignKey("assessments.id"))
    relevance_score = Column(Float)
    rank = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Define relationships
    query = relationship("UserQuery", back_populates="recommendations")
    assessment = relationship("Assessment")
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "query_id": self.query_id,
            "assessment_id": self.assessment_id,
            "relevance_score": self.relevance_score,
            "rank": self.rank
        }

# Create all tables
Base.metadata.create_all(engine)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database with assessment data"""
    db = SessionLocal()
    
    # Check if we already have assessment data
    assessment_count = db.query(Assessment).count()
    if assessment_count > 0:
        db.close()
        return
    
    # Load assessment data from JSON file
    try:
        with open("shl_assessments.json", "r") as f:
            assessments_data = json.load(f)
            
        # Add assessments to database
        for data in assessments_data:
            assessment = Assessment.from_dict(data)
            db.add(assessment)
        
        db.commit()
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        db.rollback()
    finally:
        db.close()

def save_query_and_recommendations(query_text, is_url, recommendations):
    """
    Save a user query and its recommendations to the database
    
    Args:
        query_text: The user's query text
        is_url: Whether the query is a URL
        recommendations: List of assessment dictionaries with recommendations
        
    Returns:
        The saved UserQuery object
    """
    db = SessionLocal()
    try:
        # Create user query
        query = UserQuery(
            query_text=query_text,
            query_type="url" if is_url else "text",
            is_url=is_url
        )
        db.add(query)
        db.flush()  # Get ID for the query
        
        # Add recommendations
        for i, rec in enumerate(recommendations):
            # First check if this assessment already exists in the database
            assessment = db.query(Assessment).filter(Assessment.name == rec["name"]).first()
            
            # If not, create it
            if not assessment:
                assessment = Assessment.from_dict(rec)
                db.add(assessment)
                db.flush()
            
            # Create recommendation
            recommendation = QueryRecommendation(
                query_id=query.id,
                assessment_id=assessment.id,
                relevance_score=rec.get("score", 0.0),
                rank=i + 1
            )
            db.add(recommendation)
        
        db.commit()
        return query
    except Exception as e:
        print(f"Error saving query and recommendations: {str(e)}")
        db.rollback()
        return None
    finally:
        db.close()

def get_assessment_by_id(assessment_id):
    """Get assessment by ID"""
    db = SessionLocal()
    try:
        assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        return assessment.to_dict() if assessment else None
    finally:
        db.close()

def get_assessments():
    """Get all assessments"""
    db = SessionLocal()
    try:
        assessments = db.query(Assessment).all()
        return [assessment.to_dict() for assessment in assessments]
    finally:
        db.close()

def get_recent_queries(limit=10):
    """Get recent user queries"""
    db = SessionLocal()
    try:
        queries = db.query(UserQuery).order_by(UserQuery.created_at.desc()).limit(limit).all()
        return [query.to_dict() for query in queries]
    finally:
        db.close()

# Initialize database with assessment data when module is imported
init_db()