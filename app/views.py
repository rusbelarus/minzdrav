import aiohttp
import aiohttp_jinja2
import time

from aiohttp import web
from aiohttp_session import get_session, new_session
from multiprocessing import Process
from app.database import User, Iom, Setting, Status, Account
from app.bypass import run_bypass
from app.questions import run_parser

COOKIE_LIFETIME = 86400


async def redirect(request, root):
    location = request.app.router[root].url_for()
    raise aiohttp.web.HTTPFound(location)


async def is_authorized(request):
    session = await get_session(request)
    last_visit = session['last_visit'] if 'last_visit' in session else None
    if last_visit:
        if time.time() - session['last_visit'] > COOKIE_LIFETIME:
            session['last_visit'] = time.time()
            await redirect(request, root='login')
        else:
            session['last_visit'] = time.time()
            return True
    else:
        await redirect(request, root='login')


@aiohttp_jinja2.template('login.html')
async def do_login(request):
    data = await request.post()
    if 'username' in data:
        async with request.app['pool'].acquire() as conn:
            user = await User.get_user(conn, data['username'])
        if user:
            if user.password == data['password']:
                session = await new_session(request)
                session['last_visit'] = time.time()
                await redirect(request, root='index')
            else:
                return {"pass_error": {"username": data['username'], "error": 'неверный пароль'}}
        else:
            return {"login_error": 'нет такого пользователя'}


@aiohttp_jinja2.template('index.html')
async def index(request):
    auth = await is_authorized(request)
    if auth:
        data = await request.post()
        if 'bypass' in data:
            async with request.app['pool'].acquire() as conn:
                await Setting.update_bypass(conn, state=True)
            bypass = Process(target=run_bypass, args=())
            bypass.start()
            await redirect(request, root='index')
        if 'parse' in data:
            async with request.app['pool'].acquire() as conn:
                await Setting.update_parser(conn, state=True)
            parse = Process(target=run_parser, args=())
            parse.start()
            await redirect(request, root='index')
        if 'bot' in data:
            if data['bot'] == 'True':
                state = True
            else:
                state = False
            async with request.app['pool'].acquire() as conn:
                await Setting.update_bypass_info(conn, state=state)
            await redirect(request, root='index')
        response = dict()
        _done = 0
        async with request.app['pool'].acquire() as conn:
            ioms = await Iom.get_vo_ioms(conn)
        for iom in ioms:
            if iom.status == Status.DONE:
                _done += 1
        response.update({"vo": {"count": len(ioms), "done": _done}})
        _done = 0
        async with request.app['pool'].acquire() as conn:
            ioms = await Iom.get_spo_ioms(conn)
        for iom in ioms:
            if iom.status == Status.DONE:
                _done += 1
        response.update({"spo": {"count": len(ioms), "done": _done}})
        async with request.app['pool'].acquire() as conn:
            bypass = await Account.get_account(conn, status=Status.BYPASS)
            parser = await Account.get_account(conn, status=Status.PARSER)
            sett = await Setting.get_settings(conn)
        response.update(
            {
                "accounts": {
                    "bypass": bypass.login,
                    "bypass_on": sett.bypass,
                    "parser": parser.login,
                    "parser_on": sett.parse,
                    "info": sett.bypass_info}
            }
        )
        return response


@aiohttp_jinja2.template('vo.html')
async def vo(request):
    auth = await is_authorized(request)
    if auth:
        data = await request.post()
        response = dict()
        async with request.app['pool'].acquire() as conn:
            ioms = await Iom.get_vo_ioms(conn)
        response.update({'ioms': ioms})
        return response


@aiohttp_jinja2.template('spo.html')
async def spo(request):
    auth = await is_authorized(request)
    if auth:
        data = await request.post()
        response = dict()
        async with request.app['pool'].acquire() as conn:
            ioms = await Iom.get_spo_ioms(conn)
        response.update({'ioms': ioms})
        return response


@aiohttp_jinja2.template('settings.html')
async def settings(request):
    auth = await is_authorized(request)
    if auth:
        data = await request.post()
        response = dict()
        if data:
            async with request.app['pool'].acquire() as conn:
                await Setting.update_settings(conn, data)
            #raise redirect(request.app.router, 'settings')
        async with request.app['pool'].acquire() as conn:
            response.update({'settings': await Setting.get_settings(conn)})
        return response


'''@aiohttp_jinja2.template('upload.html')
async def upload(request):
    auth = await is_authorized(request)
    if auth:
        data = await request.post()
        response = dict()
        if 'channels' in data and len(data['channels']) > 0:
            usernames = await channels_parser(data['channels'])
            if usernames:
                channels = await get_channels(request, usernames)
                response.update({"channels": channels})
        return response


@aiohttp_jinja2.template('settings.html')
async def settings(request):
    auth = await is_authorized(request)
    if auth:
        data = await request.post()
        response = dict()
        if data:
            async with request.app['pool'].acquire() as conn:
                await Setting.update_settings(conn, data)
            raise redirect(request.app.router, 'settings')
        async with request.app['pool'].acquire() as conn:
            response.update({'settings': await Setting.get_settings(conn)})
        return response'''
