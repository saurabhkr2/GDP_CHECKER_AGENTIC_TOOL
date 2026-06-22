"""
Frontend application for Document Quality Checker
Serves the UI and proxies API calls to the backend
"""

from flask import Flask, render_template
import os

app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')

# Agentic API URL (LangGraph-powered HITL pipeline)
AGENTIC_API_URL = os.getenv('AGENTIC_API_URL', 'http://localhost:5003/api')


@app.route('/')
@app.route('/review')
def review():
    """Agentic UI with human-in-the-loop comment approval."""
    return render_template('review.html', agentic_api_url=AGENTIC_API_URL)


@app.route('/login')
def login():
    """Login page. Authentication is performed client-side against the backend."""
    return render_template('login.html', agentic_api_url=AGENTIC_API_URL)


if __name__ == '__main__':
    port = int(os.getenv('FRONTEND_PORT', '5000'))
    app.run(debug=False, host='0.0.0.0', port=port)
