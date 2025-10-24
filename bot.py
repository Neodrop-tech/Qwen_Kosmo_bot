import os
import re
import asyncio
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

# Получаем токены из переменных окружения (Render)
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
HF_TOKEN = os.environ["HF_TOKEN"]

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(bot)

HF_API_URL = "https://api-inference.huggingface.co/models/Qwen/Qwen3-32B"

# --- Логика генерации ответа ---
async def ask_qwen(prompt: str) -> str:
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    # Qwen формат: system + user
    full_prompt = (
        "<|im_start|>system