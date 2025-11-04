import os
import shutil
import asyncio
import subprocess
from pathlib import Path
from pyrogram import Client, filters
from pyrogram.types import Message

# ---------- Configuration (from environment) ----------
API_ID = int(os.environ.get("API_ID", "0"))        # from my.telegram.org
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("8244378197:AAHyweoSbGBy7lfGUJuYsju2fqEpjYR8v5Y", "")

if not all([API_ID, API_HASH, BOT_TOKEN]):
    raise RuntimeError("Set API_ID, API_HASH, and BOT_TOKEN as environment variables.")

# ---------- Globals ----------
app = Client("hardsubbot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
BASE = Path("/tmp/hardsub")   # per-deploy temp working dir
BASE.mkdir(parents=True, exist_ok=True)

# Keep per-chat state: saved filenames (video, ass, font)
state = {}  # chat_id -> {"video": path, "ass": path, "font": path}


def cleanup_chat(chat_id: int):
    entry = state.get(chat_id)
    if not entry:
        return
    for k in ("video", "ass", "font", "output_dir"):
        p = entry.get(k)
        if p:
            try:
                if Path(p).is_dir():
                    shutil.rmtree(p, ignore_errors=True)
                else:
                    Path(p).unlink(missing_ok=True)
            except Exception:
                pass
    state.pop(chat_id, None)


async def run_ffmpeg(video_path: str, ass_path: str, font_dir: str, output_path: str):
    # Use fontsdir to ensure custom .otf is used
    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(video_path),
        "-vf", f"ass={str(ass_path)}:fontsdir={str(font_dir)}",
        "-c:a", "copy",
        str(output_path)
    ]
    # run in executor so we don't block event loop
    loop = asyncio.get_event_loop()
    proc = await loop.run_in_executor(None, lambda: subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE))
    return proc.returncode, proc.stdout, proc.stderr


@app.on_message(filters.command("start"))
async def start_cmd(client: Client, message: Message):
    await message.reply_text(
        "🔥 HardSub Bot ready!\n\n"
        "Workflow: Send a video -> send the .ass file (as file) -> send the font (.otf) -> bot will hard-sub and return output.\n\n"
        "You can also send the files in any order; when the bot has all 3 it will process automatically.\n\n"
        "To reset current session: /reset"
    )


@app.on_message(filters.command("reset"))
async def reset_cmd(client: Client, message: Message):
    cleanup_chat(message.chat.id)
    await message.reply_text("✅ Session reset. Please send new files.")


def ensure_chat_entry(chat_id: int):
    if chat_id not in state:
        state[chat_id] = {}


# Accept videos (video / document video)
@app.on_message(filters.video | filters.document & filters.mime_type.startswith("video/"))
async def receive_video(client: Client, message: Message):
    chat_id = message.chat.id
    ensure_chat_entry(chat_id)
    await message.reply_text("⬇️ Video received — downloading...")
    outdir = BASE / f"{chat_id}"
    outdir.mkdir(parents=True, exist_ok=True)

    path = await message.download(file_name=str(outdir / "input_video"))
    state[chat_id]["video"] = path
    state[chat_id]["output_dir"] = str(outdir)

    await message.reply_text("🎥 Video saved. Now send the .ass subtitle file (as a document).")
    # attempt auto-process if ass & font already present
    await try_process(chat_id, message)


# Accept .ass and other documents
@app.on_message(filters.document)
async def receive_document(client: Client, message: Message):
    chat_id = message.chat.id
    ensure_chat_entry(chat_id)
    filename = message.document.file_name or "file"
    lower = filename.lower()

    outdir = BASE / f"{chat_id}"
    outdir.mkdir(parents=True, exist_ok=True)

    if lower.endswith(".ass"):
        await message.reply_text("⬇️ .ass subtitle received — downloading...")
        path = await message.download(file_name=str(outdir / "subtitle.ass"))
        state[chat_id]["ass"] = path
        await message.reply_text("📝 Subtitle saved. Now send the font (.otf).")
        await try_process(chat_id, message)
        return

    if lower.endswith(".otf") or lower.endswith(".ttf"):
        await message.reply_text("⬇️ Font received — downloading...")
        font_path = await message.download(file_name=str(outdir / filename))
        # create fontsdir (ffmpeg expects a directory)
        fonts_dir = outdir / "fonts"
        fonts_dir.mkdir(exist_ok=True)
        # move/copy downloaded font into fonts dir
        dest = fonts_dir / filename
        Path(font_path).rename(dest)
        state[chat_id]["font"] = str(dest)
        state[chat_id]["fonts_dir"] = str(fonts_dir)
        await message.reply_text("🔠 Font saved. If video and subtitle are present I will start processing now.")
        await try_process(chat_id, message)
        return

    # If some other file, ignore politely
    await message.reply_text("⚠️ Unsupported file type. Send .ass for subtitles or .otf/.ttf for fonts, or send a video.")


async def try_process(chat_id: int, message: Message):
    entry = state.get(chat_id, {})
    video = entry.get("video")
    ass = entry.get("ass")
    fonts_dir = entry.get("fonts_dir")
    if not (video and ass and fonts_dir):
        return  # still waiting for files

    # All files present — start processing
    await message.reply_text("🔁 All files present. Starting FFmpeg processing — this may take some time depending on video size.")
    outdir = Path(entry.get("output_dir", "/tmp")) 
    output_file = outdir / "output_hardsub.mp4"

    try:
        rc, out, err = await run_ffmpeg(video_path=video, ass_path=ass, font_dir=fonts_dir, output_path=str(output_file))
        if rc == 0 and output_file.exists():
            await message.reply_video(str(output_file), caption="✅ Here is your hard-subbed video.")
        else:
            stderr_text = err.decode(errors="ignore") if isinstance(err, (bytes, bytearray)) else str(err)
            await message.reply_text(f"❌ FFmpeg failed. stderr:\n{stderr_text[:1500]}")
    except Exception as e:
        await message.reply_text(f"❌ Processing error: {e}")
    finally:
        # cleanup to save disk
        cleanup_chat(chat_id)


@app.on_message(filters.command("help"))
async def help_cmd(_, message: Message):
    await message.reply_text(
        "How to use:\n1) Send video\n2) Send .ass subtitle (as file)\n3) Send font (.otf or .ttf)\nWhen bot has all three, it will produce the hard-subbed video.\nCommands: /start /reset /help"
    )


if __name__ == "__main__":
    print("Starting HardSubBot...")
    app.run()
