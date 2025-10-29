from flask import Flask, render_template, redirect, url_for, request, jsonify, session
import logging
import os
import uuid
from datetime import datetime

from backend.routes.aop_suite import aop_app


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = Flask(__name__)

# Configure session
app.secret_key = os.environ.get('SECRET_KEY') or 'your-secret-key-here'  # Change in production
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True

app.register_blueprint(aop_app)

# In-memory session store (for simplicity)
sessions = {}


@app.route('/')
def index():
    """Main AOP-Suite application"""
    return render_template('services/AOPapp.html', 
                         title='AOP-Suite',
                         mie_query='',
                         qid='',
                         qid_wd='')

@app.route('/aop')
def aop_redirect():
    """Redirect old AOP route to main page"""
    return redirect(url_for('index'))

# Update session data structure to include more project info
@app.route('/session/start', methods=['POST'])
def start_session():
    data = request.get_json()
    project_name = data.get('project_name', '').strip()
    description = data.get('description', '').strip()
    author = data.get('author', '').strip()
    
    if not project_name:
        return jsonify({'success': False, 'error': 'Project name is required'})
    
    # Generate session ID and store data
    session_id = str(uuid.uuid4())
    date_created = datetime.now().isoformat()
    
    session_data = {
        'session_id': session_id,
        'project_name': project_name,
        'description': description,
        'author': author,
        'date_created': date_created,
        'active': True
    }
    
    # Store in a simple in-memory dict (or use a database for persistence)
    sessions[session_id] = session_data
    
    # Set session cookie
    session['session_id'] = session_id
    
    return jsonify({'success': True, 'session_id': session_id, 'project_name': project_name})

@app.route('/session/status')
def session_status():
    session_id = session.get('session_id')
    if session_id and session_id in sessions:
        return jsonify(sessions[session_id])
    return jsonify({'active': False})

@app.route('/session/update', methods=['POST'])
def update_session():
    session_id = session.get('session_id')
    if not session_id or session_id not in sessions:
        return jsonify({'success': False, 'error': 'No active session'})
    
    data = request.get_json()
    # Update only provided fields
    for field in ['project_name', 'description', 'author']:
        if field in data:
            sessions[session_id][field] = data.get(field, '').strip()
    
    return jsonify({'success': True, 'data': sessions[session_id]})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
