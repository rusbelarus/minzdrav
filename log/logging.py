from loguru import logger
from configparser import ConfigParser

parser = ConfigParser()
parser.read("config.ini", encoding='utf-8')

DB_NAME = parser.get("database", "dbname")
DB_USER = parser.get("database", "user")
DB_PASS = parser.get("database", "password")
DB_HOST = parser.get("database", "host")
DB_PORT = parser.get("database", "port")
DSN = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

BYPASS_SlEEP = parser.getint("DEFAULT", "bypass_sleep")
VARIANTS = parser.getint("DEFAULT", "variants")
GRADE = parser.getint("DEFAULT", "grade")

BOT_TOKEN = parser.get("bot", "token")
MY_GROUP = parser.getint("bot", "group")

BYPASS_LOG = parser.get("bypass", "login")
BYPASS_PAS = parser.get("bypass", "password")
PARSER_LOG = parser.get("parser", 'login')
PARSER_PAS = parser.get("parser", "password")

ADMIN_LOG = parser.get("admin", "login")
ADMIN_PAS = parser.get("admin", "password")

LOG_CLEAN = parser.get("log", "retention")

logger.add(
    "host.log",
    format="{time} {level} {message}",
    level="DEBUG",
    retention=LOG_CLEAN,
    compression="zip"
)
