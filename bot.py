import os
import base64
import threading
import time
import re
import requests
import telebot
from telebot import types

# === Конфигурация (ENV переопределяют значения ниже) ===
BOT_TOKEN = os.getenv("BOT_TOKEN", "8050121502:AAGCkubnfqbipGuR26RhBr083UZ8qjZC3GM")
ADMIN_IDS = {
	6053593587,
	6947365256,
}

# Репозиторий и файл ключей
OWNER = "HappyProgs"
REPO = "Vip"
BRANCH = "main"
FILE_PATH = "keys.txt"
CONTENTS_API_URL = f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{FILE_PATH}"

# GitHub токены: используйте PAT в GITHUB_TOKEN
# (App ID/Client ID приведены пользователем, но для Contents API нужен PAT)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "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")

# === Кэш ===
cached_keys = {}
last_update_time = 0
update_interval = 5

bot = telebot.TeleBot(BOT_TOKEN)


# === Вспомогательная функция ===
def parse_duration(duration_str: str):
	match = re.fullmatch(r"(\d+)([smhdw]|year)", duration_str.strip().lower())
	if not match:
		return None
	value, unit = match.groups()
	value = int(value)
	if unit == 's':
		return value
	if unit == 'm':
		return value * 60
	if unit == 'h':
		return value * 3600
	if unit == 'd':
		return value * 86400
	if unit == 'w':
		return value * 604800
	if unit == 'year':
		return value * 31536000
	return None


# === Загрузка ключей ===
def fetch_keys(force_update: bool = False):
	global cached_keys, last_update_time

	if not force_update and time.time() - last_update_time < update_interval and cached_keys:
		return cached_keys.copy()

	try:
		# Читаем через GitHub Contents API, чтобы избежать кэша CDN raw.githubusercontent.com
		headers = {
			"Authorization": f"token {GITHUB_TOKEN}",
			"Accept": "application/vnd.github+json",
			"User-Agent": "reg-bot/1.0",
		}
		resp = requests.get(CONTENTS_API_URL, headers=headers, timeout=20, params={"ref": BRANCH})
		resp.raise_for_status()
		json_body = resp.json()
		content_b64 = json_body.get("content", "")
		# содержимое может иметь переводы строк; удаляем их перед decode
		content_decoded = base64.b64decode(content_b64.encode()).decode(errors="ignore") if content_b64 else ""
		new_keys = {}

		for line in content_decoded.splitlines():
			if not line.strip():
				continue
			parts = line.split(';')
			# Ожидается формат в репозитории: Key;Hwid;Duration
			if len(parts) < 3:
				continue
			key_str = parts[0].strip()
			hwid = parts[1].strip()
			duration = parts[2].strip()
			new_keys[key_str] = {
				'hwid': hwid,
				'duration': duration,
			}

		cached_keys = new_keys
		last_update_time = time.time()
		return new_keys.copy()
	except requests.exceptions.HTTPError as http_err:
		print(f"Ошибка получения ключей: {http_err}")
		return cached_keys.copy() if cached_keys else {}
	except Exception as e:
		print(f"Ошибка получения ключей: {e}")
		return cached_keys.copy() if cached_keys else {}


# === Фоновое обновление ===
def background_updater():
	while True:
		try:
			fetch_keys(force_update=True)
			time.sleep(update_interval)
		except Exception as e:
			print(f"Ошибка фонового обновления: {e}")
			time.sleep(60)


threading.Thread(target=background_updater, daemon=True).start()


# === Сохранение ключей ===
def save_keys(keys: dict, actor_user_id) -> bool:
	try:
		content_str = ""
		for key_str, data in keys.items():
			# В репозитории сохраняем через ';' в формате: Key;Hwid;Duration
			content_str += f"{key_str};{data['hwid']};{data['duration']}\n"

		headers = {
			"Authorization": f"token {GITHUB_TOKEN}",
			"Accept": "application/vnd.github+json",
			"User-Agent": "reg-bot/1.0",
		}
		# Получаем текущий sha файла
		resp = requests.get(CONTENTS_API_URL, headers=headers, timeout=20)
		resp.raise_for_status()
		sha = resp.json().get("sha")

		payload = {
			"message": f"Updated by {actor_user_id}",
			"content": base64.b64encode(content_str.encode()).decode(),
			"sha": sha,
			"branch": BRANCH,
		}

		resp = requests.put(CONTENTS_API_URL, headers=headers, json=payload, timeout=30)
		resp.raise_for_status()

		fetch_keys(force_update=True)
		return True
	except requests.HTTPError as http_err:
		status = getattr(http_err.response, "status_code", None)
		if status == 401:
			print("Ошибка сохранения: 401 Unauthorized — проверьте GITHUB_TOKEN.")
			print("Нужен персональный токен (repo scope) с правом записи в HappyProgs/Vip.")
		else:
			print(f"Ошибка сохранения: {http_err}")
		return False
	except Exception as e:
		print(f"Ошибка сохранения: {e}")
		return False


# === Декораторы и проверки ===
def is_allowed(user_id: int) -> bool:
	return user_id in ADMIN_IDS


# === Команды бота ===
@bot.message_handler(commands=['start', 'help'])
def welcome(message):
	if not is_allowed(message.from_user.id):
		return

	kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
	kb.add("Показать ключи", "Добавить ключ", "Удалить ключ")
	bot.send_message(message.chat.id, "🔐 Панель управления ключами", reply_markup=kb)


@bot.message_handler(func=lambda m: m.text == "Показать ключи")
def show_keys(message):
	if not is_allowed(message.from_user.id):
		return
	keys = fetch_keys()
	if not keys:
		return bot.send_message(message.chat.id, "❌ Нет ключей")

	resp = "<b>Список ключей:</b>\n"
	for key_str, data in keys.items():
		resp += (
			f"\n🔑 <b>{key_str}</b>\n"
			f"🆔 HWID: <code>{data['hwid']}</code>\n"
			f"🕒 Время: <code>{data['duration']}</code>\n"
		)
	bot.send_message(message.chat.id, resp, parse_mode="HTML")


@bot.message_handler(func=lambda m: m.text == "Добавить ключ")
def add_key(message):
	if not is_allowed(message.from_user.id):
		return
	msg = bot.send_message(
		message.chat.id,
		"Введите ключ в формате (через двоеточие):\n"
		"<code>key:hwid:время</code>\n"
		"Пример: <code>VIP-KEY-1:null:30d</code> (1m, 1h, 1d, 1year)",
		parse_mode="HTML",
	)
	bot.register_next_step_handler(msg, process_add_key)


def process_add_key(message):
	if not is_allowed(message.from_user.id):
		return
	try:
		# Пользователь вводит через ':'
		parts = [p.strip() for p in message.text.split(':')]
		if len(parts) != 3:
			return bot.send_message(message.chat.id, "❌ Неверный формат. Ожидается 3 значения: key:hwid:время")

		duration_sec = parse_duration(parts[2])
		if duration_sec is None:
			return bot.send_message(message.chat.id, "❌ Неверный формат времени. Пример: 1m, 1h, 1d, 1year")

		keys = fetch_keys()
		key_str = parts[0]
		if key_str in keys:
			return bot.send_message(message.chat.id, "❌ Такой ключ уже есть")

		hwid = parts[1]
		duration = parts[2]
		keys[key_str] = {
			'hwid': hwid,
			'duration': duration,
		}

		if save_keys(keys, message.from_user.id):
			bot.send_message(message.chat.id, f"✅ Ключ <b>{key_str}</b> добавлен", parse_mode="HTML")
		else:
			bot.send_message(message.chat.id, "❌ Ошибка при сохранении")
	except Exception as e:
		bot.send_message(message.chat.id, f"❌ Ошибка: {e}")


@bot.message_handler(func=lambda m: m.text == "Удалить ключ")
def delete_key_prompt(message):
	if not is_allowed(message.from_user.id):
		return
	keys = fetch_keys()
	if not keys:
		return bot.send_message(message.chat.id, "❌ Нет ключей")

	kb = types.InlineKeyboardMarkup()
	for key_str in keys:
		kb.add(types.InlineKeyboardButton(key_str, callback_data=f"del:{key_str}"))
	bot.send_message(message.chat.id, "Выберите ключ для удаления:", reply_markup=kb)


@bot.callback_query_handler(func=lambda call: call.data.startswith("del:"))
def delete_key(call):
	if not is_allowed(call.from_user.id):
		return bot.answer_callback_query(call.id, "⛔ Нет доступа")
	key_str = call.data.split(":", 1)[1]
	keys = fetch_keys()
	if key_str not in keys:
		return bot.answer_callback_query(call.id, "❌ Ключ не найден")

	del keys[key_str]
	if save_keys(keys, call.from_user.id):
		bot.answer_callback_query(call.id, f"✅ Удален: {key_str}")
		show_keys(call.message)
	else:
		bot.answer_callback_query(call.id, "❌ Ошибка удаления")


if __name__ == '__main__':
	print("Бот запущен...")
	bot.infinity_polling()
