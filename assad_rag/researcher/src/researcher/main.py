import json
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template
import os
from logic import research_with_rag, ResearchSession
import re

load_dotenv()

app = Flask(__name__)

# Store active sessions
sessions = {}

def is_valid_url(url):
    """Check if a string is a valid URL."""
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return url_pattern.match(url) is not None

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/query', methods=['POST'])
def query():
    data = request.json
    query_text = data.get('query', '').strip()
    session_id = data.get('sessionId', 'default')
    
    # Get or create session
    if session_id not in sessions:
        sessions[session_id] = ResearchSession()
    session = sessions[session_id]
    
    # Check if the query is a URL
    url = None
    if query_text.startswith('http://') or query_text.startswith('https://'):
        if is_valid_url(query_text):
            url = query_text
        else:
            return jsonify({
                'error': 'Invalid URL format. Please provide a valid URL.'
            }), 400
    
    try:
        result = research_with_rag(query_text, session=session, url=url)
        return jsonify({
            'response': {
                'general': result['content']['general'],
                'technical': result['content']['technical']
            },
            'sources': result['sources']
        })
    except Exception as e:
        return jsonify({
            'error': f'An error occurred: {str(e)}'
        }), 500

if __name__ == '__main__':
    app.run(debug=True)
