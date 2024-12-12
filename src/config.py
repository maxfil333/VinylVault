import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('API_KEY')
URL = "http://ws.audioscrobbler.com/2.0/"
