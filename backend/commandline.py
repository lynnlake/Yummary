import os
import re
import sys
import time
import shutil

# config
import config

# youtube
import yt_dlp

# openai
import whisper
from openai import AzureOpenAI

PROMPT = {
  "summary": "You will receive a subtitle file for a video, which may contain some spelling errors. Please try to understand the text content and provide bullet points for this video."
}

def _downloadYoutube(video_id, ydl_opts, postfix, filename):
    url = f"https://www.youtube.com/watch?v={video_id}"
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
      shutil.rmtree("tmp", ignore_errors=True)
      os.mkdir("tmp")
      current_dir = os.getcwd()
      os.chdir("tmp")
      ydl.download([url])
      files = os.listdir()
      for file in files:
        if file.endswith(postfix):
          shutil.move(file, f"../{filename}")
          print(f"Audio file saved to {filename}")
          break
    os.chdir(current_dir)

def downloadYoutubeCaptions(video_id, filename="captions.vtt"):
  ydl_opts = {
    'skip_download': True,
    'writesubtitles': True,
    'subtitlesformat': 'vtt',
    'subtitleslangs': ['en', 'zh-Hans', 'zh-Hant'],
  }
  _downloadYoutube(video_id, ydl_opts, ".vtt", filename)

  # remove time stamps and empty lines
  if not os.path.exists(filename):
    raise Exception("No captions found")
  with open(filename, "r") as file:
    content = file.read()
    # repleace all lines like this: 00:00:11.261 --> 00:00:17.101
    content = re.sub(r"\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}", "", content)
    # remove all empty lines
    content = re.sub(r"\n+", "\n", content)
  with open(filename, "w") as file:
    file.write(content)
    print(f"Captions saved to {filename}")

def downloadYoutubeAudio(video_id, filename="audio.aac"):
  ydl_opts = {
    'format': 'm4a/bestaudio/best',
  }
  _downloadYoutube(video_id, ydl_opts, ".m4a", filename)

# This may take a while, better use the api version
def getAudioTextLocal(audio_file, transcript_file="transcript.txt"):
  start = time.time()
  print("Getting audio text... (This may take a while)")
  model = whisper.load_model("base")
  result = model.transcribe(audio_file)
  # print("Audio text below:\n", result["text"])
  with open(transcript_file, "w") as file:
    file.write(result["text"])
    print("Audio text saved to", transcript_file)
  end = time.time()
  print(f"Time taken: {end - start:.2f} seconds")
  return result["text"]

def getTranscriptForVideo(video_id):
  transcript_file = f"{video_id}.txt"
  audio_file = f"{video_id}.aac"
  # try to download captions first, if failed, download audio and transcribe
  try:
    downloadYoutubeCaptions(video_id, transcript_file)
  except:
    downloadYoutubeAudio(video_id, audio_file)
    getAudioTextLocal(audio_file, transcript_file)

  with open(transcript_file, "r") as file:
    transcript = file.read()
    return transcript

def getSummaryForText(text):
  print("Getting summary from openAI...")
  client = AzureOpenAI(
    azure_endpoint = config.openai_endpoint,
    api_key=config.openai_key,
    api_version=config.api_version
  )

  message_text = [
    {"role":"system", "content": PROMPT["summary"]},
    {"role":"user","content": text},
  ]

  completion = client.chat.completions.create(
    model=config.model,
    messages=message_text,
    temperature=0.7,
    max_tokens=800,
    top_p=0.95,
    frequency_penalty=0,
    presence_penalty=0,
    stop=None
  )
  return completion.choices[0].message.content

# A reasonable YouTube URL should be as follows.
# https://www.youtube.com/watch?v=pyUDqk-p7mc
# The function will extract 'pyUDqk-p7mc' as the video_id and ignore subsequent parameters.
def validateYoutubeUrl(url):
  pattern = re.compile(r"youtube\.com/watch\?v=([a-zA-Z0-9_-]+)")
  match = pattern.search(url)
  assert match, "Invalid youtube url"
  video_id = match.group(1)
  print(f"Valid youtube url, video id: {video_id}")
  return video_id

def main():
  assert len(sys.argv) == 2, "Invalid number of arguments"
  url = sys.argv[1]
  video_id = validateYoutubeUrl(url)
  video_transcript = getTranscriptForVideo(video_id)
  summary = getSummaryForText(video_transcript)
  print("=============YUMMARY=============")
  print(summary)


if __name__ == "__main__":
  main()
