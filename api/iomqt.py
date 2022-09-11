import json

from pydantic import BaseModel, Field
from log.logging import logger
from api.session import proxies, Session


class Variant(BaseModel):
    id: str
    code: str
    start: int | None = Field(alias='startTime')
    end: int | None = Field(alias='endTime')
    finish: str | None = Field(alias='finishTime')
    questions: list | None

    class Config:
        allow_population_by_field_name = True


async def get_variants(session: Session, host: dict) -> list | None:
    METHOD = f'/api/rest/quiz/variants'
    HEADERS = {"accept": "application/json", "authorization": f"Bearer {session.token.access_token}"}
    SESSION = session.session
    try:
        req = SESSION.get(f"https://{host['host']}{METHOD}", headers=HEADERS, proxies=proxies).json()
        if len(req) > 0:
            return [Variant(**variant) for variant in req]
        else:
            return None
    except Exception as exc:
        logger.critical(exc)
        return None


async def get_questions(session: Session, variant_id: str, host: dict):
    METHOD = f'/api/rest/quiz/variant/{variant_id}'
    HEADERS = {"accept": "application/json", "authorization": f"Bearer {session.token.access_token}"}
    SESSION = session.session
    try:
        req = SESSION.get(f"https://{host['host']}{METHOD}", headers=HEADERS, proxies=proxies).json()
        if req['questions']:
            return req['questions']
    except Exception as exc:
        logger.critical(exc)
        return None


async def start_variant(session: Session, variant_id: str, host: dict) -> bool:
    METHOD = f'/api/rest/quiz/variant/{variant_id}/start'
    HEADERS = {"accept": "application/json", "authorization": f"Bearer {session.token.access_token}"}
    SESSION = session.session
    try:
        req = SESSION.post(f"https://{host['host']}{METHOD}", headers=HEADERS, proxies=proxies).json()
        Variant(**req)
        return True
    except Exception as exc:
        logger.critical(exc)
        return False


async def finish_variant(session: Session, variant_id: str, host: dict) -> bool:
    METHOD = f'/api/rest/quiz/variant/{variant_id}/finish'
    HEADERS = {"accept": "application/json", "authorization": f"Bearer {session.token.access_token}"}
    SESSION = session.session
    try:
        req = SESSION.post(f"https://{host['host']}{METHOD}", headers=HEADERS, proxies=proxies)
        if req.status_code == 200:
            return True
        return False
    except Exception as exc:
        logger.critical(exc)
        return False


async def save_answer(session: Session, variant_id: str, payload: list, host: dict) -> bool:
    METHOD = f'/api/rest/quiz/variant/{variant_id}/save-answer'
    HEADERS = {
        "accept": "application/json",
        "authorization": f"Bearer {session.token.access_token}",
        "content-type": "application/json"}
    SESSION = session.session
    try:
        req = SESSION.post(f"https://{host['host']}{METHOD}", headers=HEADERS, data=json.dumps(payload), proxies=proxies)
        if req.status_code == 200:
            return True
        return False
    except Exception as exc:
        logger.critical(exc)
        return False


async def get_completed_variant(session: Session, variant_id: str, host: dict):
    METHOD = f'/api/rest/quiz/variant/{variant_id}'
    HEADERS = {
        "accept": "application/json",
        "authorization": f"Bearer {session.token.access_token}",
        "content-type": "application/json"}
    SESSION = session.session
    try:
        req = SESSION.get(f"https://{host['host']}{METHOD}", headers=HEADERS, proxies=proxies).json()
        return Variant(**req)
    except Exception as exc:
        logger.critical(exc)
        return None
