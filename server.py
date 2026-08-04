from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from sunoParser import SunoSongParser
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

server = Flask(__name__, static_folder='public')
CORS(server)

parser = SunoSongParser()

@server.route('/')
def index():
    return send_from_directory(server.static_folder, 'sunoLoader.html')

@server.route('/public/<path:filename>')
def static_files(filename):
    return send_from_directory('public', filename)

@server.route('/api/parse', methods=['POST'])
def parse_song():
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'error': 'Missing URL', 'message': 'Please provide a "url" field in the request body'}), 400
        url = data['url'].strip()
        logger.info(f"Parsing URL: {url}")
        result = parser.parse_song_url(url)
        if result:
            return jsonify({'success': True, 'data': result})
        return jsonify({'error': 'Parse failed', 'message': 'Could not parse the song URL. Please check if the URL is valid.'}), 404
    except Exception as e:
        logger.error(f"Error parsing song: {e}")
        return jsonify({'error': 'Server error', 'message': str(e)}), 500

@server.route('/api/parse-multiple', methods=['POST'])
def parse_multiple_songs():
    try:
        data = request.get_json()
        if not data or 'urls' not in data or not isinstance(data['urls'], list):
            return jsonify({'error': 'Invalid URLs', 'message': 'Please provide a "urls" array in the request body'}), 400
        urls = data['urls']
        logger.info(f"Parsing {len(urls)} URLs")
        results = [r for url in urls if (r := parser.parse_song_url(url.strip()))]
        return jsonify({'success': True, 'data': results, 'total': len(results), 'requested': len(urls)})
    except Exception as e:
        logger.error(f"Error parsing multiple songs: {e}")
        return jsonify({'error': 'Server error', 'message': str(e)}), 500

@server.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'message': 'Suno Song Parser API is running'})

@server.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found', 'message': 'The requested endpoint does not exist'}), 404

@server.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error', 'message': 'An unexpected error occurred'}), 500

if __name__ == '__main__':
    os.makedirs('public', exist_ok=True)
    port = int(os.environ.get('PORT', 5000))
    server.run(host='0.0.0.0', port=port, debug=False)
