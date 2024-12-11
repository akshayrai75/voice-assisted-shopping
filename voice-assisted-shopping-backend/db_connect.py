from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Database URL Configuration
DB_URL = 'mysql+pymysql://root:admin123@localhost:3306/shopper_store'

# Creating the database engine
db_engine = create_engine(DB_URL)

# Creating a configured "Session" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

# Base class for our classes definitions
Base = declarative_base()

# Note: No need for db_connection as session_local handles connections

# Reference: https://www.youtube.com/watch?v=zzOwU41UjTM