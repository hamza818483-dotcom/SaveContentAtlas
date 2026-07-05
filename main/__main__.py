import glob
import os
import asyncio
from pathlib import Path
from main.utils import load_plugins
import logging
from aiohttp import web

logging.basicConfig(format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s',
                    level=logging.WARNING)

path = "main/plugins/*.py"
files = glob.glob(path)
for name in files:
    with open(name) as a:
        patt = Path(a.name)
        plugin_name = patt.stem
        load_plugins(plugin_name.replace(".py", ""))

print("Successfully deployed!")

from main.plugins.main import Bot, userbot, start_clients


async def _health(request):
    return web.Response(text="OK")


async def _run_web_server():
    port = int(os.environ.get("PORT", "10000"))
    app = web.Application()
    app.router.add_get("/", _health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()


async def main():
    await _run_web_server()
    await start_clients()
    from pyrogram import idle
    await idle()


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
