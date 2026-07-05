import glob
import os
import asyncio
from pathlib import Path
from main.utils import load_plugins
import logging
from aiohttp import web
from . import bot

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


async def _start_pyrogram_clients():
    from main.plugins.main import start_clients
    await start_clients()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_run_web_server())
    loop.run_until_complete(_start_pyrogram_clients())
    bot.run_until_disconnected()

