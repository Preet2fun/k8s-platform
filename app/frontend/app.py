"""
Frontend Service - Flask Application
Provides API endpoints that proxy requests to the backend service
"""

import os
import logging
import sys
from flask import Flask, jsonify, request
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from prometheus_flask_exporter import PrometheusMetrics

# Configure structured logging (JSON format)
logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s", "level":"%(levelname)s", "message":"%(message)s", "module":"%(module)s"}',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Initialize Flask application
app = Flask(__name__)

# Initialize Prometheus metrics
metrics = PrometheusMetrics(app)
# Add custom metric info
metrics.info('frontend_app_info', 'Frontend Application Info', version='1.0.0')

# Configuration from environment variables
BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://backend:8000")
BACKEND_DATA_URL = f"{BACKEND_BASE_URL}/data"
BACKEND_FOOTBALL_URL = f"{BACKEND_BASE_URL}/footballClub"
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "5"))  # seconds

# Configure requests session with retry logic and connection pooling
def create_session():
    """
    Create a requests session with retry logic and connection pooling
    """
    session = requests.Session()

    # Retry strategy: 3 retries with exponential backoff
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,  # 1s, 2s, 4s delays
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"]
    )

    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=10,
        pool_maxsize=10
    )

    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session

# Create global session for connection pooling
http_session = create_session()

# Health check endpoint for Kubernetes probes
@app.route("/health")
def health():
    """
    Health check endpoint for liveness probe
    Returns 200 if the application is running
    """
    return jsonify({"status": "healthy", "service": "frontend"}), 200

# Readiness check endpoint
@app.route("/ready")
def ready():
    """
    Readiness check endpoint - verifies backend connectivity
    Returns 200 if backend is reachable, 503 otherwise
    """
    try:
        response = http_session.get(
            f"{BACKEND_BASE_URL}/health",
            timeout=2
        )
        if response.status_code == 200:
            return jsonify({"status": "ready", "backend": "connected"}), 200
        else:
            logger.warning(f"Backend health check failed: {response.status_code}")
            return jsonify({"status": "not_ready", "backend": "unhealthy"}), 503
    except requests.exceptions.RequestException as e:
        logger.error(f"Backend readiness check failed: {str(e)}")
        return jsonify({"status": "not_ready", "backend": "unreachable"}), 503

# Route for the home page
@app.route("/")
def home():
    """
    Home endpoint - fetches data from backend /data endpoint
    """
    request_id = request.headers.get('X-Request-ID', 'unknown')
    logger.info(f"Home endpoint called - request_id: {request_id}")

    try:
        # Make GET request to backend service with timeout
        response = http_session.get(
            BACKEND_DATA_URL,
            timeout=REQUEST_TIMEOUT,
            headers={'X-Request-ID': request_id}
        )
        response.raise_for_status()  # Raise exception for 4xx/5xx status codes

        # Parse JSON response from backend
        data = response.json()

        logger.info(f"Successfully fetched data from backend - request_id: {request_id}")
        return jsonify({
            "frontend": "Hello from Flask!",
            "backend": data
        }), 200

    except requests.exceptions.Timeout:
        logger.error(f"Backend request timeout - request_id: {request_id}")
        return jsonify({
            "error": "Backend service timeout",
            "message": "The backend service took too long to respond"
        }), 504  # Gateway Timeout

    except requests.exceptions.ConnectionError:
        logger.error(f"Backend connection error - request_id: {request_id}")
        return jsonify({
            "error": "Backend service unavailable",
            "message": "Could not connect to backend service"
        }), 503  # Service Unavailable

    except requests.exceptions.HTTPError as e:
        logger.error(f"Backend HTTP error: {e} - request_id: {request_id}")
        return jsonify({
            "error": "Backend error",
            "message": "Backend returned an error"
        }), 502  # Bad Gateway

    except Exception as e:
        logger.exception(f"Unexpected error in home endpoint - request_id: {request_id}")
        return jsonify({
            "error": "Internal server error",
            "message": "An unexpected error occurred"
        }), 500

# Route for football clubs
@app.route("/clubs")
def football_clubs():
    """
    Football clubs endpoint - fetches club data from backend
    """
    request_id = request.headers.get('X-Request-ID', 'unknown')
    logger.info(f"Clubs endpoint called - request_id: {request_id}")

    try:
        # Make GET request to football clubs endpoint with timeout
        response = http_session.get(
            BACKEND_FOOTBALL_URL,
            timeout=REQUEST_TIMEOUT,
            headers={'X-Request-ID': request_id}
        )
        response.raise_for_status()

        logger.info(f"Successfully fetched clubs from backend - request_id: {request_id}")
        return jsonify(response.json()), 200

    except requests.exceptions.Timeout:
        logger.error(f"Backend request timeout - request_id: {request_id}")
        return jsonify({
            "error": "Backend service timeout",
            "message": "The backend service took too long to respond"
        }), 504

    except requests.exceptions.ConnectionError:
        logger.error(f"Backend connection error - request_id: {request_id}")
        return jsonify({
            "error": "Backend service unavailable",
            "message": "Could not connect to backend service"
        }), 503

    except requests.exceptions.HTTPError as e:
        logger.error(f"Backend HTTP error: {e} - request_id: {request_id}")
        return jsonify({
            "error": "Backend error",
            "message": "Backend returned an error"
        }), 502

    except Exception as e:
        logger.exception(f"Unexpected error in clubs endpoint - request_id: {request_id}")
        return jsonify({
            "error": "Internal server error",
            "message": "An unexpected error occurred"
        }), 500

# Run the application if this file is executed directly
if __name__ == "__main__":
    logger.info(f"Starting frontend service on port 5000")
    logger.info(f"Backend URL: {BACKEND_BASE_URL}")
    logger.info(f"Request timeout: {REQUEST_TIMEOUT}s")

    # Start Flask server - for development only
    # In production, use Gunicorn (see Dockerfile)
    app.run(host="0.0.0.0", port=5000)
