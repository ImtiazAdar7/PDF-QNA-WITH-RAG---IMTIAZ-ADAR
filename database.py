from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv
import urllib.parse

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    # Local development fallback
    DB_USER = "pdf_qa_db_womu_user"
    DB_PASSWORD = "XbXVfUHUEyDiCQ7snzvwjYfQCbENWY8s"
    DB_HOST = "dpg-d8g4r1dckfvc73e3ecn0-a.oregon-postgres.render.com"
    DB_PORT = "5432"
    DB_NAME = "pdf_qa_db_womu"
    
    encoded_password = urllib.parse.quote(DB_PASSWORD, safe='')
    DATABASE_URL = f"postgresql://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    print("⚠️ Using hardcoded database URL (local development)")
else:
    print("✅ Using DATABASE_URL from environment variable")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=5,
    max_overflow=10,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class QARecord(Base):
    __tablename__ = "qa_history"
    
    id = Column(Integer, primary_key=True, index=True)
    pdf_filename = Column(String(255), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    sources = Column(JSON, nullable=True)
    response_time_ms = Column(Float, nullable=True)
    user_rating = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class PDFDocument(Base):
    __tablename__ = "pdf_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), unique=True, nullable=False)
    file_path = Column(String(512), nullable=False)
    chunk_count = Column(Integer, default=0)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

def init_db():
    """Initialize database - creates tables if they don't exist"""
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ PostgreSQL database connected successfully!")
    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {e}")
        raise