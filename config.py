import os
import sys
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials


if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))


dotenv_path = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError(f"Не найден BOT_TOKEN в {dotenv_path}!")

OWNER_ID = os.getenv("OWNER_ID")
if not OWNER_ID:
    raise ValueError("Не найден OWNER_ID в переменных окружения!")
OWNER_ID = int(OWNER_ID)


DATABASE_PATH = os.path.join(BASE_DIR, os.getenv("DATABASE_PATH", "data/database.db"))
REPORTS_DIR = os.path.join(BASE_DIR, os.getenv("REPORTS_DIR", "reports"))


SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
CREDS = Credentials.from_service_account_file("credentials.json", scopes=SCOPE)
CLIENT = gspread.authorize(CREDS)

