from api.vaadin import get_vaadin, click_by_key, close, Session
from pydantic import BaseModel, Field
from enum import Enum


class Variant(BaseModel):
    sync_id: int = Field(alias='syncId')
    client_id: int = Field(alias='clientId')


class VaadinActions(str, Enum):
    JUMP = "Быстрый переход"
    NEW_VARIANT = "Получить новый вариант"
    CLOSE = "Результат тестирования"
    BEFORE = ".1 Предварительное тестирование"
    FINALLY = ".1 Итоговое тестирование"
    SHOW = "Показать результат"
    WELCOME = "Добро пожаловать"


class Platform(str, Enum):
    PORTAL = "Платформа онлайн-обучения Портала"
    MEDX = "MedX PRO (сторонняя платформа онлайн-обучения)"


class State(BaseModel):
    key: int
    name: VaadinActions

    class Config:
        use_enum_values = True


async def get_vaadin_session(session: Session, iom_id: str, host: dict) -> Session | None | bool:
    session = await get_vaadin(session=session, iom_id=iom_id, host=host)
    if session:
        STATE = session.vaadin.state
        for key, value in STATE.items():
            if 'caption' in value.keys():
                if VaadinActions.CLOSE in value['caption']:
                    await close(session=session, host=host, key=key)
                    return False
        for key, value in STATE.items():
            if 'caption' in value.keys():
                if VaadinActions.NEW_VARIANT in value['caption']:
                    if 'styles' in value.keys():
                        continue
                    else:
                        session = await click_by_key(session=session, host=host, key=key)
                        return session
    return None
