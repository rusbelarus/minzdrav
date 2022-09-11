import json
import re
import time

from api.session import proxies, Vaadin, Vsess, Session
from pydantic import BaseModel, Field
from log.logging import logger


class Response(BaseModel):
    error: list | str | None = Field(alias='globalErrors')
    url: str | None
    location: str | None = Field(alias='Location')
    cookie: str | None = Field(alias='Set-Cookie')
    uidl: str | None


async def get_vaadin(session: Session, iom_id: str, host: dict) -> Session | None:
    back_url = f'https://{host["host"]}/#/user-account/my-plan'
    SESSION = session.session
    METHOD = f'/api/api/educational-elements/iom/{iom_id}/open-link?backUrl={back_url}'
    HEADERS = {"Authorization": f"Bearer {session.token.access_token}"}
    try:
        req = SESSION.get(f"https://{host['host']}{METHOD}", headers=HEADERS, proxies=proxies).json()
        result = Response(**req)
        req = SESSION.get(url=result.url, proxies=proxies, allow_redirects=False)
        if req.status_code != 302:
            logger.warning(f'VAADIN\nVaadin session error')
            return None
        result = Response(**req.headers)
        req = SESSION.get(url=result.location, proxies=proxies, allow_redirects=False)
        if req.status_code != 302:
            logger.warning(f'VAADIN\nVaadin session error')
            return None
        result = Response(**req.headers)
        req = SESSION.get(url=result.location, proxies=proxies)
        if req.status_code != 200:
            logger.warning(f'VAADIN\nVaadin session error')
            return None
        CURR_TIME = round(time.time())
        HEADERS = {"Content-Type": "application/x-www-form-urlencoded", "Accept-Encoding": "gzip, deflate"}
        DATA = f"v-browserDetails=1&theme=halo&v-appId=ROOT-2521314&v-sh=1080&v-sw=1920&v-cw=1074&v-ch=968&v-curdate=" \
               f"{CURR_TIME}&v-tzo=-180&v-dstd=0&v-rtzo=-180&v-dston=false&v-vw=1074&v-vh=968&v-loc=https://" \
               f"{host['iom']}#!&v-wn=_system"
        req = SESSION.post(url=f"https://{host['iom']}/?v-{CURR_TIME}", headers=HEADERS, data=DATA, proxies=proxies).json()
        result = Response(**req)
        if result.uidl:
            VAADIN = Vaadin(**json.loads(result.uidl))
            return Session(**{'session': SESSION, 'token': session.token, 'vaadin': VAADIN, 'vsess': None})
        logger.warning(f'VAADIN\nVaadin session error')
        return None
    except Exception as exc:
        logger.critical(exc)
        return None


async def click_by_key(session: Session, host: dict, key: int, sync_id: int = 0, client_id: int = 0):
    SESSION = session.session
    VAADIN = session.vaadin
    VSESS = session.vsess
    if VSESS:
        sync_id = VSESS.sync_id + 1
    PAYLOAD = {
        "csrfToken": VAADIN.vaadin_key,
        "rpc": [
            [f"{key}", "com.vaadin.shared.ui.button.ButtonServerRpc", "click", [{
                "altKey": False, "button": "LEFT", "clientX": 247, "clientY": 229, "ctrlKey": False, "metaKey": False,
                "relativeX": 30, "relativeY": 18, "shiftKey": False, "type": 1}]]],
        "syncId": sync_id, "clientId": client_id}
    try:
        req = SESSION.post(f"https://{host['iom']}/UIDL/?v-uiId=0", data=json.dumps(PAYLOAD), proxies=proxies).text
        if req:
            data = re.findall(r"for\(;;\);\[(.*)]", req)[0]
            VSESS = Vsess(**json.loads(data))
            return Session(**{'session': SESSION, 'token': session.token, 'vaadin': VAADIN, 'vsess': VSESS})
        return False
    except Exception as exc:
        logger.critical(exc)
        return False


async def close(session: Session, host: dict, key: int, sync_id: int = 0, client_id: int = 0):
    SESSION = session.session
    VAADIN = session.vaadin
    VSESS = session.vsess
    if VSESS:
        sync_id = VSESS.sync_id + 1
        client_id = VSESS.client_id + 1
    PAYLOAD = {
        "csrfToken": VAADIN.vaadin_key,
        "rpc": [
            [f"{key}", "v", "v", ["close", ["b", True]]]],
        "syncId": sync_id, "clientId": client_id}
    try:
        req = SESSION.post(f"https://{host['iom']}/UIDL/?v-uiId=0", data=json.dumps(PAYLOAD), proxies=proxies).text
        if req:
            data = re.findall(r"for\(;;\);\[(.*)]", req)[0]
            VSESS = Vsess(**json.loads(data))
            return Session(**{'session': SESSION, 'token': session.token, 'vaadin': VAADIN, 'vsess': VSESS})
        return False
    except Exception as exc:
        logger.critical(exc)
        return False
