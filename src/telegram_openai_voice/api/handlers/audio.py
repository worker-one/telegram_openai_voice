import logging
import os
import time
from pathlib import Path
from telegram_openai_voice.db import crud
from telegram_openai_voice.service.app import App
from openai import OpenAI
import pyaudio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = App("parameter")
openai = OpenAI()

def register_handlers(bot):
    @bot.message_handler(content_types=['voice', 'audio'])
    def get_audio_messages(message):
        user_id = message.from_user.id
        username = message.from_user.username
        user_message = message

        logger.info(
            msg="User event",
            extra={
                "user_id": user_id,
                "username": username,
                "user_message": user_message
                }
            )

        user = crud.get_user(user_id)
        if not user:
            user = crud.upsert_user(user_id, username)
        if message.voice:
            file_info = bot.get_file(message.voice.file_id)
        elif message.audio:
            file_info = bot.get_file(message.audio.file_id)
        else:
            return
        downloaded_file = bot.download_file(file_info.file_path)

        for file_type in ("voice", "audio"):
            if not os.path.exists(f"./tmp/{user_id}/{file_type}"):
                os.makedirs(f"./tmp/{user_id}/{file_type}")
        file_path = f"./tmp/{user_id}/{file_info.file_path}"
        with open(file_path, 'wb') as new_file:
            new_file.write(downloaded_file)

        transcription, translation = process_audio(file_path)
        speech_response_path = generate_speech_response(translation)

        with open(speech_response_path, 'rb') as speech_file:
            bot.send_voice(message.chat.id, speech_file)

def process_audio(file_path):
    # Create transcription from audio file
    transcription = openai.audio.transcriptions.create(
        model="whisper-1",
        file=Path(file_path),
    ).text

    # Create translation from audio file
    translation = openai.audio.translations.create(
        model="whisper-1",
        file=Path(file_path),
    ).text

    return transcription, translation

def generate_speech_response(text):
    speech_file_path = Path(f"./tmp/speech_response.mp3")
    with openai.audio.speech.with_streaming_response.create(
        model="tts-1",
        voice="alloy",
        input=text,
    ) as response:
        response.stream_to_file(speech_file_path)
    return speech_file_path

def stream_to_speakers():
    player_stream = pyaudio.PyAudio().open(format=pyaudio.paInt16, channels=1, rate=24000, output=True)

    start_time = time.time()

    with openai.audio.speech.with_streaming_response.create(
        model="tts-1",
        voice="alloy",
        response_format="pcm",
        input="""I see skies of blue and clouds of white
                The bright blessed days, the dark sacred nights
                And I think to myself
                What a wonderful world""",
    ) as response:
        print(f"Time to first byte: {int((time.time() - start_time) * 1000)}ms")
        for chunk in response.iter_bytes(chunk_size=1024):
            player_stream.write(chunk)

    print(f"Done in {int((time.time() - start_time) * 1000)}ms.")