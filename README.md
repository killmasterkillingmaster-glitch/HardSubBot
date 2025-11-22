here# Hardsub Bot 🤖🎬

A Telegram bot that adds subtitles to videos with support for multiple subtitle formats.

## Features ✨
- **Hardsub** - Burn subtitles directly into video
- **Softsub** - Add subtitles as separate stream
- **Multi-format support**: .ass, .srt, .vtt, .txt
- **Fast processing** with FFmpeg

## Commands 🎯
- `/hardsub` - Upload subtitle → Upload video → Get hardsubbed video
- `/softsub` - Upload subtitle → Upload video → Get softsubbed video

## Supported Subtitle Formats 📁
- **.ass** (Advanced SubStation Alpha)
- **.srt** (SubRip Subtitle)
- **.vtt** (WebVTT)
- **.txt** (Plain text)

## How to Use 🚀
1. Send `/hardsub` or `/softsub`
2. Upload your subtitle file (.ass/.srt/.vtt/.txt)
3. Upload your video file
4. Bot will process and send back the subtitled video

## Deployment 🛠️
This bot is deployed using GitHub Actions and runs 24/7.

## Tech Stack 💻
- Python
- python-telegram-bot
- FFmpeg
- pysubs2

## Author
[Your Name] - Telegram bot developer
