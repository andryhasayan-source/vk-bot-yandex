import os
import json
import datetime
import vk_api
import ydb
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

TOKEN = os.getenv("VK_TOKEN")
CONFIRMATION_TOKEN = os.getenv("CONFIRMATION_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

YDB_ENDPOINT = os.getenv("YDB_ENDPOINT")
YDB_DATABASE = os.getenv("YDB_DATABASE")

vk_session = vk_api.VkApi(token=TOKEN)
vk = vk_session.get_api()

driver = ydb.Driver(endpoint=YDB_ENDPOINT, database=YDB_DATABASE)
driver.wait(timeout=5)
session = driver.table_client.session().create()

def main_kb():
    k = VkKeyboard(resize=True)
    k.add_button("💰 Узнать стоимость", VkKeyboardColor.POSITIVE)
    k.add_button("📞 Контакты", VkKeyboardColor.PRIMARY)
    return k.get_keyboard()

def service_kb():
    k = VkKeyboard(resize=True)
    k.add_button("Бот ВК")
    k.add_button("Автоматизация")
    return k.get_keyboard()

def budget_kb():
    k = VkKeyboard(resize=True)
    k.add_button("до 1000")
    k.add_button("1000-5000")
    k.add_button("5000+")
    return k.get_keyboard()

def get_user(user_id):
    q = f"SELECT * FROM users WHERE user_id={user_id};"
    r = session.transaction().execute(q, commit_tx=True)
    return r[0].rows

def create_user(user_id):
    q = f'UPSERT INTO users (user_id, step) VALUES ({user_id}, "start");'
    session.transaction().execute(q, commit_tx=True)

def update_user(user_id, field, value):
    q = f'UPSERT INTO users (user_id, {field}) VALUES ({user_id}, "{value}");'
    session.transaction().execute(q, commit_tx=True)

def update_segment(user_id, step, service, budget, contact):
    segment = "cold"
    if contact:
        segment = "hot"
    elif service and budget:
        segment = "warm"
    elif step == "start":
        segment = "cold"
    else:
        segment = "lost"
    update_user(user_id, "segment", segment)

def handle(user_id, text):
    text = text.lower()
    create_user(user_id)
    user_data = get_user(user_id)

    step = "start"
    if user_data:
        user_data = user_data[0]
        step = user_data.step

    if text in ["привет", "начать"] or step == "start":
        update_user(user_id, "step", "menu")
        return "👋 Привет! Выбери 👇", main_kb()

    if "стоимость" in text:
        update_user(user_id, "step", "service")
        return "Что нужно?", service_kb()

    if step == "service":
        update_user(user_id, "service", text)
        update_user(user_id, "step", "budget")
        return "Бюджет?", budget_kb()

    if step == "budget":
        update_user(user_id, "budget", text)
        update_user(user_id, "step", "contact")
        return "Оставь контакт"

    if step == "contact":
        update_user(user_id, "contact", text)
        update_user(user_id, "created_at", datetime.datetime.now().isoformat())
        update_user(user_id, "step", "done")
        return "Заявка отправлена!", main_kb()

    if "контакты" in text:
        return "Telegram: @yourtag", main_kb()

    user = get_user(user_id)[0]
    update_segment(user_id, user.step, user.service, user.budget, user.contact)

    return "Выбери кнопку", main_kb()

def handler(event, context):
    body = json.loads(event["body"])

    if body["type"] == "confirmation":
        return {"statusCode": 200, "body": CONFIRMATION_TOKEN}

    if body["type"] == "message_new":
        msg = body["object"]["message"]

        user_id = msg["from_id"]
        text = msg["text"]

        response, keyboard = handle(user_id, text)

        vk.messages.send(
            user_id=user_id,
            message=response,
            keyboard=keyboard if keyboard else None,
            random_id=0
        )

    return {"statusCode": 200, "body": "ok"}
