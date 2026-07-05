# Github.com/Vasusen-code

from main.plugins.helpers import get_link, join, screenshot
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
        
@Bot.on_message(filters.private & filters.incoming & ~filters.command("start"))
async def clone(bot, event):
    if not event.text:
        return
    link = get_link(event.text)
    if not link:
        return
    edit = await bot.send_message(event.chat.id, 'Trying to process.')
    if 't.me/+' in link:
        xy = await join(userbot, link)
        await edit.edit(xy)
        return 
    if 't.me' in link:
        try:
            await get_msg(userbot, bot, event.chat.id, link, edit) 
        except FloodWait:
            return await edit.edit('Too many requests, try again later.')
        except ValueError:
            return await edit.edit('Send Only message link or Private channel invites  @groupdc .')
        except Exception as e:
            return await edit.edit(f'Error: `{str(e)}`')         
          
