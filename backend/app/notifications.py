import httpx
from sqlalchemy import select
from .config import settings
from .db import Session
from .models import Notification


async def deliver_telegram():
    if not (settings.telegram_enabled and settings.telegram_bot_token and settings.telegram_chat_id):
        return
    with Session() as db:
        for notification in db.scalars(select(Notification).where(Notification.telegram_sent == False, Notification.telegram_attempts < 3).limit(10)):
            notification.telegram_attempts += 1
            try:
                async with httpx.AsyncClient(timeout=10, trust_env=False) as client:
                    result = await client.post(f'https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage', json={'chat_id':settings.telegram_chat_id,'text':notification.title+'\n'+notification.message})
                    result.raise_for_status()
                    notification.telegram_sent = bool(result.json().get('ok'))
            except (httpx.HTTPError, ValueError) as exc:
                # Never persist exception URLs, which contain bot credentials.
                notification.telegram_error = type(exc).__name__
            db.commit()
