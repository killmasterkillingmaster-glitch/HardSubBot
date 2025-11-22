Enterimport os
from telegram.ext import ApplicationBuilder, MessageHandler, filters, CommandHandler
import subprocess

BOT_TOKEN = os.environ.get("8244378197:AAHyweoSbGBy7lfGUJuYsju2fqEpjYR8v5Y")

video_file = None
sub_file = None
mode = None

async def start(update, context):
    await update.message.reply_text("Send /hardsub or /softsub to begin.")

async def hardsub(update, context):
    global mode, sub_file, video_file
    mode = "hardsub"
    video_file = None
    sub_file = None
    await update.message.reply_text("Hardsub mode ON.\nUpload subtitle file (.ass/.srt/.vtt)")

async def softsub(update, context):
    global mode, sub_file, video_file
    mode = "softsub"
    video_file = None
    sub_file = None
    await update.message.reply_text("Softsub mode ON.\nUpload subtitle file (.ass/.srt/.vtt)")

async def file_handler(update, context):
    global sub_file, video_file, mode

    doc = await update.message.document.get_file()
    file_name = update.message.document.file_name

    path = f"input/{file_name}"
    os.makedirs("input", exist_ok=True)
    await doc.download_to_drive(path)

    if file_name.endswith((".ass", ".srt", ".vtt")):
        sub_file = path
        await update.message.reply_text("Subtitle received. Now send the VIDEO file (.mp4/.mkv)")
    elif file_name.endswith((".mp4", ".mkv")):
        video_file = path
        await update.message.reply_text("Video received. Processing…")
        await process(update)
    else:
        await update.message.reply_text("Unsupported file type.")

async def process(update):
    global mode, sub_file, video_file

    if mode == "hardsub":
        out = "output.mp4"
        cmd = f'ffmpeg -i "{video_file}" -vf subtitles="{sub_file}" "{out}"'
    else:
        out = "output.mkv"
        cmd = f'ffmpeg -i "{video_file}" -i "{sub_file}" -c copy -c:s srt "{out}"'

    subprocess.call(cmd, shell=True)

    await update.message.reply_document(open(out, "rb"))
    os.remove(out)

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("hardsub", hardsub))
    app.add_handler(CommandHandler("softsub", softsub))
    app.add_handler(MessageHandler(filters.Document.ALL, file_handler))

    app.run_polling()

if __name__ == "__main__":
    main()
