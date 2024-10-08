import streamlit as st
import requests
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound, VideoUnavailable
import google.generativeai as genai
import os
import logging
import dotenv
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
import io

# Configure Logging
logging.basicConfig(level=logging.INFO)
dotenv.load_dotenv()
# Set API URL from environment variable
API_URL = os.getenv("API_URL", "http://localhost:5000")  # Adjust this if necessary

# Configure Generative AI
genai.configure(api_key=os.environ["API_KEY"])

def extract_video_id(link):
    """Extracts video ID from the YouTube link."""
    if "v=" in link:
        video_id = link.split("v=")[1]
        if '&' in video_id:
            video_id = video_id.split('&')[0]
        return video_id
    elif "youtu.be/" in link:
        return link.split("youtu.be/")[1].split('?')[0]
    else:
        return None

def generate_summary(text, prompt):
    """Generates a summary using Google Gemini AI."""
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(f"{prompt}\n\n{text}")
    return response.text  # Return the generated text directly

def create_pdf(text):
    """Creates a PDF file from the text with headings and margins."""
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Define margins
    margin_left = 72
    margin_right = 72
    margin_top = 72
    margin_bottom = 72

    # Title
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(margin_left, height - margin_top, "Video Summary")

    # Set font for body text
    pdf.setFont("Helvetica", 12)

    # Split text into lines
    lines = text.split('\n')
    y_position = height - margin_top - 30  # Start below the title

    for line in lines:
        # Remove leading and trailing asterisks
        line = line.strip()
        
        # Check if line has bold headings
        if line.startswith("**") and line.endswith("**"):
            pdf.setFont("Helvetica-Bold", 12)
            line = line[2:-2].strip()  # Remove asterisks for the heading
        else:
            pdf.setFont("Helvetica", 12)

        # Calculate maximum width for the line considering the right margin
        max_width = width - margin_left - margin_right

        # Wrap the text if it exceeds the maximum width
        if pdf.stringWidth(line) > max_width:
            words = line.split()
            wrapped_line = ""
            for word in words:
                if pdf.stringWidth(wrapped_line + word) <= max_width:
                    wrapped_line += word + " "
                else:
                    pdf.drawString(margin_left, y_position, wrapped_line.strip())
                    y_position -= 15  # Move down for the next line
                    wrapped_line = word + " "

            # Draw the last wrapped line
            if wrapped_line:
                pdf.drawString(margin_left, y_position, wrapped_line.strip())
                y_position -= 15  # Move down for the next line
        else:
            # Write line to PDF with margins
            pdf.drawString(margin_left, y_position, line)
            y_position -= 15  # Move down for the next line

        # Check if y_position is too low on the page
        if y_position < margin_bottom:
            pdf.showPage()  # Create a new page
            pdf.setFont("Helvetica", 12)
            y_position = height - margin_top  # Reset y_position for the new page

    pdf.showPage()
    pdf.save()
    buffer.seek(0)

    return buffer

# Streamlit App
st.title("YouTube Video Analyzer")

# Input Form
url = st.text_input("Enter YouTube URL")

if st.button("Analyze"):
    if not url:
        st.error("Please enter a valid YouTube URL.")
    else:
        video_id = extract_video_id(url)
        if not video_id:
            st.error("Invalid YouTube URL.")
        else:
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
                summary_text = generate_summary(concatenated_text, prompt)

                # Display summary
                st.header("Video Summary")
                st.markdown(summary_text)

                # Video Thumbnail
                st.image(f"http://img.youtube.com/vi/{video_id}/0.jpg", use_column_width=True)

                # Create PDF
                pdf_buffer = create_pdf(summary_text)

                # Download Link
                st.download_button(
                    label="Download PDF",
                    data=pdf_buffer,
                    file_name="video_summary.pdf",
                    mime="application/pdf"
                )
            except TranscriptsDisabled:
                logging.error(f"Transcripts are disabled for video ID: {video_id}")
                st.error("Transcripts are disabled for this video.")
            except NoTranscriptFound:
                logging.error(f"No transcript found for video ID: {video_id}")
                st.error("No transcript found for this video.")
            except VideoUnavailable:
                logging.error(f"Video unavailable: {video_id}")
                st.error("The video is unavailable.")
            except Exception as e:
                logging.exception(f"An unexpected error occurred: {str(e)}")
                st.error("An unexpected error occurred on the server.")
