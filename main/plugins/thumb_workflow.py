#Github.com/Vasusen-code
import os, time
from pyrogram import filters
from main.plugins.main import Bot
from main.plugins.thumbgen import generate_thumbnail
from main.plugins.thumb_store import add_file_id, get_file_ids

# per-user in-memory state (collection flags/prompt only - not persistent, resets on redeploy which is fine)
user_state = {}

_add_file_id = add_file_id
_get_file_ids = get_file_ids

def _dir_for(chat_id):
    d = f"thumbdata_{chat_id}"
    os.makedirs(d, exist_ok=True)
    return d

def _get_state(chat_id):
    if chat_id not in user_state:
        user_state[chat_id] = {
            "collecting_samples": False,
            "prompt": "",
        }
    return user_state[chat_id]

@Bot.on_message(filters.private & filters.command("up"))
async def cmd_up(client, message):
    chat_id = message.chat.id
    st = _get_state(chat_id)
    st["collecting_samples"] = True
    await message.reply(
        "Sample thumbnail collection started. Send photos one by one (album/multiple at once supported).\n"
        "Type /done when finished."
    )

@Bot.on_message(filters.private & filters.command("done"))
async def cmd_done(client, message):
    chat_id = message.chat.id
    st = _get_state(chat_id)
    st["collecting_samples"] = False
    count = len(await _get_file_ids(chat_id, "samples"))
    await message.reply(f"Saved {count} sample thumbnail(s). Use /up again to add more, or /new <topic> to generate.")

@Bot.on_message(filters.private & filters.command("me"))
async def cmd_me(client, message):
    await message.reply("Send your photo(s) now (as image, not document). These will always be used as the subject.")
    _get_state(message.chat.id)["collecting_photo"] = True

@Bot.on_message(filters.private & filters.photo, group=1)
async def handle_photo(client, message):
    chat_id = message.chat.id
    st = _get_state(chat_id)
    file_id = message.photo.file_id

    if st.get("collecting_photo"):
        await _add_file_id(chat_id, "photos", file_id)
        await message.reply("Your photo saved. Send more or continue with /new <topic>.")
        return
    if st.get("collecting_samples"):
        count = await _add_file_id(chat_id, "samples", file_id)
        # only reply once per burst to avoid spam on albums; but keep it simple & informative
        await message.reply(f"Sample saved ({count} total). Send next, or /done to finish.")
        return
    # not in any collection mode -> ignore, other handlers may process

@Bot.on_message(filters.private & filters.command("prompt"))
async def cmd_prompt(client, message):
    chat_id = message.chat.id
    text = message.text.split(None, 1)
    if len(text) < 2:
        await message.reply("Usage: /prompt <your instructions>")
        return
    _get_state(chat_id)["prompt"] = text[1].strip()
    await message.reply("Prompt saved. It will be used for future /new generations.")

@Bot.on_message(filters.private & filters.command("new"))
async def cmd_new(client, message):
    chat_id = message.chat.id
    text = message.text.split(None, 1)
    topic = text[1].strip() if len(text) > 1 else "New Topic"

    sample_ids = await _get_file_ids(chat_id, "samples")
    photo_ids = await _get_file_ids(chat_id, "photos")

    if not sample_ids:
        await message.reply("No sample thumbnails saved yet. Use /up to add samples first.")
        return
    if not photo_ids:
        await message.reply("No photo saved yet. Use /me to upload your photo first.")
        return

    d = _dir_for(chat_id)
    st = _get_state(chat_id)
    status = await message.reply("Generating new thumbnail...")
    out_path = f"{d}/generated_{int(time.time())}.png"
    sample_paths, photo_paths = [], []
    try:
        for i, fid in enumerate(sample_ids):
            p = await client.download_media(fid, file_name=f"{d}/s_{i}.jpg")
            sample_paths.append(p)
        for i, fid in enumerate(photo_ids):
            p = await client.download_media(fid, file_name=f"{d}/p_{i}.jpg")
            photo_paths.append(p)

        await generate_thumbnail(sample_paths, photo_paths, st.get("prompt", ""), topic, out_path)
        await client.send_photo(chat_id, out_path, caption=f"New thumbnail: {topic}")
        await status.delete()
    except Exception as e:
        await status.edit(f"ERROR: {str(e)}")
    finally:
        for p in sample_paths + photo_paths:
            if os.path.isfile(p):
                os.remove(p)
        if os.path.isfile(out_path):
            os.remove(out_path)
