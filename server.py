"""
Flask Server for Suno Song Parser
Serves the frontend and handles parsing requests
"""

from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from sunoParser import SunoSongParser, parse_suno_song
import os
import logging
from typing import List, Dict, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)  # Enable CORS for all routes

# Initialize parser
parser = SunoSongParser()

@app.route('/')
def index():
    """Serve the main page"""
    return render_template('sunoLoader.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files"""
    return send_from_directory('static', filename)

@app.route('/api/parse', methods=['POST'])
def parse_song():
    """
    Parse a Suno song URL
    Expected JSON: {"url": "https://suno.com/song/..."}
    """
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({
                'error': 'Missing URL',
                'message': 'Please provide a "url" field in the request body'
            }), 400
        
        url = data['url'].strip()
        logger.info(f"Parsing URL: {url}")
        
        # Parse the song
        result = parser.parse_song_url(url)
        
        if result:
            return jsonify({
                'success': True,
                'data': result
            })
        else:
            return jsonify({
                'error': 'Parse failed',
                'message': 'Could not parse the song URL. Please check if the URL is valid.'
            }), 404
            
    except Exception as e:
        logger.error(f"Error parsing song: {e}")
        return jsonify({
            'error': 'Server error',
            'message': str(e)
        }), 500

@app.route('/api/parse-multiple', methods=['POST'])
def parse_multiple_songs():
    """
    Parse multiple Suno song URLs
    Expected JSON: {"urls": ["https://suno.com/song/...", ...]}
    """
    try:
        data = request.get_json()
        if not data or 'urls' not in data:
            return jsonify({
                'error': 'Missing URLs',
                'message': 'Please provide a "urls" field in the request body'
            }), 400
        
        urls = data['urls']
        if not isinstance(urls, list):
            return jsonify({
                'error': 'Invalid URLs',
                'message': 'URLs must be provided as an array'
            }), 400
        
        logger.info(f"Parsing {len(urls)} URLs")
        
        results = []
        for url in urls:
            result = parser.parse_song_url(url.strip())
            if result:
                results.append(result)
        
        return jsonify({
            'success': True,
            'data': results,
            'total': len(results),
            'requested': len(urls)
        })
        
    except Exception as e:
        logger.error(f"Error parsing multiple songs: {e}")
        return jsonify({
            'error': 'Server error',
            'message': str(e)
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'message': 'Suno Song Parser API is running'
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Not found',
        'message': 'The requested endpoint does not exist'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'error': 'Internal server error',
        'message': 'An unexpected error occurred'
    }), 500

if __name__ == '__main__':
    # Create required directories
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    # Run the server
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )
