from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound, VideoUnavailable
import dotenv
import os
import google.generativeai as genai
from flask_cors import CORS
import logging

# Load environment variables
dotenv.load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configure CORS to allow your Vercel frontend domain
CORS(app)

# Configure Generative AI
genai.configure(api_key=os.environ["API_KEY"])

# Set up logging
logging.basicConfig(level=logging.INFO)

@app.route('/')
def index():
    return "Welcome to the YouTube Transcript Summarizer API!"

@app.route('/summarize', methods=['POST'])
def summarize_video():
    # Get the YouTube link from the request
    data = request.get_json()
    link = data.get("link")
    
    if not link:
        return jsonify({"error": "No YouTube link provided."}), 400
    
    # Extract the video ID
    video_id = extract_video_id(link)
    if not video_id:
        return jsonify({"error": "Invalid YouTube URL."}), 400

    try:
        # Fetch transcript
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'hi', 'bn'])
        all_texts = [entry['text'] for entry in transcript]
        concatenated_text = " ".join(all_texts)
        
        # Summarize the transcript using Google Gemini AI
        prompt = (
            "Summarize the following text comprehensively, ensuring no information is omitted. "
            "The summary should cover all key points, facts, and minor details, organized in a clear and structured format. "
            "Present the summary in bullet points for easy readability. Bold the headings."
        )
        response = generate_summary(concatenated_text, prompt)
        return jsonify({"summary": response.text, "video_id": video_id}), 200

    except TranscriptsDisabled:
        logging.error(f"Transcripts are disabled for video ID: {video_id}")
        return jsonify({"error": "Transcripts are disabled for this video."}), 403

    except NoTranscriptFound:
        logging.error(f"No transcript found for video ID: {video_id}")
        return jsonify({"error": "No transcript found for this video."}), 404

    except VideoUnavailable:
        logging.error(f"Video unavailable: {video_id}")
        return jsonify({"error": "The video is unavailable."}), 404

    except Exception as e:
        logging.exception(f"An unexpected error occurred: {str(e)}")
        return jsonify({"error": "An unexpected error occurred on the server."}), 500

def extract_video_id(link):
    """Extracts video ID from the YouTube link."""
    if "v=" in link:
        # For full YouTube URLs (e.g., https://www.youtube.com/watch?v=VIDEO_ID)
        video_id = link.split("v=")[1]
        if '&' in video_id:
            video_id = video_id.split('&')[0]
        return video_id
    elif "youtu.be/" in link:
        # For shortened YouTube URLs (e.g., https://youtu.be/VIDEO_ID)
        return link.split("youtu.be/")[1].split('?')[0]
    else:
        return None

def generate_summary(text, prompt):
    """Generates a summary using Google Gemini AI."""
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(f"{prompt}\n\n{text}")
    return response

if __name__ == '__main__':
    app.run(debug=True)
