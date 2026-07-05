# Github.com/Vasusen-code

from main.plugins.helpers import get_link, join, screenshot, get_youtube_id, download_youtube
from main.plugins.display_progress import progress_for_pyrogram

from decouple import config

API_ID = config("API_ID", default=None, cast=int)
API_HASH = config("API_HASH", default=None)
BOT_TOKEN = config("BOT_TOKEN", default=None)
SESSION = config("SESSION", default=None) #pyro session

from pyrogram.errors import FloodWait, BadRequest
from pyrogram import Client, filters
from ethon.pyfunc import video_metadata

import re, time, asyncio, logging, os

logging.basicConfig(format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s',
                    level=logging.WARNING)

Bot = Client(
    "Simple-Pyrogram-Bot",
    bot_token=BOT_TOKEN,
    api_id=int(API_ID),
    api_hash=API_HASH
)

userbot = Client(
    "userbot",
    session_string=SESSION,
    api_hash=API_HASH,
    api_id=API_ID)

from pyrogram.errors import FloodWait as _FloodWait

async def start_clients():
    if not Bot.is_connected:
        while True:
            try:
                await Bot.start()
                break
            except _FloodWait as e:
                print(f"[FloodWait] Bot: waiting {e.value}s")
                await asyncio.sleep(e.value + 5)
    if not userbot.is_connected:
        while True:
            try:
                await userbot.start()
                break
            except _FloodWait as e:
                print(f"[FloodWait] userbot: waiting {e.value}s")
                await asyncio.sleep(e.value + 5)
            except Exception as e:
                print(f"[FATAL] userbot failed to start: {e}")
                raise

def thumbnail(sender):
    if os.path.exists(f'{sender}.jpg'):
        return f'{sender}.jpg'
    else:
         return None
      
async def resolve_chat(userbot, chat_id):
    """Resolve peer using multiple fallback strategies."""
    try:
        return await userbot.get_chat(chat_id)
    except Exception:
        pass
    try:
        async for dialog in userbot.get_dialogs():
            if dialog.chat.id == chat_id:
                return dialog.chat
    except Exception:
        pass
    try:
        return await userbot.get_chat(chat_id)
    except Exception as e:
        raise ValueError(
            f"Could not resolve chat {chat_id}. Ensure the userbot account "
            f"is a member of this chat. ({e})"
        )

async def get_msg(userbot, client, sender, msg_link, edit):
    msg_id = int(msg_link.rstrip('/').split("/")[-1])
    if 't.me/c/' in msg_link:
        parts = msg_link.rstrip('/').split("/")
        channel_id = parts[parts.index('c') + 1]
        chat = int('-100' + str(channel_id))
        try:
            await resolve_chat(userbot, chat)
            while True:
                try:
                    msg = await userbot.get_messages(chat, msg_id)
                    break
                except FloodWait as e:
                    await edit.edit(f'Rate limited, waiting {e.value}s...')
                    await asyncio.sleep(e.value + 2)
            if msg is None or msg.empty:
                await edit.edit('ERROR: Message not found or was deleted.')
                return

            if msg.media_group_id:
                await edit.edit('Downloading album...')
                group_msgs = await userbot.get_media_group(chat, msg_id)
                for i, gmsg in enumerate(group_msgs):
                    gfile = await userbot.download_media(gmsg)
                    if not gfile:
                        continue
                    gcap = gmsg.caption or ""
                    ext = str(gfile).split(".")[-1].lower()
                    if ext in ("mp4", "mkv", "mov", "webm"):
                        await client.send_video(sender, gfile, caption=gcap, supports_streaming=True)
                    elif ext in ("jpg", "jpeg", "png", "webp"):
                        await client.send_photo(sender, gfile, caption=gcap)
                    else:
                        await client.send_document(sender, gfile, caption=gcap)
                    os.remove(gfile)
                await edit.delete()
                return

            await edit.edit('Downloading...')
            file = None
            if msg.media:
                file = await userbot.download_media(
                    msg,
                    progress=progress_for_pyrogram,
                    progress_args=(userbot, "**DOWNLOADING:**\n", edit, time.time())
                )
            caption = msg.text or msg.caption or ""
            if file:
                await edit.edit('Uploading...')
                ext = str(file).split(".")[-1].lower()
                if ext in ("mp4", "mkv", "mov", "webm"):
                    data = video_metadata(file)
                    duration = data["duration"]
                    thumb_path = await screenshot(file, duration / 2, sender)
                    await client.send_video(
                        chat_id=sender, video=file, caption=caption,
                        supports_streaming=True, duration=duration, thumb=thumb_path,
                        progress=progress_for_pyrogram,
                        progress_args=(client, '**UPLOADING:**\n', edit, time.time())
                    )
                elif ext in ("jpg", "jpeg", "png", "webp"):
                    await client.send_photo(
                        chat_id=sender, photo=file, caption=caption,
                        progress=progress_for_pyrogram,
                        progress_args=(client, '**UPLOADING:**\n', edit, time.time())
                    )
                elif ext in ("mp3", "m4a", "ogg", "flac", "wav"):
                    await client.send_audio(
                        chat_id=sender, audio=file, caption=caption,
                        progress=progress_for_pyrogram,
                        progress_args=(client, '**UPLOADING:**\n', edit, time.time())
                    )
                else:
                    thumb_path = thumbnail(sender)
                    await client.send_document(
                        sender, file, caption=caption, thumb=thumb_path,
                        progress=progress_for_pyrogram,
                        progress_args=(client, '**UPLOADING:**\n', edit, time.time())
                    )
            elif caption:
                await client.send_message(sender, caption)
            else:
                await edit.edit('ERROR: Message has no text or media to clone.')
                return
            await edit.delete()
        except FloodWait as e:
            await edit.edit(f'Too many requests. Wait {e.value}s and try again.')
        except Exception as e:
            await edit.edit(f'ERROR: {str(e)}')
            return
    else:
        chat = msg_link.rstrip('/').split("/")[-2]
        while True:
            try:
                await client.copy_message(int(sender), chat, msg_id)
                break
            except FloodWait as e:
                await edit.edit(f'Rate limited, waiting {e.value}s...')
                await asyncio.sleep(e.value + 2)
        await edit.delete()
        
def get_all_links(text):
    regex = r"(?i)\bhttps?://t\.me/\S+"
    return re.findall(regex, text)

def parse_range(link):
    """Support t.me/c/CHANNEL/START-END for batch fetch."""
    m = re.match(r"(https?://t\.me/c/\d+/)(\d+)-(\d+)/?$", link.strip())
    if not m:
        return None
    base, start, end = m.group(1), int(m.group(2)), int(m.group(3))
    if end < start or end - start > 200:
        return None
    return [f"{base}{i}" for i in range(start, end + 1)]

@Bot.on_message(filters.private & filters.command("thumb") & filters.reply)
async def extract_thumb(bot, message):
    reply = message.reply_to_message
    video_obj = reply.video if reply else None
    if not video_obj and reply and reply.document and (reply.document.mime_type or "").startswith("video/"):
        video_obj = reply.document
    if not reply or not video_obj:
        await message.reply("Reply to a video with /thumb.")
        return
    status = await message.reply("Extracting 1080p thumbnail...")
    video_path = None
    thumb_path = None
    try:
        video_path = await bot.download_media(reply)
        duration = getattr(video_obj, "duration", None) or 1
        thumb_path = f"thumb_{message.chat.id}_{int(time.time())}.jpg"
        cmd = [
            "ffmpeg", "-y", "-ss", str(duration / 2), "-i", video_path,
            "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
            "-vframes", "1", thumb_path
        ]
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        _, stderr = await process.communicate()
        if not os.path.isfile(thumb_path):
            await status.edit(f"ERROR: {stderr.decode().strip()[-300:]}")
            return
        await bot.send_photo(message.chat.id, thumb_path, caption="1080p Thumbnail")
        await status.delete()
    except Exception as e:
        await status.edit(f"ERROR: {str(e)}")
    finally:
        if video_path and os.path.isfile(video_path):
            os.remove(video_path)
        if thumb_path and os.path.isfile(thumb_path):
            os.remove(thumb_path)

@Bot.on_message(filters.private & filters.incoming & ~filters.command("start") & ~filters.command("thumb") & ~filters.command(["up", "done", "me", "prompt", "new"]))
async def clone(bot, event):
    if not event.text:
        return

    yt_id = get_youtube_id(event.text)
    if yt_id:
        edit = await bot.send_message(event.chat.id, 'Downloading YouTube video...')
        file = None
        try:
            file = await download_youtube(event.text.strip(), event.chat.id)
            if not file or not os.path.isfile(file):
                await edit.edit('ERROR: Could not download this YouTube video.')
                return
            await edit.edit('Uploading...')
            data = video_metadata(file)
            duration = data["duration"]
            thumb_path = await screenshot(file, duration / 2, event.chat.id)
            await bot.send_video(
                chat_id=event.chat.id,
                video=file,
                caption=f"YouTube: {yt_id}",
                supports_streaming=True,
                duration=duration,
                thumb=thumb_path,
                progress=progress_for_pyrogram,
                progress_args=(bot, '**UPLOADING:**\n', edit, time.time())
            )
            await edit.delete()
        except Exception as e:
            await edit.edit(f'ERROR: {str(e)}')
        finally:
            if file and os.path.isfile(file):
                os.remove(file)
        return

    links = get_all_links(event.text)
    if not links:
        return

    range_links = parse_range(links[0])
    if range_links:
        status = await bot.send_message(event.chat.id, f'Batch job: {len(range_links)} messages queued.')
        done, failed = 0, 0
        for link in range_links:
            edit = await bot.send_message(event.chat.id, f'Processing {done + failed + 1}/{len(range_links)}...')
            try:
                await get_msg(userbot, bot, event.chat.id, link, edit)
                done += 1
            except Exception:
                failed += 1
                await edit.edit(f'Skipped (error): {link}')
                await asyncio.sleep(1)
        await status.edit(f'Batch complete: {done} sent, {failed} failed.')
        return

    for link in links:
        edit = await bot.send_message(event.chat.id, 'Trying to process.')
        if 't.me/+' in link:
            xy = await join(userbot, link)
            await edit.edit(xy)
            continue
        if 't.me' in link:
            try:
                await get_msg(userbot, bot, event.chat.id, link, edit)
            except FloodWait as e:
                await edit.edit(f'Too many requests. Wait {e.value}s.')
            except ValueError:
                await edit.edit('Send Only message link or Private channel invites  @groupdc .')
            except Exception as e:
                await edit.edit(f'Error: `{str(e)}`')
