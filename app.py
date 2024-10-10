import streamlit as st
import requests
import google.generativeai as genai
import os
import logging
import dotenv
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

# Configure Logging
logging.basicConfig(level=logging.INFO)
dotenv.load_dotenv()

# Set API URL from environment variable
API_URL = os.getenv("API_URL", "http://localhost:5000") 

# Configure Generative AI
genai.configure(api_key=os.environ["API_KEY"])

# RapidAPI Headers and URL
RAPIDAPI_URL = "https://youtube-transcripts.p.rapidapi.com/youtube/transcript"
RAPIDAPI_HEADERS = {
    "x-rapidapi-key": os.getenv("RAPIDAPI_KEY"),  
    "x-rapidapi-host": "youtube-transcripts.p.rapidapi.com"
}

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

def fetch_transcript(video_url):
    """Fetches transcript using the RapidAPI service."""
    querystring = {"url": video_url, "chunkSize": "1000"} 
    try:
        response = requests.get(RAPIDAPI_URL, headers=RAPIDAPI_HEADERS, params=querystring)
        response.raise_for_status() 
        return response.json()  
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching transcript: {e}")
        return None

def generate_summary(text, prompt):
    """Generates a summary using Google Gemini AI."""
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(f"{prompt}\n\n{text}")
    return response.text 

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

 
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(margin_left, height - margin_top, "Video Summary")

 
    pdf.setFont("Helvetica", 12)

    # Split text into lines
    lines = text.split('\n')
    y_position = height - margin_top - 30  

    for line in lines:
      
        line = line.strip()
        
       
        if line.startswith("**") and line.endswith("**"):
            pdf.setFont("Helvetica-Bold", 12)
            line = line[2:-2].strip()  
        else:
            pdf.setFont("Helvetica", 12)

       
        max_width = width - margin_left - margin_right

     
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

 
        if y_position < margin_bottom:
            pdf.showPage() 
            pdf.setFont("Helvetica", 12)
            y_position = height - margin_top  

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
                # Fetch transcript using RapidAPI
                transcript_response = fetch_transcript(url)
                if transcript_response:
                    all_texts = [chunk['text'] for chunk in transcript_response['content']]
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
                else:
                    st.error("Could not fetch the transcript.")
            except Exception as e:
                logging.exception(f"An unexpected error occurred: {str(e)}")
                st.error("An unexpected error occurred on the server.")
