import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('API_KEY')
URL = "http://ws.audioscrobbler.com/2.0/"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEBSITE_DIR = os.path.join(BASE_DIR, "..", "website")
USERS_DIR = os.path.join(WEBSITE_DIR, "data", "users")