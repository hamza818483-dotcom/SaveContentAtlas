#Github.com/Vasusen-code
import os, time, asyncio
from pyrogram import filters
from main.plugins.main import Bot
from main.plugins.display_progress import progress_for_pyrogram

COMPRESS_PRESETS = {
    "fast": {"crf": "28", "preset": "ultrafast", "scale": None},
    "balanced": {"crf": "23", "preset": "medium", "scale": None},
    "small": {"crf": "28", "preset": "medium", "scale": "640:-2"},
}

pending_compress = {}

def _video_from_message(message):
    if message.video:
        return message.video
    if message.document and (message.document.mime_type or "").startswith("video/"):
        return message.document
    return None

@Bot.on_message(filters.private & filters.command("compress"))
async def cmd_compress(client, message):
    reply = message.reply_to_message
    video_obj = _video_from_message(reply) if reply else None
    if not video_obj:
        await message.reply(
            "Reply to a video with /compress.\n"
            "Usage: /compress fast|balanced|small\n"
            "fast = quick, larger file\nbalanced = good quality/size (default)\nsmall = 360p, smallest file"
        )
        return

    args = message.text.split(None, 1)
    quality = args[1].strip().lower() if len(args) > 1 else "balanced"
    if quality not in COMPRESS_PRESETS:
        await message.reply("Invalid option. Use: fast, balanced, or small.")
        return

    status = await message.reply(f"Downloading video... (preset: {quality})")
    chat_id = message.chat.id
    in_path = None
    out_path = None
    try:
        start = time.time()
        in_path = await client.download_media(
            reply,
            file_name=f"compress_in_{chat_id}_{int(time.time())}.mp4",
            progress=progress_for_pyrogram,
            progress_args=(client, "**DOWNLOADING:**\n", status, start),
        )
        await status.edit("Compressing...")

        preset = COMPRESS_PRESETS[quality]
        out_path = f"compress_out_{chat_id}_{int(time.time())}.mp4"
        cmd = ["ffmpeg", "-y", "-i", in_path, "-c:v", "libx264",
               "-crf", preset["crf"], "-preset", preset["preset"]]
        if preset["scale"]:
            cmd += ["-vf", f"scale={preset['scale']}"]
        cmd += ["-c:a", "aac", "-b:a", "128k", out_path]

        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        _, stderr = await process.communicate()

        if not os.path.isfile(out_path):
            await status.edit(f"ERROR: Compression failed.\n{stderr.decode().strip()[-300:]}")
            return

        in_size = os.path.getsize(in_path)
        out_size = os.path.getsize(out_path)
        caption = (
            f"Compressed ({quality})\n"
            f"Before: {in_size/1_000_000:.1f} MB\n"
            f"After: {out_size/1_000_000:.1f} MB\n"
            f"Reduced: {(1 - out_size/in_size)*100:.0f}%"
        )
        await status.edit("Uploading...")
        upload_start = time.time()
        await client.send_video(
            chat_id, out_path, caption=caption, supports_streaming=True,
            progress=progress_for_pyrogram,
            progress_args=(client, "**UPLOADING:**\n", status, upload_start),
        )
        await status.delete()
    except Exception as e:
        await status.edit(f"ERROR: {str(e)}")
    finally:
        for p in (in_path, out_path):
            if p and os.path.isfile(p):
                os.remove(p)
