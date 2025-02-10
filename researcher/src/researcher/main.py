import json
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template, send_file, send_from_directory
import os
from logic import research_with_rag, ResearchSession
import re
from pdf_file import generate_research_paper
import threading
from datetime import datetime, timedelta

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

@app.route('/api/export-pdf', methods=['POST'])
def export_pdf():
    try:
        data = request.json
        session_id = data.get('sessionId', 'default')
        instructions = data.get('instructions', '')
        paper_standard = data.get('paperStandard', 'ITTT')
        formatting_options = data.get('formattingOptions', '')
        
        if session_id not in sessions:
            return jsonify({'error': 'Session not found'}), 404
            
        session = sessions[session_id]
        
        # Generate unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"research_paper_{session_id}_{timestamp}.pdf"
        
        # Create temp directory in static folder
        temp_dir = os.path.join(app.static_folder, 'temp_pdfs')
        os.makedirs(temp_dir, exist_ok=True)
        output_path = os.path.join(temp_dir, filename)
        
        # Generate PDF
        file_path = generate_research_paper(
            chat_history=session.conversation_history,
            paper_standard=paper_standard,
            formatting_options=formatting_options,
            instructions=instructions,
            output_path=output_path
        )
        
        return jsonify({
            'success': True,
            'filename': os.path.basename(file_path),
            'download_url': f'/static/temp_pdfs/{os.path.basename(file_path)}'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<path:filename>')
def download_file(filename):
    try:
        return send_from_directory(
            os.path.join(app.static_folder, 'temp_pdfs'),
            filename,
            as_attachment=True
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 404

if __name__ == '__main__':
    app.run(debug=True)
