import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from core.config import settings
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

class Student(Base):
    __tablename__ = 'students'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50))
    age = Column(Integer)
    major = Column(String(100))

def test_db():
    DATABASE_URL = f"postgresql+psycopg://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    print(f"[Postgres] Connecting to: postgresql+psycopg://{settings.postgres_user}:***@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}")
    
    print("\n--- Step 1: Create Table 'students' ---")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    print("Table 'students' created successfully.")
    
    print("\n--- Step 2: Inserting Data ---")
    s1 = Student(name="Somsak", age=20, major="Computer Engineering")
    s2 = Student(name="Somying", age=21, major="Information Technology")
    s3 = Student(name="Somchai Dee", age=22, major="Computer Science")
    s4 = Student(name="Somsri Raakdee", age=20, major="Data Science")
    s5 = Student(name="Anan Panya", age=23, major="Software Engineering")
    s6 = Student(name="Somsak", age=24, major="Cyber Security")
    
    session.add_all([s1, s2, s3, s4, s5, s6])
    session.commit()
    print("Successfully inserted: Somsak (Major: Computer Engineering)")
    print("Successfully inserted: Somying (Major: Information Technology)")

    print("\n--- Step 3: Updating Data ---")
    student = session.query(Student).filter_by(name="Somsak").first()
    print(f"Original Age: {student.age}, Major: {student.major}")
    student.age = 21
    student.major = "Computer Science"
    session.commit()
    print(f"Updated to Age: {student.age}, Major: {student.major}")
    
    print("\n--- Step 4: Deleting Data ---")
    student_to_delete = session.query(Student).filter_by(name="Somying").first()
    session.delete(student_to_delete)
    session.commit()
    print("Deleted student: Somying")
    
    remaining = [s.name for s in session.query(Student).all()]
    print(f"Students remaining in DB: {remaining}")
    
    print("\n--- Step 5: Deleting Table 'students' ---")
    Base.metadata.drop_all(engine)
    print("Table 'students' deleted (dropped) successfully.")

if __name__ == "__main__":
    test_db()
