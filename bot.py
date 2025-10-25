import os
import asyncio
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import ChatType

# === КОНФИГУРАЦИЯ ===
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
HF_TOKEN = os.environ["HF_TOKEN"]

HF_API_URL = "https://api-inference.huggingface.co/models/Qwen/Qwen3-32B"

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(bot)

# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

async def ask_qwen(prompt: str, max_new_tokens: int = 1024) -> str:
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": max_new_tokens,
            "temperature": 0.3,
            "repetition_penalty": 1.1
        }
    }
    try:
        response = requests.post(HF_API_URL, headers=headers, json=payload, timeout=60)
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                return result[0].get("generated_text", "").strip()
        return f"Ошибка HF API: {response.status_code} — {response.text[:200]}"
    except Exception as e:
        return f"Исключение: {str(e)}"

async def fetch_chat_history(chat_id: int, limit: int = 500) -> str:
    """Собирает последние `limit` сообщений из чата (только текст от пользователей)"""
    messages = []
    offset = 0
    collected = 0

    while collected < limit:
        try:
            # Получаем пачку сообщений (макс. 100 за раз)
            history = await bot.get_chat_history(chat_id, limit=100, offset=offset)
            if not history.messages:
                break

            for msg in history.messages:
                if msg.from_user and not msg.from_user.is_bot and msg.text:
                    messages.append(f"[{msg.from_user.first_name}]: {msg.text}")
                    collected += 1
                    if collected >= limit:
                        break

            offset += 100
            await asyncio.sleep(0.5)  # уважаем лимиты Telegram API

        except Exception as e:
            print(f"Ошибка при чтении истории: {e}")
            break

    # Возвращаем последние N сообщений в хронологическом порядке
    return "\n".join(reversed(messages[-limit:]))

# === КОМАНДЫ ===

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.reply(
        "🧠 Я — Qwen-партнёр для разработки!\n\n"
        "Команды:\n"
        "/analyze_game — проанализировать чат и сгенерировать описание настолки\n"
        "/qwen <вопрос> — задать вопрос напрямую"
    )

@dp.message_handler(commands=["qwen"])
async def handle_qwen(message: types.Message):
    user_text = message.get_args()
    if not user_text:
        await message.reply("💬 Используй: /qwen Как реализовать паттерн Observer?")
        return
    thinking = await message.reply("🧠 Думаю...")
    answer = await ask_qwen(user_text)
    await thinking.edit_text("✅ Готово!")
    for i in range(0, len(answer), 4000):
        await message.reply(answer[i:i+4000])

@dp.message_handler(commands=["analyze_game"])
async def analyze_game(message: types.Message):
    if message.chat.type == ChatType.PRIVATE:
        await message.reply("❌ Эту команду нужно вызывать в группе, где я админ!")
        return

    # Проверим, админ ли бот (иначе get_chat_history не сработает)
    try:
        chat_member = await bot.get_chat_member(message.chat.id, (await bot.me).id)
        if chat_member.status not in ["administrator", "creator"]:
            await message.reply("⚠️ Я должен быть администратором, чтобы читать историю чата!")
            return
    except:
        await message.reply("⚠️ Не удалось проверить права. Сделайте меня админом!")
        return

    thinking = await message.reply("🔍 Собираю историю чата (последние 500 сообщений)...")
    
    try:
        history = await fetch_chat_history(message.chat.id, limit=500)
        if not history.strip():
            await thinking.edit_text("📭 В чате нет сообщений для анализа.")
            return

        await thinking.edit_text("🧠 Анализирую обсуждение настолки... (Qwen-32B, ~30 сек)")

        prompt = (
            "Ты — эксперт по настольным играм. На основе следующего чата разработчиков "
            "создай структурированное описание настольной игры. Включи:\n"
            "- Название (придумай, если не указано)\n"
            "- Цель игры\n"
            "- Основные правила\n"
            "- Механики (очередность ходов, ресурсы, победные условия и т.д.)\n"
            "- Особенности дизайна\n\n"
            "Чат:\n" + history[-8000:]  # HF API имеет лимит контекста
        )

        analysis = await ask_qwen(prompt, max_new_tokens=1500)
        await thinking.edit_text("✅ Анализ завершён!")

        for i in range(0, len(analysis), 4000):
            await message.reply(analysis[i:i+4000])

    except Exception as e:
        await thinking.edit_text(f"💥 Ошибка при анализе: {str(e)[:300]}")

# === ЗАПУСК ===
if __name__ == "__main__":
    print("🚀 Qwen-партнёр запущен!")
    executor.start_polling(dp, skip_updates=True)
