# Import required libraries
from fastapi import FastAPI, HTTPException  # FastAPI framework for building APIs
from prometheus_fastapi_instrumentator import Instrumentator  # For Prometheus metrics integration
import psycopg2  # PostgreSQL database adapter
from psycopg2.extras import RealDictCursor
import os  # For environment variables

# Database connection parameters
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_NAME = os.getenv("DB_NAME", "postgres")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

# Initialize FastAPI application
app = FastAPI()
# Set up Prometheus metrics instrumentation for monitoring
Instrumentator().instrument(app).expose(app)

# Database connection function
def get_db_connection():
    """
    Creates and returns a connection to the PostgreSQL database
    """
    try:
        return psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            cursor_factory=RealDictCursor
        )
    except psycopg2.Error as e:
        raise HTTPException(status_code=500, detail=f"Database connection error: {str(e)}")

# Health check endpoint to verify service is running
@app.get("/health")
def health_check():
    """
    Returns a simple health check response to indicate service status
    """
    return {"status": "ok"}

# Data endpoint that serves the main API functionality
@app.get("/data")
def get_data():
    """
    Retrieves data from the items table
    """
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT name FROM items")
            items = [item['name'] for item in cur.fetchall()]
            return {"data": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

# Football clubs endpoint that returns list of top football clubs
@app.get("/footballClub")
def get_football_clubs():
    """
    Returns a list of football clubs from the database
    """
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT name, country FROM football_clubs")
            clubs = cur.fetchall()
            return {"clubs": clubs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()
