from pytube import YouTube
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound
from moviepy.editor import AudioFileClip
import os
from pydub import AudioSegment
import time


def normalize_volume(folder_path, audio_file, target_volume=-30):
    audio_path = os.path.join(folder_path, audio_file)
    audio = AudioSegment.from_mp3(audio_path)
    audio_volume = audio.dBFS
    volume_change = target_volume - audio_volume
    audio = audio + volume_change
    output_path = os.path.join(folder_path, audio_file)
    audio.export(output_path, format="mp3")


def change_sampling_rate(audio_path, sampling_rate=16000):
    audio = AudioSegment.from_file(audio_path)
    audio = audio.set_frame_rate(sampling_rate)
    audio.export(audio_path, format="mp3")
    changed_audio = AudioSegment.from_file(audio_path)
    print("New sampling rate:", changed_audio.frame_rate, "Hz")


def clean_filename(filename):
    return "".join(char for char in filename if char.isalnum() or char in ['_', ' ']).rstrip()


def download_audio(output_folder, youtube_url):
    yt = YouTube(youtube_url)
    speaker_folder = output_folder
    if not os.path.exists(speaker_folder):
        os.makedirs(speaker_folder)

    audio_name = f"{clean_filename(yt.title)}.mp3"
    audio_path = os.path.join(speaker_folder, audio_name)
    audio = yt.streams.filter(only_audio=True).first()
    audio.download(filename=audio_path)
    return audio_path, speaker_folder, yt, audio_name


def format_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"


def split_audio(audio_path, transcript, speaker_id, output_folder, film_id):
    clip = AudioFileClip(audio_path)
    clip1 = AudioSegment.from_file(audio_path)
    print("Sampling rate:", clip1.frame_rate, "Hz")
    for i, entry in enumerate(transcript):
        start_time = entry['start']
        end_time = start_time + entry['duration']

        if start_time < clip1.duration_seconds and end_time < clip1.duration_seconds:
            if start_time > 0.1:
                start_time -= 0.1
            if end_time < clip1.duration_seconds - 0.1:
                end_time += 0.1
            split_clip = clip.subclip(start_time, end_time)
            output_folder_path = os.path.join(output_folder, f'{speaker_id}_{film_id}_{i+1}.mp3')

            # Check if there are profanities in the transcript
            if not exclude_line(entry['text']):
                split_clip.write_audiofile(output_folder_path)
            else:
                print(f"Excluded line in transcript for sample {i+1}.")
        else:
            print(f"Sample time out of range for audio file for sample {i+1}.")

    clip.close()


def exclude_line(text):
    exclusion_list = ['*', '(', ')', '[', ']']  # Add other profanities
    for exclusion in exclusion_list:
        if exclusion.lower() in text.lower():
            return True
    return False


def download_transcript(youtube_url, speaker_folder, speaker_id, film_id, lang='en'):
    _id = youtube_url.split("=")[1].split("&")[0]

    transcript_filename = f"{speaker_id}_{film_id}_transcript.txt"
    transcript_path = os.path.join(speaker_folder, transcript_filename)
    try:
        transcript = YouTubeTranscriptApi.get_transcript(_id, languages=[lang])
        convert_transcript(transcript, transcript_path)
        return transcript
    except NoTranscriptFound:
        print("Transcript in English is not available for this video.")
        return None


def convert_transcript(transcript, transcript_path):
    with open(transcript_path, 'w', encoding='utf-8') as file:
        for i, entry in enumerate(transcript):
            text = entry['text'].replace('\n', ' ')

            # Remove entire line with profanity
            if not exclude_line(text):
                file.write(f"{i+1}: {text}\n")
            else:
                print(f"Removed line in transcript for sample {i+1}.")


def remove_file(file_path):
    max_attempts = 5
    for attempt in range(max_attempts):
        try:
            os.remove(file_path)
            print(f"File {file_path} removed.")
            break
        except PermissionError:
            print(f"Attempt {attempt + 1}/{max_attempts}: File {file_path} is in use...")
            time.sleep(2)


def create_speaker_legend(folder, legend_filename, legend):
    os.makedirs(folder, exist_ok=True)
    legend_path = os.path.join(folder, legend_filename)
    with open(legend_path, 'w', encoding='utf-8') as file:
        for entry in legend:
            file.write(f"{entry['speaker_id']} {entry['name']}\n")


def create_film_legend(folder, legend_filename, legend):
    os.makedirs(folder, exist_ok=True)
    legend_path = os.path.join(folder, legend_filename)
    with open(legend_path, 'w', encoding='utf-8') as file:
        for entry in legend:
            file.write(f"{entry['speaker_id']} {entry['film_id']} {entry['name']}\n")


def main():
    youtube_url_list = ["list of youtube film"]
    speakers_legend = []
    films_legend = []
    lang = 'en'

    for youtube_url in youtube_url_list:
        speaker_id = None
        film_id = None
        output_folder = None

        yt = YouTube(youtube_url)

        _id = youtube_url.split("=")[1].split("&")[0]
        try:
            transcript = YouTubeTranscriptApi.get_transcript(_id, languages=[lang])
        except NoTranscriptFound:
            print("Transcript in English is not available for this video.")

        if transcript:
            # Check if speaker already exists in the legend
            channel_name = clean_filename(yt.author)
            existing_speaker_entry = next((entry for entry in speakers_legend if entry['name'] == channel_name), None)

            if existing_speaker_entry:
                speaker_id = existing_speaker_entry['speaker_id']
            else:
                speaker_id = f"S{len(speakers_legend) + 1:02d}"
                speakers_legend.append({'speaker_id': speaker_id, 'name': channel_name})

            # Check if film already exists in the legend
            film_name = clean_filename(yt.title)
            film_id = f"F{len(films_legend) + 1:02d}"
            films_legend.append({'film_id': film_id, 'speaker_id': speaker_id, 'name': film_name})

        audio_path, speaker_folder,
