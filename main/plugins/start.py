#Github.com/Vasusen-code

import os, asyncio
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from main.plugins.main import Bot

st = "Oii Buddy 🤡 __Send me Link of any message to clone it here, For private channel message, Send invite link first.__\n\nSUPPORT: @groupdcbots\nDEV: @selfiebd"

waiting_for_thumb = {}

@Bot.on_message(filters.private & filters.command("start"))
async def start(client, message):
    await message.reply(
        st,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("SET THUMB.", callback_data="sett"),
             InlineKeyboardButton("REM THUMB.", callback_data="remt")]
        ])
    )

@Bot.on_callback_query(filters.regex("^sett$"))
async def sett(client, callback_query):
    chat_id = callback_query.message.chat.id
    await callback_query.answer()
    await callback_query.message.delete()
    prompt = await client.send_message(chat_id, "Send me any image for thumbnail as a `reply` to this message. @groupdc")
    waiting_for_thumb[chat_id] = prompt.id

@Bot.on_callback_query(filters.regex("^remt$"))
async def remt(client, callback_query):
    chat_id = callback_query.message.chat.id
    await callback_query.answer()
    try:
        os.remove(f'{chat_id}.jpg')
        await callback_query.message.edit("Removed!")
    except Exception:
        await callback_query.message.edit("No thumbnail saved. @groupdcbots")

@Bot.on_message(filters.private & filters.photo & filters.create(lambda _, __, m: m.chat.id in waiting_for_thumb))
async def save_thumb(client, message):
    chat_id = message.chat.id
    waiting_for_thumb.pop(chat_id, None)
    status = await client.send_message(chat_id, "Trying.")
    path = await client.download_media(message)
    if os.path.exists(f'{chat_id}.jpg'):
        os.remove(f'{chat_id}.jpg')
    os.rename(path, f'./{chat_id}.jpg')
    await status.edit("Temporary thumbnail saved! @groupdcbots")
