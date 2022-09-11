import asyncio
import asyncpg
import json
import re
import time

from requests.exceptions import ConnectionError
from api.session import Host, Session, create_session
from api.parser import VaadinActions, Platform
from api.nmfo import include_in_plan
from api.vaadin import get_vaadin, click_by_key, close
from api.nmfo import get_completed_ioms
from api.iomqt import get_variants, get_questions, start_variant, save_answer, finish_variant, get_completed_variant
from app.database import Account, Iom, Status, Question, Answer, Setting
from log.logging import logger, DB_NAME, DB_USER, DB_PASS, DB_HOST, DB_PORT


async def is_closed(session: Session, iom_id: str, host) -> bool:
    STATE = session.vaadin.state
    for key, value in STATE.items():
        if 'caption' in value.keys():
            if VaadinActions.CLOSE in value['caption']:
                logger.info(f'VAADIN\n{iom_id} CLOSE session')
                await close(session, host=host, key=key)
                return False
    return True


async def is_before(session: Session) -> bool | None:
    STATE = session.vaadin.state
    for key, value in STATE.items():
        if 'caption' in value.keys():
            if VaadinActions.NEW_VARIANT in value['caption']:
                if 'styles' in value.keys():
                    return True
    for key, value in STATE.items():
        if 'caption' in value.keys():
            if VaadinActions.NEW_VARIANT in value['caption']:
                if 'styles' in value.keys():
                    continue
                else:
                    return False
    return None


async def run_variant(pool, qt_session: Session, iom_id: str, variant_id: str) -> int | None:
    answers_payloads = list()
    questions = await get_questions(session=qt_session, variant_id=variant_id, host=Host.QT_SPO)
    if questions is None:
        logger.warning(f'IOM\nIom - {iom_id} no questions')
        return None
    for question in questions:
        question = Question(**question)
        payloads = list()
        async with pool.acquire() as conn:
            _question = await Question.insert_question(conn, question=question)
        if _question is None:
            async with pool.acquire() as conn:
                _question = await Question.insert_question(conn, question=question)
        combination = sorted(json.loads(_question.combinations))
        combination = combination[0]
        _answers = sorted(json.loads(_question.answers))
        counter = 0
        for _answer in _answers:
            for answer in question.answers:
                answer = Answer(**answer)
                selected = False
                if answer.content == _answer:
                    if combination[counter] == 1:
                        selected = True
                    payloads.append({"id": answer.id, "selected": selected})
                    counter += 1
                    break
        answers_payloads.append({'raw': question.id, 'db': _question.id, 'data': payloads})

    is_start = await start_variant(session=qt_session, variant_id=variant_id, host=Host.QT_SPO)
    if is_start:
        for payload in answers_payloads:
            done = await save_answer(
                session=qt_session, variant_id=variant_id, payload=payload['data'], host=Host.QT_SPO)
            if done:
                continue
            else:
                logger.critical('ERROR')
        is_finish = await finish_variant(session=qt_session, variant_id=variant_id, host=Host.QT_SPO)
        if is_finish:
            completed = await get_completed_variant(session=qt_session, variant_id=variant_id, host=Host.QT_SPO)
            if completed:
                print(completed)
                for payload in answers_payloads:
                    for question in completed.questions:
                        question = Question(**question)
                        if question.id == payload['raw']:
                            async with pool.acquire() as conn:
                                if question.correct is True:
                                    await Question.update_question(conn, q_id=payload['db'], status=Status.DONE)
                                if question.correct is False:
                                    await Question.update_question(conn, q_id=payload['db'], status=Status.WAIT)
                grade = int(re.findall(r'оценка (\d)', completed.code)[0])
                return grade
    logger.warning(f'IOM\nIom - {iom_id} run error')
    return None


async def get_iom_variants(pool, iom: Iom, host) -> list | None:
    variant_ids = []
    async with pool.acquire() as conn:
        account = await Account.get_account(conn, status=Status.PARSER)
    session = await create_session(login=account.login, password=account.password, host=Host.IOM_SPO)
    if session is None:
        return None
    session = await get_vaadin(session=session, iom_id=iom.id, host=host)
    if session is None:
        return None
    closed = await is_closed(session, iom_id=iom.id, host=host)
    if closed:
        qt_session = await create_session(login=account.login, password=account.password, host=Host.QT_SPO)
        if qt_session is None:
            logger.warning('QT\nSession not created')
            return None
        numb_variants = re.findall(r'(Вариант №\d+ - не завершен )', str(session))
        variants = await get_variants(session=qt_session, host=Host.QT_SPO)
        print(variants)
        if variants is None:
            logger.warning(f'IOM\nIom - {iom.id} no new variants for {account.login}')
            return None
        for variant in variants:
            if variant.code in numb_variants:
                variant_ids.append(variant.id)
        if len(variant_ids) > 0:
            return variant_ids
        else:
            return None
    return None


async def parse_spo_questions(pool, account: Account, host: dict):
    async with pool.acquire() as conn:
        settings = await Setting.get_settings(conn)
    COUNTER = settings.variants

    async with pool.acquire() as conn:
        ioms = await Iom.get_spo_ioms(conn)
    for iom in ioms:
        async with pool.acquire() as conn:
            iom = await Iom.get_spo_iom(conn, iom_id=iom.id)
        if iom.status:
            if iom.status == Status.DONE or iom.status == Status.FAIL or iom.status == Status.MANUAL:
                continue
        if json.loads(iom.iomhost)['name'] not in Platform.PORTAL:
            async with pool.acquire() as conn:
                await Iom.set_spo_iom_status(conn, iom_id=iom.id, status=Status.MANUAL)
            continue
        logger.info(f'IOM\nIom {iom.id} in job')

        session = await create_session(login=account.login, password=account.password, host=Host.IOM_SPO)
        if session is None:
            return None

        completed = await get_completed_ioms(session=session, host=Host.IOM_SPO)
        if completed is False:
            logger.warning('NFMO\nSession not created')
            return None

        if iom.id in completed:
            session = await get_vaadin(session=session, iom_id=iom.id, host=host)
            if session is None:
                return False
            qt_session = await create_session(login=account.login, password=account.password, host=Host.QT_SPO)
            if qt_session is None:
                return False
            numb_variants = re.findall(r'(Вариант №\d+ - не завершен )', str(session))
            variants = await get_variants(session=qt_session, host=Host.QT_SPO)
            for variant in variants:
                if variant.code in numb_variants:
                    async with pool.acquire() as conn:
                        _iom = await Iom.get_spo_iom(conn, iom_id=iom.id)
                        GRADE = _iom.grade
                    if GRADE == 0:
                        async with pool.acquire() as conn:
                            await Iom.set_spo_iom_status(conn, iom_id=iom.id, status=Status.DONE)
                        logger.info(f'IOM\n{iom.id} parsing DONE')
                        break
                    grade = await run_variant(pool, qt_session=qt_session, iom_id=iom.id, variant_id=variant.id)
                    if grade:
                        if int(grade) == 5:
                            GRADE -= 1
                            async with pool.acquire() as conn:
                                await Iom.set_spo_iom_grade(conn, iom_id=iom.id, grade=GRADE)
                        else:
                            async with pool.acquire() as conn:
                                await Iom.set_spo_iom_grade(conn, iom_id=iom.id, grade=settings.grade)
            async with pool.acquire() as conn:
                await Iom.set_spo_iom_status(conn, iom_id=iom.id, status=Status.FAIL)
            logger.info(f'IOM\n{iom.id} parsing FAIL')

        else:
            included = await include_in_plan(session=session, iom_id=iom.id, host=host)
            if included is False:
                logger.warning(f'IOM\nIom - {iom.id} not included for {account.login}')
                return False

            async with pool.acquire() as conn:
                await Iom.set_spo_iom_status(conn, iom_id=iom.id, status=Status.WAIT)

            session = await get_vaadin(session=session, iom_id=iom.id, host=host)
            if session is None:
                return False
            closed = await is_closed(session, iom_id=iom.id, host=host)
            if closed:
                before = await is_before(session)
                if before is None:
                    print(before)

                elif before:
                    print(before)
                    numb_variants = re.findall(r'(Вариант №\d+ - не завершен )', str(session))
                    if len(numb_variants) > 0:
                        qt_sess = await create_session(login=account.login, password=account.password, host=Host.QT_SPO)
                        if qt_sess is None:
                            logger.warning('QT\nSession not created')
                            return False
                        variants = await get_variants(session=qt_sess, host=Host.QT_SPO)
                        if variants is None:
                            logger.warning(f'IOM\nIom - {iom.id} no new variants for {account.login}')
                            return False
                        for variant in variants:
                            if variant.code in numb_variants:
                                await run_variant(pool, qt_session=qt_sess, iom_id=iom.id, variant_id=variant.id)
                        return False

                    else:
                        for key, value in session.vaadin.state.items():
                            if 'caption' in value.keys():
                                if VaadinActions.NEW_VARIANT in value['caption']:
                                    if 'styles' in value.keys():
                                        continue
                                    else:
                                        await click_by_key(session, host, key=key, client_id=session.vaadin.client_id)
                                        return False
                        return False
                else:
                    print(before)
                    '''variant_ids = await get_iom_variants(pool, iom=iom, host=host)
                    print(variant_ids)
                    sys.exit()'''
            #return False


@logger.catch
async def parse_questions():
    pool = await asyncpg.create_pool(
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT)
    async with pool.acquire() as conn:
        account = await Account.get_account(conn, status=Status.PARSER)
    while account:
        start_time = round(time.time())
        logger.info(f"PARSER\n{account.login} parser start")
        #VO = asyncio.create_task(parse_vo_questions(pool=pool, account=account, host=Host.IOM_VO))
        SPO = asyncio.create_task(parse_spo_questions(pool=pool, account=account, host=Host.IOM_SPO))
        try:
            await asyncio.gather(SPO)
        except ConnectionError as exc:
            logger.critical(exc)
        except Exception as exc:
            logger.critical(exc)
        finally:
            async with pool.acquire() as conn:
                account = await Account.get_account(conn, status=Status.PARSER)
        logger.info(f"PARSER\n{account.login} parser finish in {round(time.time()) - start_time} sec")
    logger.critical("PARSER\n no parser account found")


def run_parser():
    asyncio.run(parse_questions())
