import asyncio
import asyncpg
import time

from aiogram import Bot
from requests.exceptions import ConnectionError
from app.database import Account, Iom, Status, Setting
from api.session import Host, Session, create_session
from api.nmfo import get_programs, get_ioms_by_program_id, get_iom
from log.logging import logger, DB_NAME, DB_USER, DB_PASS, DB_HOST, DB_PORT
from enum import Enum


class IomKind(str, Enum):
    TRAINING = 'Тренинг'
    INTERACTIVE = 'Интерактивная ситуационная задача'


async def send_notification(iom: Iom, sett: Setting, host: dict):
    speciality = [spec.strip() for spec in iom.additionalspecialities.split(',') if len(spec) > 3]
    if iom.specialityname:
        speciality.append(iom.specialityname.strip())
    speciality.sort()
    if len(speciality) == 1:
        sorted_spec_txt = f"{speciality[0]}."
    else:
        sorted_spec_txt = ""
        for spec in speciality:
            if spec == speciality[-1]:
                sorted_spec_txt += f"{spec}."
            else:
                sorted_spec_txt += f"{spec}, "
    text = f"*iom:* {host['host']}\n" \
           f"*zet:* {iom.zet}\n" \
           f"*start date:* {iom.startdate}\n" \
           f"*end date:* {iom.enddate}\n" \
           f"*name:* _{iom.name}_\n" \
           f"*speciality:* _{sorted_spec_txt}_\n" \
           f"*iom host:* {iom.iomhost['name']}\n" \
           f"*type:* _{iom.iomkind}_"
    try:
        bot = Bot(token=sett.bot_token)
        await bot.send_message(chat_id=sett.my_group, text=text, parse_mode="Markdown")
    except Exception as exc:
        logger.critical(exc)


async def control_vo_ioms(pool, session: Session, iom_id: str, host: dict):
    iom = await get_iom(session, iom_id=iom_id, host=host)
    if iom:
        async with pool.acquire() as conn:
            sett = await Setting.get_settings(conn)
            await Iom.insert_vo_iom(conn, iom=iom, grade=sett.grade)
        if sett.bypass_info:
            asyncio.create_task(send_notification(iom=iom, sett=sett, host=host))
        if IomKind.TRAINING in iom.iomkind or IomKind.INTERACTIVE in iom.iomkind:
            async with pool.acquire() as conn:
                await Iom.set_vo_iom_status(conn, iom_id=iom_id, status=Status.MANUAL)


async def control_spo_ioms(pool, session: Session, iom_id: str, host: dict):
    iom = await get_iom(session, iom_id=iom_id, host=host)
    if iom:
        if iom:
            async with pool.acquire() as conn:
                sett = await Setting.get_settings(conn)
                await Iom.insert_spo_iom(conn, iom=iom, grade=sett.grade)
            if sett.bypass_info:
                asyncio.create_task(send_notification(iom=iom, sett=sett, host=host))
            if IomKind.TRAINING in iom.iomkind or IomKind.INTERACTIVE in iom.iomkind:
                async with pool.acquire() as conn:
                    await Iom.set_spo_iom_status(conn, iom_id=iom_id, status=Status.MANUAL)


async def vo_bypass(pool, account: Account, host: dict):
    session = await create_session(login=account.login, password=account.password, host=host)
    if session:
        programs = await get_programs(session, host=host)
        if programs:
            async with pool.acquire() as conn:
                _ioms = await Iom.get_vo_iom_ids(conn)
            for program in programs:
                tasks = []
                for zet in range(16):
                    if zet == 0:
                        continue
                    ioms = await get_ioms_by_program_id(session, host=host, program_id=program.programId, zet=zet)
                    if ioms:
                        for iom_id in ioms:
                            if iom_id in _ioms:
                                continue
                            task = asyncio.create_task(control_vo_ioms(pool, session, iom_id=iom_id, host=host))
                            tasks.append(task)
                await asyncio.gather(*tasks)


async def spo_bypass(pool, account: Account, host: dict):
    session = await create_session(login=account.login, password=account.password, host=host)
    if session:
        programs = await get_programs(session, host=host)
        if programs:
            async with pool.acquire() as conn:
                _ioms = await Iom.get_spo_iom_ids(conn)
            for program in programs:
                tasks = []
                for zet in range(16):
                    if zet == 0:
                        continue
                    ioms = await get_ioms_by_program_id(session, host=host, program_id=program.programId, zet=zet)
                    if ioms:
                        for iom_id in ioms:
                            if iom_id in _ioms:
                                continue
                            task = asyncio.create_task(control_spo_ioms(pool, session, iom_id=iom_id, host=host))
                            tasks.append(task)
                await asyncio.gather(*tasks)


@logger.catch
async def bypass():
    pool = await asyncpg.create_pool(
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT)
    async with pool.acquire() as conn:
        account = await Account.get_account(conn, status=Status.BYPASS)
    while account:
        start_time = round(time.time())
        logger.info(f"BYPASS\n{account.login} bypass start")
        VO = asyncio.create_task(vo_bypass(pool, account=account, host=Host.IOM_VO))
        SPO = asyncio.create_task(spo_bypass(pool, account=account, host=Host.IOM_SPO))
        try:
            await asyncio.gather(VO, SPO)
        except ConnectionError as exc:
            logger.critical(exc)
        except Exception as exc:
            logger.critical(exc)
        finally:
            async with pool.acquire() as conn:
                account = await Account.get_account(conn, status=Status.BYPASS)
        logger.info(f"BYPASS\n{account.login} bypass finish in {round(time.time())-start_time} sec")
    logger.critical("BYPASS\n no bypass account found")


def run_bypass():
    asyncio.run(bypass())
