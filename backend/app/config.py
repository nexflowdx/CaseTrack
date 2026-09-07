from dotenv import load_dotenv
import os

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
API_LOGIN_BASE_URL = os.getenv("API_LOGIN_BASE_URL")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY não foi definida no .env")

if not API_LOGIN_BASE_URL:
    raise RuntimeError("API_LOGIN_BASE_URL não foi definida no .env")