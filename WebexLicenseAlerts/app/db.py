from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base

from app.config import DATABASE_URL

engine = create_engine(DATABASE_URL, future=True)
Base = declarative_base()

