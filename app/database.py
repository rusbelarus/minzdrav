import asyncpg
import json
import collections

from itertools import combinations_with_replacement
from log.logging import (
    logger, parser, DB_NAME, ADMIN_LOG, ADMIN_PAS, BYPASS_LOG, BYPASS_PAS, PARSER_LOG, PARSER_PAS,
    BOT_TOKEN, MY_GROUP, BYPASS_SlEEP, VARIANTS, GRADE)
from pydantic import BaseModel, Field
from enum import Enum
from log.logging import DSN


class Status(str, Enum):
    WAIT = 'wait'
    DONE = 'done'
    FAIL = 'fail'
    MANUAL = 'manual'
    CONTINUE = 'continue'
    ADMIN = 'admin'
    BYPASS = 'bypass'
    PARSER = 'parser'


class Table(str, Enum):
    USERS = 'users'
    ACCOUNTS = 'accounts'
    VO_IOMS = 'vo_ioms'
    SPO_IOMS = 'spo_ioms'
    QUESTIONS = 'questions'
    SETTINGS = 'settings'


async def delete_table(table: Table):
    conn = await asyncpg.connect(dsn=DSN)
    await conn.execute(
        f"""
        DROP TABLE IF EXISTS {table}
        """
    )
    await conn.close()


async def database_init(app: object()) -> bool:
    try:
        async with app['pool'].acquire() as conn:
            await User.create_table(conn)
            logger.info(f"DATABASE {DB_NAME}:\nTable {Table.USERS} created")
            await User.insert_user(conn, login=ADMIN_LOG, password=ADMIN_PAS, status=Status.ADMIN)
            logger.info(f"DATABASE {DB_NAME}:\nTable {Table.USERS} added {ADMIN_LOG} as {Status.ADMIN}")
            await Account.create_table(conn)
            logger.info(f"DATABASE {DB_NAME}:\nTable {Table.ACCOUNTS} created")
            await Account.insert_account(conn, login=BYPASS_LOG, password=BYPASS_PAS, status=Status.BYPASS)
            logger.info(f"DATABASE {DB_NAME}:\nTable {Table.ACCOUNTS} add {BYPASS_LOG} as {Status.BYPASS}")
            await Account.insert_account(conn, login=PARSER_LOG, password=PARSER_PAS, status=Status.PARSER)
            logger.info(f"DATABASE {DB_NAME}:\nTable {Table.ACCOUNTS} add {PARSER_LOG} as {Status.PARSER}")
            await Iom.create_table_vo_ioms(conn)
            logger.info(f"DATABASE {DB_NAME}:\nTable {Table.VO_IOMS} created")
            await Iom.create_table_spo_ioms(conn)
            logger.info(f"DATABASE {DB_NAME}:\nTable {Table.SPO_IOMS} created")
            await Question.create_table(conn)
            logger.info(f"DATABASE {DB_NAME}:\nTable {Table.QUESTIONS} created")
            await Setting.create_table(conn)
            logger.info(f"DATABASE {DB_NAME}:\nTable {Table.SETTINGS} created")
        parser["database"]["not_created"] = "False"
        with open("config.ini", "w") as configfile:
            parser.write(configfile)
        return True
    except Exception as exc:
        logger.critical(f"DATABASE {DB_NAME}:\n{exc}")
        return False


class User(BaseModel):
    login: str
    password: str
    status: str

    @staticmethod
    async def create_table(conn):
        await conn.execute(
            f"""CREATE TABLE IF NOT EXISTS {Table.USERS}
            (LOGIN TEXT PRIMARY KEY, PASSWORD TEXT NOT NULL, STATUS TEXT NOT NULL)""")

    @staticmethod
    async def insert_user(conn, login: str, password: str, status: str):
        await conn.execute(f"""INSERT INTO {Table.USERS}
            (LOGIN, PASSWORD, STATUS) VALUES ($1, $2, $3) ON CONFLICT (LOGIN) DO NOTHING""", login, password, status)

    @staticmethod
    async def get_user(conn, username: str):
        user = await conn.fetchrow(f"""SELECT * FROM {Table.USERS} WHERE LOGIN = $1""", username)
        return User(**user) if user else None


class Account(BaseModel):
    login: str
    password: str
    status: str

    @staticmethod
    async def create_table(conn):
        await conn.execute(f"""CREATE TABLE IF NOT EXISTS {Table.ACCOUNTS}
        (LOGIN TEXT PRIMARY KEY, PASSWORD TEXT NOT NULL, STATUS TEXT NOT NULL)""")

    @staticmethod
    async def insert_account(conn, login: str, password: str, status: str):
        await conn.execute(f"""INSERT INTO {Table.ACCOUNTS} (LOGIN, PASSWORD, STATUS) 
        VALUES ($1, $2, $3) ON CONFLICT (LOGIN) DO NOTHING""", login, password, status)

    @staticmethod
    async def get_account(conn, status: str):
        record = await conn.fetchrow(f"""SELECT * FROM {Table.ACCOUNTS} WHERE STATUS = $1""", status)
        if record:
            account = Account(**record)
            return account
        return None


class Iom(BaseModel):
    id: str
    name: str
    zet: int
    startdate: str | None = Field(alias='startDate')
    enddate: str | None = Field(alias='endDate')
    iomhost: dict | str | None = Field(alias='iomHost')
    iomkind: str | None = Field(alias='iomKind')
    specialityname: str | None = Field(alias='specialityName')
    additionalspecialities: str | None = Field(alias='additionalSpecialities')
    questions: list | str | None
    status: str | None
    grade: int | None

    class Config:
        allow_population_by_field_name = True

    @staticmethod
    async def create_table_vo_ioms(conn):
        await conn.execute(f"""CREATE TABLE IF NOT EXISTS {Table.VO_IOMS} (
                ID TEXT PRIMARY KEY,
                NAME TEXT NOT NULL,
                ZET INTEGER NOT NULL,
                STARTDATE TEXT NOT NULL,
                ENDDATE TEXT NOT NULL,
                IOMHOST JSON NOT NULL,
                IOMKIND TEXT NOT NULL,
                SPECIALITYNAME TEXT NOT NULL,
                ADDITIONALSPECIALITIES TEXT NOT NULL,
                QUESTIONS TEXT[] DEFAULT NULL,
                STATUS TEXT DEFAULT NULL,
                GRADE INTEGER NOT NULL)""")

    @staticmethod
    async def insert_vo_iom(conn, iom: object(), grade: int):
        await conn.execute(f"""INSERT INTO {Table.VO_IOMS} 
           (ID, NAME, ZET, STARTDATE, ENDDATE, IOMHOST, IOMKIND, SPECIALITYNAME, ADDITIONALSPECIALITIES, GRADE) 
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10) ON CONFLICT (ID) DO NOTHING""", iom.id, iom.name, iom.zet,
                           iom.startdate, iom.enddate, json.dumps(iom.iomhost), iom.iomkind, iom.specialityname,
                           iom.additionalspecialities, grade)

    @staticmethod
    async def get_vo_ioms(conn) -> list:
        record = await conn.fetch(f"""SELECT * FROM {Table.VO_IOMS}""")
        if record:
            ioms = [Iom(**iom) for iom in record]
            ioms.sort(key=lambda x: x.name, reverse=False)
            return ioms
        return []

    @staticmethod
    async def get_vo_iom_ids(conn) -> list:
        record = await conn.fetch(f"""SELECT * FROM {Table.VO_IOMS}""")
        if record:
            ioms = [Iom(**iom).id for iom in record]
            return ioms
        return []

    @staticmethod
    async def get_vo_iom(conn, iom_id: str):
        record = await conn.fetchrow(f"""SELECT * FROM {Table.VO_IOMS} WHERE ID = $1""", iom_id)
        if record:
            return Iom(**record)
        return None

    @staticmethod
    async def set_vo_iom_status(conn, iom_id: str, status: str):
        await conn.execute(f"""UPDATE {Table.VO_IOMS} SET STATUS = $2 WHERE ID = $1""", iom_id, status)

    @staticmethod
    async def set_vo_iom_grade(conn, iom_id: str, grade: int):
        await conn.execute(f"""UPDATE {Table.VO_IOMS} SET GRADE = $2 WHERE ID = $1""", iom_id, grade)

    @staticmethod
    async def create_table_spo_ioms(conn):
        await conn.execute(f"""CREATE TABLE IF NOT EXISTS {Table.SPO_IOMS} (
                ID TEXT PRIMARY KEY,
                NAME TEXT NOT NULL,
                ZET INTEGER NOT NULL,
                STARTDATE TEXT NOT NULL,
                ENDDATE TEXT NOT NULL,
                IOMHOST JSON NOT NULL,
                IOMKIND TEXT NOT NULL,
                SPECIALITYNAME TEXT NOT NULL,
                ADDITIONALSPECIALITIES TEXT NOT NULL,
                QUESTIONS TEXT[] DEFAULT NULL,
                STATUS TEXT DEFAULT NULL,
                GRADE INTEGER NOT NULL)""")

    @staticmethod
    async def insert_spo_iom(conn, iom: object(), grade: int):
        await conn.execute(f"""INSERT INTO {Table.SPO_IOMS} 
        (ID, NAME, ZET, STARTDATE, ENDDATE, IOMHOST, IOMKIND, SPECIALITYNAME, ADDITIONALSPECIALITIES, GRADE) 
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10) ON CONFLICT (ID) DO NOTHING""", iom.id, iom.name, iom.zet,
                           iom.startdate, iom.enddate, json.dumps(iom.iomhost), iom.iomkind, iom.specialityname,
                           iom.additionalspecialities, grade)

    @staticmethod
    async def get_spo_ioms(conn) -> list:
        record = await conn.fetch(f"""SELECT * FROM {Table.SPO_IOMS}""")
        if record:
            ioms = [Iom(**iom) for iom in record]
            ioms.sort(key=lambda x: x.name, reverse=False)
            return ioms
        return []

    @staticmethod
    async def get_spo_iom_ids(conn) -> list:
        record = await conn.fetch(f"""SELECT * FROM {Table.SPO_IOMS}""")
        if record:
            ioms = [Iom(**iom).id for iom in record]
            return ioms
        return []

    @staticmethod
    async def get_spo_iom(conn, iom_id: str):
        record = await conn.fetchrow(f"""SELECT * FROM {Table.SPO_IOMS} WHERE ID = $1""", iom_id)
        if record:
            return Iom(**record)
        return None

    @staticmethod
    async def set_spo_iom_status(conn, iom_id: str, status: str):
        await conn.execute(f"""UPDATE {Table.SPO_IOMS} SET STATUS = $2 WHERE ID = $1""", iom_id, status)

    @staticmethod
    async def set_spo_iom_grade(conn, iom_id: str, grade: int):
        await conn.execute(f"""UPDATE {Table.VO_IOMS} SET GRADE = $2 WHERE ID = $1""", iom_id, grade)


class Answer(BaseModel):
    id: int | str
    content: str
    correct: bool | None


class Question(BaseModel):
    id: int | str
    type: str
    content: str
    correct: bool | None
    answers: list | str | None
    status: str | None
    combinations: list | str | None

    @staticmethod
    async def generate_multi_answers(q_len: int) -> list:
        comb = set()
        temp = combinations_with_replacement([1, 0, 1, 0], q_len)
        for x in list(temp):
            comb.add(x)
        return [[*combination] for combination in comb]

    @staticmethod
    async def generate_single_answers(q_len: int) -> list:
        comb = [[0 for _ in range(q_len)] for _ in range(q_len)]
        counter = 0
        for x in comb:
            x[counter] = 1
            counter += 1
        return comb

    @staticmethod
    async def create_table(conn):
        await conn.execute(f"""CREATE TABLE IF NOT EXISTS {Table.QUESTIONS} (
                ID SERIAL PRIMARY KEY,
                TYPE TEXT NOT NULL,
                CONTENT TEXT NOT NULL,
                CORRECT BOOL DEFAULT NULL,
                ANSWERS JSON NOT NULL,
                STATUS TEXT DEFAULT NULL,
                COMBINATIONS JSON DEFAULT NULL)""")

    @staticmethod
    async def insert_question(conn, question: object()):
        record = await conn.fetch(f"""SELECT * FROM {Table.QUESTIONS} WHERE CONTENT = $1""", question.content)
        answers = [answer['content'] for answer in question.answers]
        if record:
            for _question in record:
                _question = Question(**_question)
                _answers = json.loads(_question.answers)
                if collections.Counter(answers) == collections.Counter(_answers):
                    return _question
        q_len = len(answers)
        if question.type == 'multi':
            combinations = await Question.generate_multi_answers(q_len)
        else:
            combinations = await Question.generate_single_answers(q_len)
        await conn.execute(f"""INSERT INTO {Table.QUESTIONS}
        (TYPE, CONTENT, ANSWERS, STATUS, COMBINATIONS) 
        VALUES ($1, $2, $3, $4, $5)""",
                           question.type,
                           question.content,
                           json.dumps(sorted(answers), ensure_ascii=False),
                           Status.WAIT,
                           json.dumps(sorted(combinations), ensure_ascii=False))
        return None

    @staticmethod
    async def update_question(conn, q_id: int, status: str):
        record = await conn.fetchrow(
            f"""SELECT * FROM {Table.QUESTIONS} WHERE ID = $1""", q_id)
        question = Question(**record)
        if question.status != Status.DONE:
            combinations = sorted(json.loads(question.combinations))
            if status == Status.DONE:
                await conn.execute(f"""UPDATE {Table.QUESTIONS} 
                SET STATUS = $2, COMBINATIONS = $3 WHERE ID = $1""", q_id, status, json.dumps([combinations[0]]))
            else:
                combinations.remove(combinations[0])
                await conn.execute(f"""UPDATE {Table.QUESTIONS} 
                SET STATUS = $2, COMBINATIONS = $3 WHERE ID = $1""", q_id, status, json.dumps(sorted(combinations)))


class Setting(BaseModel):
    bot_token: str
    my_group: int
    bypass_sleep: int
    bypass_info: bool
    bypass: bool
    parse: bool
    variants: int
    grade: int

    @staticmethod
    async def create_table(conn):
        await conn.execute(f"""CREATE TABLE IF NOT EXISTS {Table.SETTINGS} (
            NAME TEXT PRIMARY KEY,
            BOT_TOKEN TEXT NOT NULL,
            MY_GROUP BIGINT NOT NULL,
            BYPASS_SLEEP INTEGER NOT NULL,
            BYPASS_INFO BOOL DEFAULT FALSE,
            BYPASS BOOL DEFAULT FALSE,
            PARSE BOOL DEFAULT FALSE,
            VARIANTS INTEGER NOT NULL,
            GRADE INTEGER NOT NULL)""")
        await conn.execute(
            f"""INSERT INTO {Table.SETTINGS}
            (NAME, BOT_TOKEN, MY_GROUP, BYPASS_SLEEP, VARIANTS, GRADE) 
            VALUES ($1, $2, $3, $4, $5, $6) ON CONFLICT (NAME) DO NOTHING""",
            "settings", BOT_TOKEN, MY_GROUP, BYPASS_SlEEP, VARIANTS, GRADE)

    @staticmethod
    async def update_settings(conn, data):
        try:
            settings = Setting(**data)
            await conn.execute(
                f"""UPDATE {Table.SETTINGS} SET 
                BOT_TOKEN = $2, 
                MY_GROUP = $3, 
                BYPASS_SLEEP = $4, 
                BYPASS = $5,  
                PARSE = $6,
                VARIANTS = $7,
                GRADE = $8,
                WHERE NAME = $1""",
                "settings",
                settings.bot_token,
                settings.my_group,
                settings.bypass_sleep, settings.bypass, settings.parse, settings.variants, settings.grade)
        except Exception as exc:
            logger.critical(exc)

    @staticmethod
    async def update_grade(conn, count: int):
        await conn.execute(f"""UPDATE {Table.SETTINGS} SET GRADE = $2 WHERE NAME = $1""", "settings", count)

    @staticmethod
    async def update_variants(conn, count: int):
        await conn.execute(f"""UPDATE {Table.SETTINGS} SET VARIANTS = $2 WHERE NAME = $1""", "settings", count)

    @staticmethod
    async def update_bypass(conn, state: bool):
        await conn.execute(f"""UPDATE {Table.SETTINGS} SET BYPASS = $2 WHERE NAME = $1""", "settings", state)

    @staticmethod
    async def update_parser(conn, state: bool):
        await conn.execute(f"""UPDATE {Table.SETTINGS} SET PARSE = $2 WHERE NAME = $1""", "settings", state)

    @staticmethod
    async def update_bypass_info(conn, state: bool):
        await conn.execute(f"""UPDATE {Table.SETTINGS} SET BYPASS_INFO = $2 WHERE NAME = $1""", "settings", state)

    @staticmethod
    async def get_settings(conn):
        record = await conn.fetchrow("""SELECT * FROM settings WHERE NAME = $1""", 'settings')
        if record:
            settings = Setting(**record)
            return settings
        return None
