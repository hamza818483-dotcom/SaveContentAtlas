#Github.com/Vasusen-code

from pyrogram import Client
from pyrogram.errors import FloodWait, BadRequest

import asyncio, subprocess, re, os, time

def get_youtube_id(text):
    m = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)([A-Za-z0-9_-]{11})', text)
    return m.group(1) if m else None

async def download_youtube_thumbnail(url, sender):
    out_tmpl = f'ytthumb_{sender}_{int(time.time())}'
    cmd = [
        'yt-dlp', '--skip-download', '--write-thumbnail',
        '--convert-thumbnails', 'jpg',
        '-o', f'{out_tmpl}.%(ext)s',
        '--no-playlist',
        '--remote-components', 'ejs:github',
    ]
    cookies_path = os.getenv('YT_COOKIES_PATH', 'cookies.txt')
    cookies_content = os.getenv('YT_COOKIES_CONTENT')
    if cookies_content and not os.path.isfile(cookies_path):
        with open(cookies_path, 'w') as f:
            f.write(cookies_content)
    if os.path.isfile(cookies_path):
        cmd += ['--cookies', cookies_path]
    cmd.append(url)
    process = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    await process.communicate()
    for ext in ('jpg', 'webp', 'png'):
        p = f'{out_tmpl}.{ext}'
        if os.path.isfile(p):
            return p
    return None

async def download_youtube(url, sender, status_message=None):
    out_path = f'yt_{sender}_{int(time.time())}.mp4'
    cmd = [
        'yt-dlp', '-f', 'best[ext=mp4]/best', '-o', out_path,
        '--no-playlist',
        '--remote-components', 'ejs:github',
        '--newline',
        '--progress-template', 'download:%(progress._percent_str)s|%(progress._eta_str)s|%(progress._speed_str)s',
    ]
    cookies_path = os.getenv('YT_COOKIES_PATH', 'cookies.txt')
    cookies_content = os.getenv('YT_COOKIES_CONTENT')
    if cookies_content and not os.path.isfile(cookies_path):
        with open(cookies_path, 'w') as f:
            f.write(cookies_content)
    if os.path.isfile(cookies_path):
        cmd += ['--cookies', cookies_path]
    cmd.append(url)
    process = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)

    last_update = 0
    stderr_lines = []

    async def _read_progress():
        nonlocal last_update
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            text = line.decode(errors="ignore").strip()
            if status_message and "|" in text and time.time() - last_update >= 3:
                try:
                    pct, eta, speed = text.split("|")
                    await status_message.edit(
                        f"**Downloading YouTube video...**\n\n{pct.strip()} | ETA: {eta.strip()} | {speed.strip()}"
                    )
                    last_update = time.time()
                except Exception:
                    pass

    async def _read_stderr():
        while True:
            line = await process.stderr.readline()
            if not line:
                break
            stderr_lines.append(line.decode(errors="ignore"))

    await asyncio.gather(_read_progress(), _read_stderr())
    await process.wait()

    if process.returncode != 0:
        raise Exception(f"yt-dlp failed: {''.join(stderr_lines).strip()[-300:]}")
    if os.path.isfile(out_path):
        return out_path
    matches = [f for f in os.listdir('.') if f.startswith(f'yt_{sender}_')]
    return matches[0] if matches else None

#Join private chat-------------------------------------------------------------------------------------------------------------

async def join(client, invite_link):
    try:
        await client.join_chat(invite_link)
        return "Successfully joined the Channel🚀"
    except BadRequest as e:
        return f"Could not join: {str(e)}"
    except FloodWait:
        return "Too many requests, try again later 🚧."
    except Exception as e:
        return f"{str(e)}"
           
#Regex---------------------------------------------------------------------------------------------------------------
#to get the url from event

def get_link(string):
    regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
    url = re.findall(regex,string)   
    try:
        link = [x[0] for x in url][0]
        if link:
            return link
        else:
            return False
    except Exception:
        return False
    
#Screenshot---------------------------------------------------------------------------------------------------------------

async def screenshot(video, time_stamp, sender):
    if os.path.isfile(f'{sender}.jpg'):
        return f'{sender}.jpg'
    out = str(video).split(".")[0] + ".jpg"
    cmd = (f"ffmpeg -ss {time_stamp} -i {video} -vframes 1 {out}").split(" ")
    process = await asyncio.create_subprocess_exec(
         *cmd,
         stdout=asyncio.subprocess.PIPE,
         stderr=asyncio.subprocess.PIPE)
        
    stdout, stderr = await process.communicate()
    x = stderr.decode().strip()
    y = stdout.decode().strip()
    print(x)
    print(y)
    if os.path.isfile(out):
        return out
    else:
        None
        
