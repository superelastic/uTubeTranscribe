from google.cloud import speech_v1p1beta1 as speech
from google.cloud import storage
from googleapiclient.discovery import build
from yt_dlp import YoutubeDL
import os
import logging
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

logging.basicConfig(level=logging.INFO)

# YouTube API setup
youtube = build('youtube', 'v3', developerKey=os.getenv("YOUTUBE_API_KEY"))

# Cloud Storage client
storage_client = storage.Client()

# Speech-to-Text client
speech_client = speech.SpeechClient()

def download_youtube_audio(video_id, output_filename):
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
            'preferredquality': '192',
        }],
        'outtmpl': output_filename,
        'ffmpeg_location': 'C:/FFmpeg/bin',  # Replace with actual path
        # Add FFmpeg args to convert to mono directly
        'postprocessor_args': [
            '-ac', '1'
        ],
    }
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([f'https://www.youtube.com/watch?v={video_id}'])

def upload_to_gcs(bucket_name, source_file_name, destination_blob_name):
    try:
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_filename(source_file_name)
        logging.info(f"File {source_file_name} uploaded to {destination_blob_name}.")
    except Exception as e:
        logging.error(f"An error occurred while uploading to GCS: {e}")
        raise

def transcribe_audio(gcs_uri):
    audio = speech.RecognitionAudio(uri=gcs_uri)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        language_code="en-US",
    )
    operation = speech_client.long_running_recognize(config=config, audio=audio)
    
    # Remove the poll() call and just check done() status
    print("Waiting for operation to complete...")
    while not operation.done():
        print("Still transcribing... Please wait.")
        time.sleep(30)   # Wait 30 seconds before checking again
    
    response = operation.result(timeout=18000)  # Set timeout to 5 hours (18000 seconds)
    
    transcription = ""
    for result in response.results:
        transcription += result.alternatives[0].transcript + " "
    
    return transcription

def save_transcription(bucket_name, destination_blob_name, transcription):
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_string(transcription)

# Main process
video_id = "bKFLqfc1mn0"
audio_filename = "audio.wav"
bucket_name = "my-new-bucket-without-vpc"

# Download YouTube audio
download_youtube_audio(video_id, audio_filename)

# Upload audio to GCS
audio_gcs_path = f"audio/{video_id}.wav"
upload_to_gcs(bucket_name, audio_filename, audio_gcs_path)

# Transcribe audio
gcs_uri = f"gs://{bucket_name}/{audio_gcs_path}"
transcription = transcribe_audio(gcs_uri)

# Save transcription to GCS
transcription_gcs_path = f"transcriptions/{video_id}.txt"
save_transcription(bucket_name, transcription_gcs_path, transcription)

print(f"Transcription saved to gs://{bucket_name}/{transcription_gcs_path}")
