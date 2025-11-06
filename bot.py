import os
import shutil
import asyncio
import subprocess
from pathlib import Path
from pyrogram import Client, filters
from pyrogram.types import Message

# ---------- Configuration (Environment variables se) ----------
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

if not all([API_ID, API_HASH, BOT_TOKEN]):
    raise RuntimeError("Set API_ID, API_HASH, and BOT_TOKEN as environment variables.")

# ---------- Globals ----------
app = Client("hardsubbot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
BASE = Path("/tmp/hardsub")
BASE.mkdir(parents=True, exist_ok=True)

state = {}  # chat_id -> {"video": path, "ass": path}


def cleanup_chat(chat_id: int):
    entry = state.get(chat_id)
    if not entry:
        return
    for k in ("video", "ass", "output_dir"):
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


async def run_ffmpeg(video_path: str, ass_path: str, output_path: str):
    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(video_path),
        "-vf", f"ass={str(ass_path)}",
        "-c:a", "copy",
        str(output_path)
    ]
    loop = asyncio.get_event_loop()
    proc = await loop.run_in_executor(None, lambda: subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE))
    return proc.returncode, proc.stdout, proc.stderr


@app.on_message(filters.command("start"))
async def start_cmd(client: Client, message: Message):
    await message.reply_text(
        "🔥 HardSub Bot Ready!\n\n"
        "Send a video 🎥 and then an .ass subtitle file 📄\n"
        "Bot will automatically hard-sub it for you!\n\n"
        "Commands:\n/start - Welcome\n/reset - Clear old files\n/help - Usage info"
    )


@app.on_message(filters.command("reset"))
async def reset_cmd(client: Client, message: Message):
    cleanup_chat(message.chat.id)
    await message.reply_text("✅ Session reset. Please send new files.")


def ensure_chat_entry(chat_id: int):
    if chat_id not in state:
        state[chat_id] = {}


# Accept video file
@app.on_message(filters.video | (filters.document & filters.mime_type.startswith("video/")))
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
    await try_process(chat_id, message)


# Accept subtitle (.ass)
@app.on_message(filters.document)
async def receive_document(client: Client, message: Message):
    chat_id = message.chat.id
    ensure_chat_entry(chat_id)
    filename = message.document.file_name or "file"
    lower = filename.lower()

    outdir = BASE / f"{chat_id}"
    outdir.mkdir(parents=True, exist_ok=True)

    if lower.endswith(".ass"):
        await message.reply_text("⬇️ Subtitle (.ass) received — downloading...")
        path = await message.download(file_name=str(outdir / "subtitle.ass"))
        state[chat_id]["ass"] = path
        await message.reply_text("📝 Subtitle saved. Starting process if video available...")
        await try_process(chat_id, message)
        return

    await message.reply_text("⚠️ Unsupported file type. Please send only .ass for subtitles or a video.")


async def try_process(chat_id: int, message: Message):
    entry = state.get(chat_id, {})
    video = entry.get("video")
    ass = entry.get("ass")
    if not (video and ass):
        return  # Wait until both available

    await message.reply_text("🔁 All files present. Starting FFmpeg processing...")
    outdir = Path(entry.get("output_dir", "/tmp"))
    output_file = outdir / "output_hardsub.mp4"

    try:
        rc, out, err = await run_ffmpeg(video_path=video, ass_path=ass, output_path=str(output_file))
        if rc == 0 and output_file.exists():
            await message.reply_video(str(output_file), caption="✅ Here is your hard-subbed video.")
        else:
            stderr_text = err.decode(errors="ignore") if isinstance(err, (bytes, bytearray)) else str(err)
            await message.reply_text(f"❌ FFmpeg failed:\n{stderr_text[:1500]}")
    except Exception as e:
        await message.reply_text(f"❌ Processing error: {e}")
    finally:
        cleanup_chat(chat_id)


@app.on_message(filters.command("help"))
async def help_cmd(_, message: Message):
    await message.reply_text(
        "How to use:\n"
        "1️⃣ Send video\n"
        "2️⃣ Send .ass subtitle (as file)\n"
        "✅ Bot will process and send hard-subbed video back.\n\n"
        "Commands: /start /reset /help"
    )


if __name__ == "__main__":
    print("Starting HardSubBot...")
    app.run()
