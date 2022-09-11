#!/usr/bin/python3.10
# -*- coding: utf-8 -*-

import aiogram
import asyncpg
import sys
import aiohttp_jinja2
import jinja2
import base64

from aiohttp import web
from aiohttp_session import setup
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from cryptography import fernet
from app.routes import setup_routes
from app.middlewares import setup_middlewares
from app.database import database_init, Setting
from log.logging import BOT_TOKEN, DB_NAME, DB_USER, DB_PASS, DB_HOST, DB_PORT


async def init_app():
    app = web.Application()

    app['pool'] = await asyncpg.create_pool(
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT)

    create_db = await database_init(app)
    if create_db is False:
        sys.exit()

    async with app['pool'].acquire() as conn:
        await Setting.update_bypass(conn, state=False)
        await Setting.update_parser(conn, state=False)

    app['bot'] = aiogram.Bot(token=BOT_TOKEN)
    fernet_key = fernet.Fernet.generate_key()
    secret_key = base64.urlsafe_b64decode(fernet_key)
    setup(app, EncryptedCookieStorage(secret_key))
    aiohttp_jinja2.setup(app, loader=jinja2.PackageLoader('app', 'templates'))
    setup_routes(app)
    setup_middlewares(app)
    return app


if __name__ == "__main__":
    web.run_app(init_app(), handle_signals=False)
