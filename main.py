from logging import exception
from sqlite3.dbapi2 import version
import vk_api, datetime, sqlite3, random
from vk_api import keyboard
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from datetime import datetime

from config import token
from config import bot_id
from config import bot_domain
from config import bot_version

from config import dev_id
from config import prefix
from config import ranks
from config import names

class MyBotLongPoll(VkBotLongPoll):
	def listen(self):
		while True:
			try:
				for event in self.check():
					yield event
			except Exception as e:
				print('[Error] ', e)

vk_session = vk_api.VkApi(token = token)
longpoll = MyBotLongPoll(vk_session, bot_id)

print(f"[{datetime.now()}] Бот запущен")

db = sqlite3.connect('db.sqlite')
sql = db.cursor()
print(f"[{datetime.now()}] Бот подключен к базе данных")

sql.execute("""CREATE TABLE IF NOT EXISTS users (
	user_id INTEGER,
	rank INTEGER,
	name TEXT
)""")
sql.execute("""CREATE TABLE IF NOT EXISTS biz (
	biz_name TEXT,
	biz_type INTEGER,
	biz_cost INTEGER,
	biz_owner INTEGER
)""")
db.commit()

keyboard = VkKeyboard(one_time=False)
keyboard.add_button('&#128452; Профиль', color=VkKeyboardColor.PRIMARY)
keyboard.add_button('&#128221; Беседа', color=VkKeyboardColor.SECONDARY)
keyboard.add_button('&#129302; Бот', color=VkKeyboardColor.SECONDARY)

keyboard_reg_url = VkKeyboard(one_time = False, inline=True)
keyboard_reg_url.add_openlink_button('Регистрация', link= 'https://vk.me/domain') # Вставить вместо domain ссылка-скоращение группы



keyboard_reg = VkKeyboard(one_time = False, inline=True)
keyboard_reg.add_button('Регистрация', color=VkKeyboardColor.POSITIVE)

keyboard_group = VkKeyboard(one_time=False)
keyboard_group.add_button('&#128452; Профиль', color=VkKeyboardColor.PRIMARY)
keyboard_group.add_button('&#129302; Бот', color=VkKeyboardColor.SECONDARY)

keyboard_profile = VkKeyboard(one_time = False, inline=True)
keyboard_profile.add_button('&#9881; Настройки', color=VkKeyboardColor.SECONDARY)

keyboard_profile_settings = VkKeyboard(one_time = False, inline=True)
keyboard_profile_settings.add_button('&#127917; Смена ника', color=VkKeyboardColor.SECONDARY)

def reply_message(chat_id, text, keyboard):
	vk_session.method('messages.send', {'user_id' : chat_id, 'message' : text, 'random_id' : 0, 'keyboard' : keyboard})

def reply_message_chat(chat_id, text, keyboard):
	vk_session.method('messages.send', {'chat_id' : chat_id, 'message' : text, 'random_id' : 0, 'keyboard' : keyboard})

def check_registration(user_id):
	sql.execute(f"SELECT user_id FROM users WHERE user_id = '{user_id}'")
	if sql.fetchone() is None:
		reply_message_chat(chat_id, f'[id{user_id}|Извини], но я могу обслуживать только верифицированных пользователей, жми на кнопку ниже, чтобы стать одним из них!', keyboard_reg_url.get_keyboard())
		return 0
	else:	
		return 1

def get_user(user_id):
	user_id = vk_session.method("users.get", {"user_ids": user_id})
	user_id = user_id[0]['first_name'] +  ' ' + user_id[0]['last_name']
	return user_id

def execute_read_query(query):
    cursor = db.cursor()
    result = None
    cursor.execute(query)
    result = cursor.fetchone()
    return result[0]


keyboard_invite = VkKeyboard(one_time = False, inline=True)
keyboard_invite.add_button('Получить ссылку', color=VkKeyboardColor.POSITIVE)

for event in longpoll.listen():
	if event.type == VkBotEventType.MESSAGE_NEW:

		received_message = event.object.message['text']
		user_id = event.message.from_id 
		
		if event.from_chat:
			chat_id = event.chat_id
			
			if received_message == f'{bot_domain} 🤖 Бот' and check_registration(user_id) == 1:
				reply_message_chat(chat_id, f'&#9851; Версия бота: {bot_version}\n&#128706; Действующий префикс: "{prefix}"', keyboard.get_keyboard())
			
			elif received_message == f"{prefix}cid":
				reply_message_chat(chat_id, f'Чат ID: {chat_id}', [])

			elif received_message == f'{bot_domain} 🗄 Профиль' and check_registration(user_id) == 1:
				rank = execute_read_query(f'SELECT rank FROM users WHERE user_id = "{user_id}"')
				rank = ranks[rank-1]

				name = execute_read_query(f'SELECT name FROM users WHERE user_id = "{user_id}"')

				if name == 'None': 
					name_id = random.randint(0, 5)
					name = names[name_id]

				biz_name = sql.execute(f'SELECT biz_name FROM biz WHERE biz_owner = "{user_id}"')
				biz_name = biz_name.fetchone()
				
				if biz_name is None:
					biz_name = 'Нету'
				else:
					biz_name = sql.execute(f'SELECT biz_name FROM biz WHERE biz_owner = "{user_id}"')
					biz_name = biz_name.fetchone()[0]

				reply_message_chat(chat_id, f'&#128697; Профиль: {name}\n&#127775; Ранг: {rank}\n\n\n&#127760; Бизнес: {biz_name}', [])

			elif received_message == f'{bot_domain} 📝 Беседа' and check_registration(user_id) == 1:
				title = vk_session.method('messages.getConversationsById', {'peer_ids' : 2000000000 + chat_id})['items'][0]['chat_settings']['title']
				owner_id = vk_session.method('messages.getConversationsById', {'peer_ids' : 2000000000 + chat_id})['items'][0]['chat_settings']['owner_id']
				members = vk_session.method("messages.getConversationMembers", {"peer_id": 2000000000 + chat_id})['count']
				reply_message_chat(chat_id, f'&#128172; Беседа: "{title}"\n&#128081; Основатель: {get_user(owner_id)}\n&#9881; Идентификатор: {chat_id}\n&#128106; Участников: {members}', keyboard_invite.get_keyboard())

			elif received_message == f'{bot_domain} Получить ссылку' and check_registration(user_id) == 1: 
				invite_code = vk_session.method("messages.getInviteLink", {"peer_id": 2000000000 + chat_id})['link']
				reply_message_chat(chat_id, f'Вот [id{user_id}|твоя] ссылка: {invite_code}', [])

			else:
				if prefix in received_message:
					reply_message_chat(chat_id, f'Ой, кажется я вижу несуществующую команду! Разработчик обещал её реализовать к осени. Но не сказал, к какой', [])
			
		else:
			chat_id = event.object.message['from_id']

			if received_message == 'Начать':
				reply_message(chat_id, 'Пора освободить твой разум. Но я могу лишь указать на кнопку. Тебе придётся самостоятельно нажать на неё &#128572;', keyboard_reg.get_keyboard())

			elif received_message == 'Регистрация':
				sql.execute(f"SELECT user_id FROM users WHERE user_id = '{user_id}'")
				if sql.fetchone() is None:
					sql.execute(f"INSERT INTO users VALUES (?, ?, ?)", (user_id, 1, 'None'))
					db.commit()
					print(f'[{datetime.now()}] [MySQL] Запрос успешно выполнен')
					reply_message(chat_id, f'Круто! Пополнение в наших рядах, да пребудет с [id{user_id}|тобой] Сила!', keyboard.get_keyboard())
				else:
					print(f'[{datetime.now()}] [MySQL] Запрос отклонен. Введены существующие данные')
					reply_message(chat_id, f'Нет-нет, [id{user_id}|ты] не можешь просто так взять и заново зарегистрироваться. Эта процедура одноразовая.', keyboard.get_keyboard())


			elif received_message == f'🤖 Бот':
				reply_message(chat_id, f'&#9889; Клавиатура обновлена\n&#128187; Разработчик: Р.Ю.\n&#9881; Версия: {bot_version}', keyboard_group.get_keyboard())
			
			elif received_message == f'🗄 Профиль' and check_registration(user_id) == 1:
				rank = execute_read_query(f'SELECT rank FROM users WHERE user_id = "{user_id}"')
				rank = ranks[rank-1]

				name = execute_read_query(f'SELECT name FROM users WHERE user_id = "{user_id}"')

				if name == 'None': 
					name_id = random.randint(0, 5)
					name = names[name_id]

				biz_name = sql.execute(f'SELECT biz_name FROM biz WHERE biz_owner = "{user_id}"')
				biz_name = biz_name.fetchone()
				
				if biz_name is None:
					biz_name = 'Нету'
				else:
					biz_name = sql.execute(f'SELECT biz_name FROM biz WHERE biz_owner = "{user_id}"')
					biz_name = biz_name.fetchone()[0]

				reply_message(chat_id, f'&#128697; Профиль: {name}\n&#127775; Ранг: {rank}\n\n\n&#127760; Бизнес: {biz_name}', keyboard_profile.get_keyboard())

			elif received_message == '⚙ Настройки' and check_registration(user_id) == 1:
				name = sql.execute(f'SELECT name FROM users WHERE user_id = "{user_id}"')
				name = name.fetchone()[0]
				if name == 'None': 
					name = 'Нету'
					name_info = 'Ты аноним! Система автоматически каждый раз генерирует ник среди 5 вариантов'
				else:
					name_info = 'Какой любопытный у тебя ник! Надеюсь ты не против, что я его повзаимствую для своих наследников? Мне кажется, что Новый сын (1) и Новая дочь (2) звучит не так красиво по сравнению с твоим ником &#128547;'
				reply_message(chat_id, f'Здесь, в этом небольшом сообщении мы уместили настройки твоего аккаунта. Выбирай нужную категорию и меняй под себя &#128521;\n\nДействующие настройки:\n\n&#127380; Идентификатор: id{user_id} [Нельзя изменить]\n&#127917; Псевдоним (ник):  {name}\n\n\n\n&#127744; {name_info}', keyboard_profile_settings.get_keyboard())

			elif received_message == '🎭 Смена ника' and check_registration(user_id) == 1:
				reply_message(chat_id, f'Мои биты подсказывают, что ты любишь меняться и это очень круто, я тебе помогу. Введи: {prefix}newname Text\n\n&#128204; В нике не должно быть пробелов\n&#128204; Чтобы удалить ник, напиши "None"', [])

			elif f'{prefix}newname' in received_message and check_registration(user_id) == 1:
				name = sql.execute(f"SELECT name FROM users WHERE user_id = '{user_id}'")
				name = name.fetchone()[0]
				new_name = received_message.split()
				new_name = new_name[1]
				print(new_name[1])
				if name == 'None':
					name = 'Аноним'
				sql.execute(f"UPDATE users SET name = '{new_name}' WHERE user_id = '{user_id}'")
				db.commit()
				if new_name == 'None':
					reply_message(chat_id, f'Время перемен! Теперь ты не {name}, а Аноним\n\n&#9888; Сообщаю, что ник меняется и используется иисключительно в боте. Ник также никак не связан с ФИ (Фамилия и Имя) ВКонтакте', [])
				else:
					reply_message(chat_id, f'Время перемен! Теперь ты не {name}, а {new_name}\n\n&#9888; Сообщаю, что ник меняется и используется иисключительно в боте. Ник также никак не связан с ФИ (Фамилия и Имя) ВКонтакте', [])

			else:
				reply_message(chat_id, f'Я всего лишь бот и распознаю только ключевые слова - команды. &#128532;', [])