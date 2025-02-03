from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app import sql
from config import ADMIN_USERS, ADMIN_MESSAGE, BOT_TOKEN
import datetime

import asyncio
import logging
logging.basicConfig(level=logging.INFO)

# Создаем экземпляры бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Создание таблиц в базе данных SQLite
sql.create_tables()


@dp.message(Command('start'))
async def send_start(message: types.Message):
    user_id = message.from_user.id
    data_reg = message.date
    user = sql.get_user_by_id(user_id)
    
    if not user:
        # Если пользователь отсутствует, добавляем его
        user_info = {
            'tg_id': user_id,
            'pos': 'main_menu',
            'data_reg': data_reg, 
            'profile': {"organization": "Нет данных", "organization_adress": "Нет данных", "organization_inn": "Нет данных", "organization_phone": "Нет данных", "history_ticket": "", "data_ticket": "", "user_name": ""}
        }
        sql.add_user(**user_info)
        text_no_user = f"Добро пожаловать в HelpDesk компании <b>ЭниКей</b>! Для работы в сервисе необходимо заполнить данные."

        builder = InlineKeyboardBuilder()
        builder.button(text="🏢 Моя компания", callback_data="my_company")
        keyboard = builder.as_markup()
        await message.answer(text_no_user, reply_markup=keyboard, parse_mode="HTML")
        
    else:
        # Проверка открытых\закрытых тикетов 
        open_ticket = sql.get_total_tickets_by_status_for_user(user_id, "В работе")
        closed_ticket = sql.get_total_tickets_by_status_for_user(user_id, "Завершена")
        # Чтение профиля
        profile = sql.read_profile(user_id)
        sql.update_pos('main_menu', 'tg_id', user_id)
        organization = profile.get("organization", "Нет данных")
        organization_phone = profile.get("organization_phone", "Нет данных")
        
        text_user =  (f"<b>🧑‍💻 Главное меню</b> \n\n" 
                f"<b>📋 Компания: </b> {organization}\n"
                f"<b>☎️ Контактный номер:</b> {organization_phone}\n\n"
                
                f"<b>📬Открытых заявок:</b> {open_ticket}\n" 
                f"<b>📭Закрытых заявок:</b> {closed_ticket}\n" 
                f"\nВыберите интересующее действие ⬇️"
        )

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="🏢 Моя компания", callback_data="my_company"),
            InlineKeyboardButton(text="📥 Мои заявки", callback_data="my_ticket")
        )
        builder.row(
            InlineKeyboardButton(text="📤 Новая заявка", callback_data="new_ticket")
        )

        # Проверяем, является ли пользователь администратором
        if user_id in ADMIN_USERS:
            builder.row(InlineKeyboardButton(text="🤘 Тикет меню", callback_data="admin_panel"))
        keyboard = builder.as_markup()
        await message.answer(text_user, reply_markup=keyboard, parse_mode="HTML")
       
    
# Главное меню пользователя мимикрия под /start
def main_menu(tg_id):
    sql.update_pos('main_menu', 'tg_id', tg_id)
    user_id = tg_id
    open_ticket = sql.get_total_tickets_by_status_for_user(tg_id, "В работе")
    closed_ticket = sql.get_total_tickets_by_status_for_user(tg_id, "Завершена")
    profile = sql.read_profile(tg_id)
    organization = profile.get("organization", "Нет данных")
    organization_phone = profile.get("organization_phone", "Нет данных")
    
    text =  (f"<b>🧑‍💻 Главное меню</b> \n\n" 
            f"<b>📋 Компания: </b> {organization}\n"
            f"<b>☎️ Контактный номер:</b> {organization_phone}\n\n"
            
            f"<b>📬Открытых заявок:</b> {open_ticket}\n" 
            f"<b>📭Закрытых заявок:</b> {closed_ticket}\n" 
            f"\nВыберите интересующее действие ⬇️"
    )

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🏢 Моя компания", callback_data="my_company"),
        InlineKeyboardButton(text="📥 Мои заявки", callback_data="my_ticket")
    )
    builder.row(
        InlineKeyboardButton(text="📤 Новая заявка", callback_data="new_ticket")
    )

    # Проверяем, является ли пользователь администратором
    if user_id in ADMIN_USERS:
        builder.row(InlineKeyboardButton(text="🤘Тикет меню", callback_data="admin_panel"))

    keyboard = builder.as_markup()
    return text, keyboard
    
    
def new_ticket(tg_id):
    text = (f"<b>📤 Создание новой заявки</b>\n\n" 
            # f" - 📝 Опишите вашу проблему.\n"
            f" - 🧩 Пожалуйста, опишите вашу проблему и укажите как можно подробнее.\n\n"
            f"<b>Пример оформления заявки:</b> \n<i>Не работает принтер на 4 ПК, необходимо проверить подключение.</i>")
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data="main_menu")
    keyboard = builder.as_markup()
    return text, keyboard 


def my_ticket(tg_id):
    profile = sql.read_profile(tg_id)
    user_tickets_in_progress = sql.get_tickets_in_progress_by_user_id(tg_id)
    total_user_tickets_in_progress = len(user_tickets_in_progress)
    open_ticket = str(total_user_tickets_in_progress) if total_user_tickets_in_progress else "0"
    organization = profile.get("organization")
    organization_address = profile.get("organization_adress")
    
    if user_tickets_in_progress:
        text = (f"<b>📥 Мои заявки в работе</b>\n\n"
                     f"<b>Компания:</b> {organization}\n"
                     f"<b>Адрес заявки:</b> {organization_address}\n" 
                     f"<b>Заявок в работе:</b> {open_ticket}\n\n"
                     )     
        for ticket in user_tickets_in_progress:
            # Использование индексов для доступа к данным кортежа           
            text += (f"<b>Номер заявки:</b> <code>#{ticket[0]} </code>\n"
                     f"<b>Описание:</b> {ticket[4]}\n"
                     f"<b>Дата: </b>{ticket[5]}\n"
                     f"<b>Статус:</b> {ticket[6]}\n"
                     )
    else:
        text = '<b>📥 Мои заявки </b>\n\nУ вас пока нет заявок в работе..  🤷‍♂️ \n- <i>Что бы оставить заявку воспользуйтесь меню </i><b>"📤 Новая заявка"</b>'

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="☑️ История заявок", callback_data="my_ticket_history"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu"))
    keyboard = builder.as_markup()
    return text, keyboard


def my_ticket_history(tg_id, page=1, page_size=4):
    completed_tickets = sql.get_completed_tickets_by_user(tg_id)
    # Проверяем, есть ли завершенные заявки
    if completed_tickets:
        # Проверяем, нужна ли пагинация
        if len(completed_tickets) > page_size:
            start_index = (page - 1) * page_size
            end_index = start_index + page_size
            current_page_tickets = completed_tickets[start_index:end_index]
            text = f"<b>📨 История ваших завершенных заявок (страница {page}):</b>\n\n"
        else:
            current_page_tickets = completed_tickets
            text = "<b>📨 История ваших завершенных заявок:</b>\n\n"
        
        for ticket in current_page_tickets:
            text += f"✅\n" \
                    f"<b>├ Номер заявки:</b> <code>#{ticket[0]}</code>\n" \
                    f"<b>├ Время создания:</b> {ticket[5]}\n" \
                    f"<b>├ Сообщение:</b> - <em>{ticket[4]}</em>\n" \
                    f"<b>└ Комментарий исполнителя:</b>  - <em>{ticket[7]}</em>\n\n"
                    
    else:
        text = "🤷‍♂️ Упс.. У вас нет истории заявок."
        
    builder = InlineKeyboardBuilder()
    # Создаем кнопки для навигации по страницам, если нужно
    if len(completed_tickets) > page_size:
        if page > 1:
            builder.button(text="🔙 Предыдущая", callback_data=f"my_ticket_page_{page - 1}")
        if end_index < len(completed_tickets):
            builder.button(text="🔜 Следующая", callback_data=f"my_ticket_page_{page + 1}")
    # Добавляем кнопку "Назад"
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="my_ticket"))
    keyboard = builder.as_markup()
    return text, keyboard


def my_company(tg_id):
    profile = sql.read_profile(tg_id)
    organization = profile.get("organization", "Нет данных")
    organization_address = profile.get("organization_adress", "Нет данных")
    organization_inn = profile.get("organization_inn", "Нет данных")
    organization_phone = profile.get("organization_phone", "Нет данных")
    
    # Формирование текста для отображения данных о компании
    text = (f"<b>🏢 Информация о компании</b>\n\n" 
           f"<b>📋 Компания:</b> {organization}\n" 
           f"<b>📍 Адрес:</b> {organization_address}\n" 
           f"<b>📑 ИНН:</b> {organization_inn}\n" 
           f"<b>☎️ Контактный номер:</b> <i>{organization_phone}</i>\n\n" 
           f"<b>ЗАПОЛНИТЬ ДАННЫЕ О КОМПАНИИ ⬇️ </b>" )

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=f"{'✅' if organization != 'Нет данных' else '❌'} Наименование компании", callback_data="edit_company_name"))
    builder.row(InlineKeyboardButton(text=f"{'✅' if organization_address != 'Нет данных' else '❌'} Фактический адрес", callback_data="edit_company_adress"))
    builder.row(InlineKeyboardButton(text=f"{'✅' if organization_inn != 'Нет данных' else '❌'} ИНН", callback_data="edit_company_inn"))
    builder.row(InlineKeyboardButton(text=f"{'✅' if organization_phone != 'Нет данных' else '❌'} Контактный номер", callback_data="edit_company_phone"))
    builder.row(InlineKeyboardButton(text="⬅️ В меню", callback_data="main_menu"))
    keyboard = builder.as_markup()
    return text, keyboard


def edit_company_name(tg_id):
    text = f"📋 Введите наименование организации. \nПример: <code> ООО РОГА И КОПЫТА </code>"
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data="my_company")
    keyboard = builder.as_markup()
    return text, keyboard

def edit_company_adress(tg_id):
    text = f"📍Введите фактический адрес организации. \nПример: <code> г. Иваново, ул. Пушкина, д. 3 оф. 1 </code>"
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data="my_company")
    keyboard = builder.as_markup()
    return text, keyboard
    
def edit_company_inn(tg_id):
    text = f"📑 Введите ИНН организации. \nПример: <code> 3700010101 </code>"
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data="my_company")
    keyboard = builder.as_markup()
    return text, keyboard

def edit_company_phone(tg_id):
    text = f"☎️ Введите контактный номер телефона. \nПример: <code> +79100009999 </code>"
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data="my_company")
    keyboard = builder.as_markup()
    return text, keyboard
      
def done_ticket(tg_id):
    last_ticket_number = sql.get_last_ticket_number()   
    text = f'🎉🥳 Успех, ваша заявка зарегистрирована! \n\n<b>Номер заявки: </b><code>#{last_ticket_number}</code>. \n\n<i>PS: Отслеживайте статус поставленных задач в разделе</i> <b>"📥 Мои заявки"</b>'
    builder = InlineKeyboardBuilder()
    builder.button(text="🧑‍💻 Главное меню", parse_mode="HTML", callback_data="main_menu")
    keyboard = builder.as_markup()
    return text, keyboard


# Административный раздел
def admin_panel():
    total_open_tickets = sql.get_total_tickets_by_status_admin("В работе")  # Получаем общее количество заявок "В работе"
    total_closed_tickets = sql.get_total_tickets_by_status_admin("Завершена")  # Получаем общее количество завершенных заявок
    all_tickets_in_progress = sql.get_all_tickets_in_progress()
    
    text = f"<b>🤘 Тикет меню 💲</b>\n\n"
    text += f"<b>🔥Заявок в работе:</b> {total_open_tickets}\n"
    text += f"<b>👍Завершенных заявок:</b> {total_closed_tickets}\n\n"
    text += f"<b>⚠️ Внимание!</b> <i>Закрытые задачи не могут быть возвращены в работу. Пожалуйста, будьте внимательны при их закрытии!</i>"

    builder = InlineKeyboardBuilder()
    for ticket in all_tickets_in_progress:
        ticket_info = f"Заявка #{ticket[0]} - {ticket[5]}"  # Номер и описание заявки
        builder.row(InlineKeyboardButton(text=ticket_info, callback_data=f"ticket_{ticket[0]}"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu"))
    keyboard = builder.as_markup()
    return text, keyboard



@dp.callback_query(lambda query: query.data.startswith(('ticket_', 'my_ticket_page_')))
async def handle_ticket_callback(query: types.CallbackQuery):
    user_id = query.from_user.id
    tg_id = user_id
    

    if query.data.startswith('ticket_'):
        ticket_id = query.data.split('_')[1]
        ticket_info = sql.get_ticket_info(int(ticket_id))
        sql.update_pos(f'ticket_details_{ticket_info[0]}', 'tg_id', user_id)
        await query.answer()
        text = f"<b>Детали заявки:</b> <code>#{ticket_info[0]}\n\n</code>" \
               f"<b>Пользователь ID:</b> <a href='tg://user?id={ticket_info[1]}'>{ticket_info[1]}</a>\n" \
               f"<b>Организация:</b> {ticket_info[2]}\n" \
               f"<b>Адрес:</b> {ticket_info[3]}\n\n" \
               f"<b>Сообщение от пользователя:</b> - <em>{ticket_info[4]}</em>\n\n" \
               f"<b>Время создания:</b> {ticket_info[5]}\n" \
               f"<b>Статус:</b> {ticket_info[6]}\n\n" \
               f"<em>⚠️ Для завершения задачи введите комментарий. В ответ вам придет сообщение с подтвержением!</em>"

        builder = InlineKeyboardBuilder()
        builder.button(text="⬅️ Назад", callback_data="admin_panel")
        keyboard_markup = builder.as_markup()
        await query.message.edit_text(text, reply_markup=keyboard_markup, parse_mode="HTML")
    
    
    if query.data.startswith('my_ticket_page_'):
        page = int(query.data.split('_')[3])  # Получаем номер страницы из колбека
        await query.answer()                  # Ответим на колбек, чтобы убрать "крутилку"
        tg_id = query.from_user.id
        # Получаем текст сообщения и клавиатуру с учетом текущей страницы
        text, keyboard = my_ticket_history(tg_id, page)
        # Редактируем сообщение с новым текстом и клавиатурой
        await query.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")



# Группа колбеков на батоны
@dp.callback_query()
async def inline_kb_answer_callback_handler(query: types.CallbackQuery):
    user_id = query.from_user.id
    tg_id = user_id
        
    if query.data == 'admin_panel':
        # Обновление ячейки 'pos' в базе данных
        sql.update_pos('admin_panel', 'tg_id', user_id)
        await query.answer()
        text, keyboard = admin_panel()
        await query.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

    if query.data == 'main_menu':
        # Обновление ячейки 'pos' в базе данных
        sql.update_pos('main_menu', 'tg_id', user_id)
        await query.answer()
        text, keyboard = main_menu(tg_id)
        await query.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        
    if query.data.startswith('complete_'):   
        ticket_id = query.data.split('_')[1]
        # Обновление ячейки 'pos' в базе данных
        sql.update_pos('complete_', 'tg_id', user_id)
        await query.answer()
        sql.update_ticket_status(int(ticket_id), "Завершена")
        ticket_comm_done = sql.read_ticket_comment(int(ticket_id))
        ticket_info = sql.get_ticket_info(int(ticket_id))
            
        current_time = datetime.datetime.now(datetime.timezone.utc)
        time_ticket = datetime.datetime.fromisoformat(ticket_info[5])
        time_difference = current_time - time_ticket
        
        # Преобразуем общее количество секунд в объект timedelta
        total_seconds = time_difference.total_seconds()
        hours = int(total_seconds // 3600) 

        # Отправка сообщения пользователю о завершении задачи
        user_id = ticket_info[1]  # ID пользователя, поставившего задачу
        completion_message = f"🎉 Задача <code>#{ticket_id}</code> выполнена!\n<b>Время выполнения:</b> {hours} часа(ов).\n\n<b>Ответ исполнителя:</b> - <em>{ticket_comm_done}</em>\n\n<em>⚠️ Пожалуйста, проверьте корректность исполнения задачи.</em>"

        #Клавиатура для пользователя
        builder_user = InlineKeyboardBuilder()
        builder_user.button(text="☑️ История заявок", callback_data="my_ticket_history")
        builder_user.button(text="🧑‍💻 Главное меню", callback_data="main_menu")
        keyboard_markup_user = builder_user.as_markup()

        #Клавиатура для админа
        builder_admin = InlineKeyboardBuilder()
        builder_admin.button(text="🤘Тикет меню", callback_data="admin_panel")
        keyboard_markup_admin = builder_admin.as_markup()
        
        await bot.send_message(user_id, completion_message, reply_markup=keyboard_markup_user, parse_mode="HTML")
        await bot.send_message(query.from_user.id, completion_message, reply_markup=keyboard_markup_admin, parse_mode="HTML")  
        
    
    if query.data == 'my_company':
        # Обновление ячейки 'pos' в базе данных
        sql.update_pos('my_company', 'tg_id', user_id)
        await query.answer()
        text, keyboard = my_company(tg_id)
        await query.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
       
    if query.data == 'edit_company_name':
        # Обновление ячейки 'pos' в базе данных
        sql.update_pos('edit_company_name', 'tg_id', user_id)
        await query.answer()
        text, keyboard = edit_company_name(tg_id)
        await query.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        
    if query.data == 'edit_company_adress':
        # Обновление ячейки 'pos' в базе данных
        sql.update_pos('edit_company_adress', 'tg_id', user_id)
        await query.answer()
        text, keyboard = edit_company_adress(tg_id)
        await query.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")     

    if query.data == 'edit_company_inn':
        # Обновление ячейки 'pos' в базе данных
        sql.update_pos('edit_company_inn', 'tg_id', user_id)
        await query.answer()
        text, keyboard = edit_company_inn(tg_id)
        await query.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
 
    if query.data == 'edit_company_phone':
        # Обновление ячейки 'pos' в базе данных
        sql.update_pos('edit_company_phone', 'tg_id', user_id)
        await query.answer()
        text, keyboard = edit_company_phone(tg_id)
        await query.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
             
    if query.data == 'new_ticket':
        # Обновление ячейки 'pos' в базе данных
        sql.update_pos('new_ticket', 'tg_id', user_id)
        await query.answer()
        text, keyboard = new_ticket(tg_id)
        await query.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        
    if query.data == 'my_ticket':
        # Обновление ячейки 'pos' в базе данных
        sql.update_pos('my_ticket', 'tg_id', user_id)
        await query.answer()
        text, keyboard = my_ticket(tg_id)
        await query.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")      

    if query.data == 'my_ticket_history':
        # Обновление ячейки 'pos' в базе данных
        sql.update_pos('my_ticket_history', 'tg_id', user_id)
        await query.answer()
        text, keyboard = my_ticket_history(tg_id)
        await query.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")   
        
        
        
        
# Обратотка текстовых сообщений
@dp.message()
async def handle_text_input(message: types.Message):
    
    user_id = message.from_user.id
    username = message.from_user.username
    profile = sql.read_profile(user_id)  
    organization_name = profile.get("organization", "")
    organization_address = profile.get("organization_adress", "") 
    organization_phone = profile.get("organization_phone", "Нет данных")
    user_position = sql.read_cell('pos', 'tg_id', user_id)

    if user_position.startswith('ticket_details_'):
        parts = user_position.split('_')
        if len(parts) == 3 and parts[2].isdigit():
            ticket_id = int(parts[2])
            # Обновление комментария в базе данных
            comment_text = message.text
            sql.update_ticket_comment(ticket_id, comment_text)
            
            # Создаем кнопку "✅ Выполнить"
            builder = InlineKeyboardBuilder()
            builder.button(text="✅ Завершить задачу", callback_data=f"complete_{ticket_id}")
            keyboard = builder.as_markup()
            
            # Вставляем переменные в текст сообщения
            success_message = f"<b>Комментарий к тикету <code>#{ticket_id}</code> успешно записан!</b>\n\n<b>Ответ исполнителя:</b> - <em>{comment_text}</em>\n\n<em>⚠️ Если вы допустили ошибку, просто отправьте исправленное сообщение еще раз.</em>"
            await message.reply(success_message, reply_markup=keyboard, parse_mode="HTML")
        else:
            await message.reply("Ошибка формата номера тикета", parse_mode="HTML")
                
    if user_position == 'edit_company_name':
        sql.update_profile_data(user_id, 'organization', message.text)
        text, keyboard = my_company(user_id)
        await message.reply(text, reply_markup=keyboard, parse_mode="HTML")


    if user_position == 'edit_company_adress':
        sql.update_profile_data(user_id, 'organization_adress', message.text)
        text, keyboard = my_company(user_id)
        await message.reply(text, reply_markup=keyboard, parse_mode="HTML")

    if user_position == 'edit_company_inn':
        sql.update_profile_data(user_id, 'organization_inn', message.text)
        text, keyboard = my_company(user_id)
        await message.reply(text, reply_markup=keyboard, parse_mode="HTML")
        
    if user_position == 'edit_company_phone':
        sql.update_profile_data(user_id, 'organization_phone', message.text)
        text, keyboard = my_company(user_id)
        await message.reply(text, reply_markup=keyboard, parse_mode="HTML")
        
    if user_position == 'new_ticket':
        user_ticket = user_id
        organization = organization_name
        addres_ticket = organization_address
        message_ticket = message.text
        time_ticket = message.date
        state_ticket = "В работе"
        ticket_comm = ""

        # Добавляем новую заявку в базу данных
        sql.add_ticket(user_ticket, organization, addres_ticket, message_ticket, time_ticket, state_ticket, ticket_comm)
        # Получаем номер последней добавленной заявки
        last_ticket_number = sql.get_last_ticket_number()

        if last_ticket_number:
            # Обновляем профиль пользователя с номером последней добавленной заявки
            sql.update_profile_data(user_id, 'history_ticket', str(last_ticket_number))
            sql.update_profile_data(user_id, 'data_ticket', str(time_ticket))
            sql.update_profile_data(user_id, 'user_name', str(username))
            

            # Меню благодарочки
            text, keyboard = done_ticket(user_id)
            await message.reply(text, reply_markup=keyboard, parse_mode="HTML")

            builder = InlineKeyboardBuilder()
            builder.button(text="🤘Тикет меню🫰", callback_data="admin_panel")
            keyboard_markup = builder.as_markup()
            
            # Отправка сообщения администратору
            admin_text = (f"📬❗️\nПользователь @{username} создал новую заявку с номером <code>#{last_ticket_number}</code>."
                        f"\n\n<b>Сообщение от пользователя:</b>\n - <em>{message_ticket}</em>"
                        f"\n\n<b>Телефон:</b> {organization_phone}\n"
                        f"<b>Компания:</b> {organization}\n"
                        f"<b>Адрес:</b> {addres_ticket}\n"
            )
            
            # Добавляем клавиатуру к уведомлению
            await bot.send_message(ADMIN_MESSAGE, admin_text, parse_mode="HTML", reply_markup=keyboard_markup)
        else:
            await message.reply("Ошибка при получении заявки.")
            

# Основная функция запуска бота
async def main():
    try:
        print("Бот запущен...")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
