# Github.com/Vasusen-code

from main.plugins.helpers import get_link, join, screenshot, get_youtube_id, download_youtube, download_youtube_thumbnail
from main.plugins.display_progress import progress_for_pyrogram

from decouple import config

API_ID = config("API_ID", default=None, cast=int)
API_HASH = config("API_HASH", default=None)
BOT_TOKEN = config("BOT_TOKEN", default=None)
SESSION = config("SESSION", default=None) #pyro session

from pyrogram.errors import FloodWait, BadRequest
from pyrogram import Client, filters
from ethon.pyfunc import video_metadata

import re, time, asyncio, logging, os, json

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
    print("[BOOT] Starting Bot client...")
    if not Bot.is_connected:
        while True:
            try:
                await Bot.start()
                print("[BOOT] Bot client started successfully.")
                break
            except _FloodWait as e:
                print(f"[FloodWait] Bot: waiting {e.value}s")
                await asyncio.sleep(e.value + 5)
    print("[BOOT] Starting userbot client...")
    if not userbot.is_connected:
        while True:
            try:
                await userbot.start()
                print("[BOOT] userbot client started successfully.")
                break
            except _FloodWait as e:
                print(f"[FloodWait] userbot: waiting {e.value}s")
                await asyncio.sleep(e.value + 5)
            except Exception as e:
                print(f"[FATAL] userbot failed to start: {e}")
                raise
    print("[BOOT] All clients ready.")

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

    # Case 1: reply is a YouTube link -> fetch the real YT thumbnail directly
    if not video_obj and reply and reply.text:
        yt_id = get_youtube_id(reply.text)
        if yt_id:
            status = await message.reply("Fetching original YouTube thumbnail...")
            thumb_path = None
            hd_path = None
            try:
                thumb_path = await download_youtube_thumbnail(reply.text.strip(), message.chat.id)
                if not thumb_path:
                    await status.edit("ERROR: Could not fetch YouTube thumbnail.")
                    return
                hd_path = f"{thumb_path}_1080.jpg"
                cmd = [
                    "ffmpeg", "-y", "-i", thumb_path,
                    "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
                    hd_path
                ]
                process = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                await process.communicate()
                send_path = hd_path if os.path.isfile(hd_path) else thumb_path
                await bot.send_photo(message.chat.id, send_path, caption="1080p Thumbnail")
                await status.delete()
            except Exception as e:
                await status.edit(f"ERROR: {str(e)}")
            finally:
                if thumb_path and os.path.isfile(thumb_path):
                    os.remove(thumb_path)
                if hd_path and os.path.isfile(hd_path):
                    os.remove(hd_path)
            return

    target_msg = reply
    if not video_obj and reply and reply.text:
        mapped_id = await get_yt_map_entry(message.chat.id, reply.id)
        if not mapped_id:
            mapped_id = yt_video_map.get((message.chat.id, reply.id))
        if mapped_id:
            try:
                target_msg = await bot.get_messages(message.chat.id, mapped_id)
                video_obj = target_msg.video or target_msg.document
            except Exception:
                target_msg = None
                video_obj = None
        if not video_obj:
            target_msg = None

    if not target_msg or not video_obj:
        await message.reply("Reply to a video with /thumb.")
        return
    status = await message.reply("Extracting 1080p thumbnail...")
    video_path = None
    thumb_path = None
    try:
        video_path = await bot.download_media(target_msg)
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

YT_MAP_FILE = "yt_video_map.json"

def _load_yt_map():
    try:
        with open(YT_MAP_FILE, "r") as f:
            raw = json.load(f)
        return {tuple(map(int, k.split(":"))): v for k, v in raw.items()}
    except Exception:
        return {}

def _save_yt_map():
    try:
        raw = {f"{k[0]}:{k[1]}": v for k, v in yt_video_map.items()}
        with open(YT_MAP_FILE, "w") as f:
            json.dump(raw, f)
    except Exception:
        pass

from main.plugins.thumb_store import get_yt_map_entry, set_yt_map_entry

yt_video_map = _load_yt_map()  # legacy local cache; Supabase is source of truth now

async def _download_and_send_youtube(bot, chat_id, url, reply_to_id):
    yt_id = get_youtube_id(url)
    edit = await bot.send_message(chat_id, 'Downloading YouTube video...')
    file = None
    try:
        file = await download_youtube(url.strip(), chat_id, status_message=edit)
        if not file or not os.path.isfile(file):
            await edit.edit('ERROR: Could not download this YouTube video.')
            return
        await edit.edit('Uploading...')
        data = video_metadata(file)
        duration = data["duration"]
        thumb_path = await screenshot(file, duration / 2, chat_id)
        sent = await bot.send_video(
            chat_id=chat_id,
            video=file,
            caption=f"YouTube: {yt_id}",
            supports_streaming=True,
            duration=duration,
            thumb=thumb_path,
            reply_to_message_id=reply_to_id,
            progress=progress_for_pyrogram,
            progress_args=(bot, '**UPLOADING:**\n', edit, time.time())
        )
        yt_video_map[(chat_id, reply_to_id)] = sent.id
        _save_yt_map()
        await set_yt_map_entry(chat_id, reply_to_id, sent.id)
        await edit.delete()
    except Exception as e:
        await edit.edit(f'ERROR: {str(e)}')
    finally:
        if file and os.path.isfile(file):
            os.remove(file)

@Bot.on_message(filters.private & filters.command("yt"))
async def cmd_yt(bot, message):
    text = message.text.split(None, 1)
    if len(text) < 2 or not get_youtube_id(text[1]):
        await message.reply("Usage: /yt <youtube_link>")
        return
    await _download_and_send_youtube(bot, message.chat.id, text[1].strip(), message.id)

@Bot.on_message(filters.private & filters.incoming & ~filters.command("start") & ~filters.command("thumb") & ~filters.command(["up", "done", "me", "prompt", "new", "compress", "yt"]))
async def clone(bot, event):
    if not event.text:
        return

    yt_id = get_youtube_id(event.text)
    if yt_id:
        # YT links no longer auto-download; use /yt <link>
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
