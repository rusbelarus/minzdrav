import json

from api.session import proxies, Session
from app.database import Iom
from pydantic import BaseModel
from log.logging import logger


class Program(BaseModel):
    programId: str
    programName: str
    specialityName: str


async def include_in_plan(session: Session, iom_id: str, host: dict) -> bool:
    METHOD = f'/api/api/educational-elements/iom/{iom_id}/plan'
    HEADERS = {"Accept": "application/json", "Authorization": f"Bearer {session.token.access_token}"}
    SESSION = session.session
    try:
        req = SESSION.put(f"https://{host['host']}{METHOD}", headers=HEADERS, proxies=proxies)
        if req.status_code == 200:
            METHOD = f'/api/api/educational-elements/iom/{iom_id}'
            req = SESSION.get(f"https://{host['host']}{METHOD}", headers=HEADERS, proxies=proxies).json()
            if req['includedToPlan']:
                return True
        return False
    except Exception as exc:
        logger.critical(exc)
        return False


async def exclude_from_plan(session: Session, iom_id: str, host: dict) -> bool:
    METHOD = f'/api/api/educational-elements/application-order-delete/confirm'
    HEADERS = {
        "Accept": "application/json",
        "Authorization": f"Bearer {session.token.access_token}",
        "Content-type": "application/json"}
    SESSION = session.session
    PAYLOAD = {"elementId": iom_id, "trainingCycleId": None, "personCyclesList": []}
    try:
        req = SESSION.post(f"https://{host['host']}{METHOD}", headers=HEADERS, data=json.dumps(PAYLOAD), proxies=proxies).json()
        if req['code'] == 0:
            return True
        return False
    except Exception as exc:
        logger.critical(exc)
        return False


async def get_programs(session: Session, host: dict) -> list | bool:
    METHOD = '/api/api/profile/programs/all'
    HEADERS = {"Accept": "application/json", "Authorization": f"Bearer {session.token.access_token}"}
    SESSION = session.session
    try:
        req = SESSION.get(f"https://{host['host']}{METHOD}", headers=HEADERS, proxies=proxies).json()
        if len(req) > 0:
            programs = [Program(**program) for program in req]
            return programs
        return False
    except Exception as exc:
        logger.critical(exc)
        return False


async def get_iom(session: Session, iom_id: str,  host: dict) -> Iom | bool:
    METHOD = '/api/api/educational-elements/iom/'
    HEADERS = {"accept": "application/json", "authorization": f"Bearer {session.token.access_token}"}
    SESSION = session.session
    try:
        req = SESSION.get(f"https://{host['host']}{METHOD}{iom_id}", headers=HEADERS, proxies=proxies).json()
        if len(req) > 0:
            iom = Iom(**req)
            return iom
        return False
    except Exception as exc:
        logger.critical(exc)
        return False


async def get_completed_ioms(session: Session, host: dict) -> list | bool:
    METHOD = '/api/api/profile/my-plan/extra-elements?completed=true'
    HEADERS = {"accept": "application/json", "authorization": f"Bearer {session.token.access_token}"}
    SESSION = session.session
    try:
        req = SESSION.get(f"https://{host['host']}{METHOD}", headers=HEADERS, proxies=proxies).json()
        if len(req) > 0:
            variants = [iom['id'] for iom in req]
            return variants
        return False
    except Exception as exc:
        logger.critical(exc)
        return False


async def get_ioms_by_program_id(session: Session, program_id: str, zet: int, host: dict) -> list | None:
    LIMIT = 50
    OFFSET = 0
    IOMS = []

    METHOD = '/api/api/educational-elements/search'
    HEADERS = {
        "Accept": "application/json",
        "Authorization": f"Bearer {session.token.access_token}",
        "content-type": "application/json"}
    SESSION = session.session
    PAYLOAD = {
        "limit": LIMIT,
        "programId": [program_id],
        "elementType": "iom",
        "offset": OFFSET,
        "startDate": None,
        "endDate": None,
        "zetMin": zet,
        "zetMax": zet}
    try:
        req = SESSION.post(f"https://{host['host']}{METHOD}", headers=HEADERS, data=json.dumps(PAYLOAD), proxies=proxies).json()
        if len(req['elements']) > 0:
            IOMS.extend([iom['elementId'] for iom in req['elements']])
            while len(req['elements']) == LIMIT:
                OFFSET = OFFSET + LIMIT
                PAYLOAD = {
                    "limit": LIMIT,
                    "programId": [program_id],
                    "elementType": "iom",
                    "offset": OFFSET,
                    "startDate": None,
                    "endDate": None,
                    "zetMin": zet,
                    "zetMax": zet}
                req = SESSION.post(f"https://{host['host']}{METHOD}", headers=HEADERS, data=json.dumps(PAYLOAD), proxies=proxies).json()
                if len(req['elements']) > 0:
                    IOMS.extend([iom['elementId'] for iom in req['elements']])
            return IOMS
        else:
            return None
    except Exception as exc:
        logger.critical(exc)
        return None
