import os
from dotenv import load_dotenv

print("Looking for .env file in:", os.getcwd())  # prints current dir

from pathlib import Path
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=dotenv_path)


google_key = os.getenv("GOOGLE_API_KEY")
print("GOOGLE_API_KEY:", google_key)

if not google_key:
    print("❌ Still not found. Check directory or dotenv setup.")
else:
    print("✅ Key loaded successfully.")
