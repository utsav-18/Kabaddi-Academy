import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
dotenv_path = BASE_DIR / "key.env"
print("Loading:", dotenv_path)

load_dotenv(dotenv_path, override=True)

print("RAZORPAY_KEY_ID:", os.getenv("RAZORPAY_KEY_ID"))
print("RAZORPAY_KEY_SECRET:", os.getenv("RAZORPAY_KEY_SECRET"))
