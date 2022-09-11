import json
import requests
import re

from pydantic import BaseModel, Field
from enum import Enum
from log.logging import logger


proxies = {"http": "socks5://127.0.0.1:9050", "https": "socks5://127.0.0.1:9050"}


class Token(BaseModel):
    access_token: str | None
    token_type: str | None
    refresh_token: str | None
    expires_in: int | None
    scope: str | None
    idp_session_id: str | None


class Vaadin(BaseModel):
    vaadin_key: str = Field(alias='Vaadin-Security-Key')
    vaadin_push: str = Field(alias='Vaadin-Push-ID')
    sync_id: int = Field(alias='syncId')
    resynchronize: bool
    client_id: int = Field(alias='clientId')
    changes: list
    state: dict
    rpc: list


class Vsess(BaseModel):
    sync_id: int | None = Field(alias='syncId')
    client_id: int | None = Field(alias='clientId')
    state: dict | None


class Session(BaseModel):
    token: Token
    session: requests.sessions.Session
    vaadin: Vaadin | None
    vsess: Vsess | None

    class Config:
        arbitrary_types_allowed = True


class Idp(BaseModel):
    error: str | None = Field(alias='errorCode')
    url: str | None = Field(alias='serviceProviderUrl')


class Response(BaseModel):
    error: list | str | None = Field(alias='globalErrors')
    url: str | None
    location: str | None = Field(alias='Location')
    cookie: str | None = Field(alias='Set-Cookie')
    uidl: str | None


class Host(dict, Enum):
    IOM_VO = {
        "host": "nmfo-vo.edu.rosminzdrav.ru",
        "api": "/api/api/v2/idp/token",
        "iom": "iom-vo.edu.rosminzdrav.ru",
        "login": "a.edu.rosminzdrav.ru"}
    IOM_SPO = {
        "host": "nmfo-spo.edu.rosminzdrav.ru",
        "api": "/api/api/v2/idp/token",
        "iom": "iom-spo.edu.rosminzdrav.ru",
        "login": "a.edu.rosminzdrav.ru"}
    QT_VO = {
        "host": "iomqt-vo.edu.rosminzdrav.ru",
        "iom": "iom-vo.edu.rosminzdrav.ru",
        "api": "/api/rest/v2/idp/token",
        "login": "a.edu.rosminzdrav.ru"}
    QT_SPO = {
        "host": "iomqt-spo.edu.rosminzdrav.ru",
        "iom": "iom-spo.edu.rosminzdrav.ru",
        "api": "/api/rest/v2/idp/token",
        "login": "a.edu.rosminzdrav.ru"}


async def create_session(login: str, password: str, host: dict) -> Session | None:
    METHOD = '/idp/auth?type=custom'
    PAYLOAD = {
        "username": login,
        "usernameEmail": "",
        "password": password,
        "serviceProviderUrl": f"https://{host['host']}/auth/",
        "responseType": "server-ticket",
        "locale": None,
        "useAccessibe": False,
        "accessibleMode": "WHITE"}
    HEADERS = {'content-type': 'application/json; charset=UTF-8'}
    try:
        SESSION = requests.Session()
        req = SESSION.post(f"https://{host['login']}{METHOD}", headers=HEADERS, data=json.dumps(PAYLOAD), proxies=proxies).json()
        idp = Idp(**req)
        HEADERS = {'content-type': 'application/x-www-form-urlencoded', 'authorization': 'Basic Y2xpZW50OnNlY3JldA=='}
        if idp.url:
            idp = re.findall(r"(idp_ticket=.*)", idp.url)[0]
            req = SESSION.post(f"https://{host['host']}{host['api']}", headers=HEADERS, data=idp, proxies=proxies).json()
            return Session(**{'token': Token(**req), 'session': SESSION})
        elif idp.error:
            logger.warning(f"Get Token: {idp.error}\n{login} {password} {host}")
        logger.warning(f'{host}\n{login} session not created')
        return None
    except Exception as exc:
        logger.critical(exc)
        return None
