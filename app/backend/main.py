"""
Backend Service - FastAPI Application
Provides API endpoints that query PostgreSQL database
"""

import os
import logging
import sys
from contextlib import contextmanager
from typing import Generator

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from psycopg2 import OperationalError, DatabaseError

# Configure structured logging (JSON format)
logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s", "level":"%(levelname)s", "message":"%(message)s", "module":"%(module)s"}',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Database connection parameters
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_NAME = os.getenv("DB_NAME", "postgres")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_MIN_CONN = int(os.getenv("DB_MIN_CONN", "2"))
DB_MAX_CONN = int(os.getenv("DB_MAX_CONN", "10"))

# Initialize FastAPI application
app = FastAPI(
    title="Backend Service",
    version="1.0.0",
    description="Backend API for k8s-platform demo"
)

# Set up Prometheus metrics instrumentation for monitoring
Instrumentator().instrument(app).expose(app)

# Global connection pool
connection_pool = None


@app.on_event("startup")
async def startup_event():
    """
    Initialize database connection pool on application startup
    """
    global connection_pool
    try:
        connection_pool = psycopg2.pool.SimpleConnectionPool(
            DB_MIN_CONN,
            DB_MAX_CONN,
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            cursor_factory=RealDictCursor
        )
        logger.info(
            f"Database connection pool created successfully. "
            f"Min: {DB_MIN_CONN}, Max: {DB_MAX_CONN}"
        )
    except Exception as e:
        logger.error(f"Failed to create database connection pool: {str(e)}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """
    Close all database connections on application shutdown
    """
    global connection_pool
    if connection_pool:
        connection_pool.closeall()
        logger.info("Database connection pool closed")


@contextmanager
def get_db_connection() -> Generator:
    """
    Context manager for database connections from the pool
    Ensures connections are properly returned to the pool
    """
    conn = None
    try:
        conn = connection_pool.getconn()
        if conn:
            yield conn
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to get database connection from pool"
            )
    except OperationalError as e:
        logger.error(f"Database operational error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection error"
        )
    finally:
        if conn:
            connection_pool.putconn(conn)


# Middleware to add request ID for distributed tracing
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """
    Add request ID to all requests for tracing
    """
    request_id = request.headers.get("X-Request-ID", "unknown")
    request.state.request_id = request_id

    logger.info(f"Request: {request.method} {request.url.path} - request_id: {request_id}")

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id

    return response


# Health check endpoint for liveness probe
@app.get("/health", tags=["Health"])
def health_check():
    """
    Health check endpoint for liveness probe
    Returns 200 if the application is running
    Does not check database connectivity
    """
    return {"status": "healthy", "service": "backend"}


# Readiness check endpoint that verifies database connectivity
@app.get("/ready", tags=["Health"])
def readiness_check():
    """
    Readiness check endpoint for readiness probe
    Verifies database connectivity before marking as ready
    Returns 200 if database is accessible, 503 otherwise
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Simple query to verify database connectivity
                cur.execute("SELECT 1")
                result = cur.fetchone()

                if result:
                    return {
                        "status": "ready",
                        "database": "connected",
                        "pool_available": connection_pool.maxconn - len(connection_pool._used)
                    }
                else:
                    logger.warning("Database readiness check failed: no result")
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="Database not responding"
                    )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready"
        )


# Data endpoint that serves the main API functionality
@app.get("/data", tags=["Data"])
def get_data(request: Request):
    """
    Retrieves data from the items table
    """
    request_id = getattr(request.state, "request_id", "unknown")
    logger.info(f"Fetching data from items table - request_id: {request_id}")

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, name, description, created_at FROM items ORDER BY id"
                )
                items = cur.fetchall()

                logger.info(
                    f"Successfully fetched {len(items)} items - request_id: {request_id}"
                )
                return {"data": items}

    except HTTPException:
        raise
    except DatabaseError as e:
        logger.error(f"Database error in get_data: {str(e)} - request_id: {request_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database query error"
        )
    except Exception as e:
        logger.exception(f"Unexpected error in get_data - request_id: {request_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# Football clubs endpoint that returns list of football clubs
@app.get("/footballClub", tags=["Data"])
def get_football_clubs(request: Request):
    """
    Returns a list of football clubs from the database
    """
    request_id = getattr(request.state, "request_id", "unknown")
    logger.info(f"Fetching football clubs - request_id: {request_id}")

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, name, country, founded_year, created_at "
                    "FROM football_clubs ORDER BY id"
                )
                clubs = cur.fetchall()

                logger.info(
                    f"Successfully fetched {len(clubs)} clubs - request_id: {request_id}"
                )
                return {"clubs": clubs}

    except HTTPException:
        raise
    except DatabaseError as e:
        logger.error(
            f"Database error in get_football_clubs: {str(e)} - request_id: {request_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database query error"
        )
    except Exception as e:
        logger.exception(
            f"Unexpected error in get_football_clubs - request_id: {request_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler to catch any unhandled exceptions
    """
    request_id = getattr(request.state, "request_id", "unknown")
    logger.exception(f"Unhandled exception - request_id: {request_id}")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "request_id": request_id
        }
    )
