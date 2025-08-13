# Import required libraries
from flask import Flask, jsonify  # Flask for web framework, jsonify for JSON responses
import requests  # For making HTTP requests to the backend service

# Initialize Flask application
app = Flask(__name__)
# Define backend service URLs - using kubernetes service name 'backend'
BACKEND_BASE_URL = "http://backend:8000"
BACKEND_DATA_URL = f"{BACKEND_BASE_URL}/data"
BACKEND_FOOTBALL_URL = f"{BACKEND_BASE_URL}/footballClub"

# Route for the home page
@app.route("/")
def home():
    try:
        # Make GET request to backend service
        response = requests.get(BACKEND_DATA_URL)
        # Parse JSON response from backend
        data = response.json()
        # Return combined response from frontend and backend
        return jsonify({"frontend": "Hello from Flask!", "backend": data})
    except Exception as e:
        # Return error message if backend request fails
        return jsonify({"error": str(e)})

# Route for football clubs
@app.route("/clubs")
def football_clubs():
    try:
        # Make GET request to football clubs endpoint
        response = requests.get(BACKEND_FOOTBALL_URL)
        # Parse and return the football clubs data
        return jsonify(response.json())
    except Exception as e:
        # Return error message if backend request fails
        return jsonify({"error": str(e)})

# Run the application if this file is executed directly
if __name__ == "__main__":
    # Start Flask server on all network interfaces (0.0.0.0) on port 5000
    app.run(host="0.0.0.0", port=5000)
