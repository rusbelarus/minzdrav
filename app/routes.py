import pathlib

from app.views import do_login, index, vo, spo, settings

PROJECT_ROOT = pathlib.Path(__file__).parent


def setup_routes(app):
    app.router.add_get('/', index, name='index')
    app.router.add_post('/', index, name='index')
    app.router.add_get('/vo', vo, name='vo')
    app.router.add_post('/vo', vo, name='vo')
    app.router.add_get('/spo', spo, name='spo')
    app.router.add_post('/spo', spo, name='spo')
    app.router.add_get('/login', do_login, name='login')
    app.router.add_post('/login', do_login, name='login')
    app.router.add_get('/settings', settings, name='settings')
    app.router.add_post('/settings', settings, name='settings')
    # app.router.add_get('/upload', upload, name='upload')
    # app.router.add_post('/upload', upload, name='upload')
    setup_static_routes(app)


def setup_static_routes(app):
    app.router.add_static('/static/', path=PROJECT_ROOT / 'static', name='static')
