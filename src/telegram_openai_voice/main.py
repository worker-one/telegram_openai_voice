from telegram_openai_voice.api.bot import start_bot
from telegram_openai_voice.db.database import create_tables

if __name__ == "__main__":
    create_tables()
    start_bot()
