# Schema defined in src/infrastructure/database/models.py

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()

_connection_string = os.environ["DB_CONNECTION_STRING"]
engine = create_engine(_connection_string, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
