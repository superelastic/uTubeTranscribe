from google.cloud import speech_v1p1beta1 as speech
from google.cloud import storage
from googleapiclient.discovery import build
import youtube_dl
import os

# Set up credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "C:\Users\fisch\AppData\Roaming\gcloud\application_default_credentials.json"

# YouTube API setup
youtube = build('youtube', 'v3', developerKey='AIzaSyAt95vjsPkv6dwIBw2uyPvwoD73wcNCAgg')

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
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([f'https://www.youtube.com/watch?v={video_id}'])

def upload_to_gcs(bucket_name, source_file_name, destination_blob_name):
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(source_file_name)

def transcribe_audio(gcs_uri):
    audio = speech.RecognitionAudio(uri=gcs_uri)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code="en-US",
    )
    operation = speech_client.long_running_recognize(config=config, audio=audio)
    response = operation.result()
    
    transcription = ""
    for result in response.results:
        transcription += result.alternatives[0].transcript + " "
    
    return transcription

def save_transcription(bucket_name, destination_blob_name, transcription):
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_string(transcription)

# Main process
video_id = "YOUR_YOUTUBE_VIDEO_ID"
audio_filename = "audio.wav"
bucket_name = "YOUR_GCS_BUCKET_NAME"

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