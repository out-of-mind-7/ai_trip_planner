import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import URL,create_engine,text
from sqlalchemy.orm import Session

env_path=Path(__file__).parent / ".env"
load_dotenv(env_path)

database_url = URL.create(
    "postgresql+psycopg",
    username=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD")
    ,
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT","5432")),
    database=os.getenv("DB_NAME"),
)
engine=create_engine(database_url)

def get_session():
    with Session(engine) as session:
        yield session

if __name__=="__main__":
    with engine.connect() as connection:
        result=connection.execute(text("SELECT current_database()"))
        print(result.scalar())
