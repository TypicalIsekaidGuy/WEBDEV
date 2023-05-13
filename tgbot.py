import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from yookassa import Configuration, Payment
from yookassa.domain.request import PaymentRequest
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils import executor
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import sqlite3 as sql
from PIL import Image
import io
from io import BytesIO


#Print Hello

Configuration.account_id = '204988'
Configuration.secret_key = 'test_C3nuO7SxYNVWYmwCwfc7_O24x8q8KDtFA_1ruXUhuWg'

API_TOKEN = '6041845486:AAHo9a8_yHBB2sM2_b05e-W0_0SaJc6uLSc'

# logging.basicConfig(level=logging.INFO)
logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

materials = {
    '1': {"title": "Математика база", "price": 199, "file_id": "file_id_1"},
    '2': {"title": "Математика Профиль", "price": 299, "file_id": "file_id_2"},
    '3': {"title": "Все по скидке (для себя и для друга)", "price": 349, "file_id": "file_id_3"}
}
user_payments = {}

global isAdmin
global chat_id
global idea_index
idea_index = 0
isAdmin = False

def create_yookassa_payment(amount, material_title):
    payment_data = {
        "amount": {
            "value": amount,
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": "https://t.me/your_bot_username"
        },
        "capture": True,
        "description": material_title
    }

    payment_request = PaymentRequest(payment_data)
    payment = Payment.create(payment_request)

    return payment


async def check_payment(payment_id: str) -> bool:
    # Получить информацию о платеже от Kassa
    try:
        payment_info = Payment.find_one(payment_id)

        # Если статус платежа равен "succeeded", платеж успешно выполнен
        if payment_info.status == "succeeded":
            return True

    except Exception as e:
        print(f"Error while checking payment: {e}")

    return False

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    global chat_id
    chat_id = message.chat.id
    # Connecting to sqlite
    conn = sql.connect('Orders.db')

    # Creating a cursor object using the cursor() method
    cursor = conn.cursor()

    cursor.execute('SELECT Key FROM Admins')

    # Fetch all the rows returned by the query
    rows = cursor.fetchall()
    # Iterate over the rows and print the values in the "Key" column
    for row in rows:
        if(row[0] == message.chat.id):
            break #only for debug remove if completed block for users
            global isAdmin
            isAdmin = True
            cursor.execute('SELECT Name, "Middle name", Surname FROM Admins WHERE Key=?', (row[0],))
            FIO = cursor.fetchall()
            await bot.send_message(message.chat.id, 'Здравствуйте, админ: ' + FIO[0][0] + ' ' + FIO[0][1] +' ' + FIO[0][2])
            await send_welcome_message_admin(message.from_user.id)
            cursor.close()
            conn.close()
            return
    cursor.close()
    conn.close()
    await send_welcome_message_user(message.from_user.id)

async def send_welcome_message_user(chat_id):
    welcome_keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton("Предложить идею разработчику/коллаборировать", callback_data="give_idea"))
    welcome_keyboard.add(InlineKeyboardButton("Посмотреть продукты", callback_data="get_products"))
    await bot.send_message(chat_id,
                           "Добро пожаловать в нашего бота!\n\n"
                           "Что вы хотите сделать?",
                           reply_markup=welcome_keyboard)

async def send_welcome_message_admin(chat_id):
    welcome_keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton("Просмотреть предложения", callback_data="get_idea"))
    welcome_keyboard.add(InlineKeyboardButton("Добавить продукт", callback_data="create_order"))
    await bot.send_message(chat_id,
                           "Что вы хотите сделать?",
                           reply_markup=welcome_keyboard)

"""
async def send_welcome_message(chat_id):
    welcome_keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton("Показать доступные материалы", callback_data="show_materials"))
    welcome_keyboard.add(InlineKeyboardButton("Проверить оплату", callback_data="check_paid_order"))

    await bot.send_message(chat_id,
                           "Добро пожаловать в нашего бота для продажи авторских материалов по подготовке к ЕГЭ по математике!\n\n"
                           "Нажмите кнопку 'Показать доступные материалы' ниже, "
                           "чтобы увидеть список материалов, доступных для покупки.\n\n"
                           "Используйте кнопку 'Проверить оплату', если хотите проверить статус ранее сделанного заказа.",
                           reply_markup=welcome_keyboard)"""

@dp.callback_query_handler(lambda call: call.data == "give_idea")
async def enter_payment_id(call: types.CallbackQuery):
    await bot.answer_callback_query(call.id)
    global mode
    mode = 'contacts'
    await bot.send_message(call.message.chat.id, "Введите пожалуйста ваши контактные данные (email, tg, vk, телефон или что-то другое, где вы сможете ответить)")

@dp.callback_query_handler(lambda call: call.data == "give_idea")
async def enter_payment_id(call: types.CallbackQuery):
    await bot.answer_callback_query(call.id)
    await bot.send_message(call.message.chat.id, "Введите пожалуйста ваши контактные данные (email, tg, vk, телефон или что-то другое, где вы сможете ответить)")

@dp.callback_query_handler(lambda call: call.data == "get_idea")
async def get_idea(call: types.CallbackQuery):
    global idea
    conn = sql.connect('Orders.db')
    kb = InlineKeyboardMarkup()
    c = conn.cursor()
    # Execute a SELECT query to count the number of rows in the table
    c.execute("SELECT COUNT(*) FROM Proposals")

    # Fetch the result
    result = c.fetchone()

    # Check if any rows exist in the table
    if (result[0] > 0)&(idea_index<result[0]):
        print(result[0])
        print(idea_index)
        c.execute('SELECT * FROM Proposals')
        idea = c.fetchall()
    else:
        await bot.send_message(call.message.chat.id, "Пока что больше вам никто не писал")
        conn.commit()
        conn.close()
        await send_welcome_message_admin(chat_id)
    conn.commit()
    conn.close()
    kb.add(InlineKeyboardButton("Принять предложение", callback_data="submit_idea"))
    kb.add(InlineKeyboardButton("Отклонить предложение", callback_data="cancel_idea"))
    await bot.answer_callback_query(call.id)
    await bot.send_message(call.message.chat.id, "Кто-то хочет предложить вам идею:" + idea[idea_index][1],reply_markup=kb)

def delete_idea():
    global idea_index
    idea_index+=1
    try:
        conn = sql.connect('Orders.db')
        c = conn.cursor()
        c.execute('DELETE FROM Proposals WHERE rowid=1')
        conn.commit()
    except sql.Error as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()

@dp.callback_query_handler(lambda call: call.data == "submit_idea")
async def enter_payment_id(call: types.CallbackQuery):
    await bot.answer_callback_query(call.id)
    global idea
    await bot.send_message(call.message.chat.id, "Раз вам понравилась идея, то вот контактные данные:  "+idea[idea_index][0],reply_markup=return_end_keyboard())

@dp.callback_query_handler(lambda call: call.data == "cancel_idea")
async def enter_payment_id(call: types.CallbackQuery):
    await bot.answer_callback_query(call.id)
    await bot.send_message(call.message.chat.id, "Идея отклонена",reply_markup=return_end_keyboard())

def return_end_keyboard():
    welcome_keyboard = InlineKeyboardMarkup()
    welcome_keyboard.add(InlineKeyboardButton("Продолжить смотреть предложения", callback_data="continue_getting"))
    welcome_keyboard.add(InlineKeyboardButton("Вернутся обратно", callback_data="return_admin"))
    return welcome_keyboard


@dp.callback_query_handler(lambda call: call.data == "continue_getting")
async def enter_payment_id(call: types.CallbackQuery):
    delete_idea()
    await get_idea(call)

@dp.callback_query_handler(lambda call: call.data == "return_admin")
async def enter_payment_id(call: types.CallbackQuery):
    delete_idea()
    await bot.answer_callback_query(call.id)
    await send_welcome_message_admin(chat_id)

class CheckingPayment(StatesGroup):
    waiting_for_payment_id = State()


@dp.callback_query_handler(lambda call: call.data == "get_products")
async def enter_payment_id(call: types.CallbackQuery):
    await bot.answer_callback_query(call.id)
    await bot.send_message(call.message.chat.id, "Вот список доступных на данный момент продуктов:")
    global product_index
    product_index = 0
    conn = sql.connect('Orders.db')
    c = conn.cursor()
    c.execute('SELECT * FROM Products')
    products = c.fetchall()
    conn.commit()
    conn.close()
    for p in products:
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("Купить продукт: "+str(p[3]), callback_data=f"buy_product_{p[0]}"))
        image_stream = io.BytesIO(p[4])
        await bot.send_photo(chat_id,InputFile(image_stream, filename='photo.jpg'),caption=str(p[1]) +
                               '\n' +"Описание: " + str(p[2]) +
                               '\nЦена: '+str(p[3]),reply_markup=kb)

"""        # read the byte code into an io.BytesIO object
        byte_stream = io.BytesIO(p[4]).encode('utf-8')

        # open the image from the byte stream
        image = Image.open(byte_stream)

        await bot.send_photo(chat_id,photo=image)"""



"""@dp.callback_query_handler(lambda call: call.data == "check_paid_order")
async def enter_payment_id(call: types.CallbackQuery):
    await bot.answer_callback_query(call.id)
    await bot.send_message(call.message.chat.id, "Введите Код платежа для проверки:")
    await CheckingPayment.waiting_for_payment_id.set()"""

@dp.callback_query_handler(lambda call: call.data.startswith("buy_product_"))
async def process_callback_buy(call: types.CallbackQuery):
    conn = sql.connect('Orders.db')
    c = conn.cursor()

    material_number = call.data.split("_")[2]
    for i in material_number:
        c.execute("SELECT Name, Price FROM Products WHERE `Index`=?", (i,))
        result = c.fetchone()
        material_title = result[0]
        material_price = result[1]
    conn.commit()
    conn.close()

    # Создаем платеж и получаем ссылку на оплату
    print(material_price,material_title)
    payment = create_yookassa_payment(material_price, material_title)
    payment_url = payment.confirmation.confirmation_url

    # Сохраняем payment_id для данного пользователя
    user_id = call.from_user.id
    user_payments[user_id] = payment.id

    if payment_url:
        pay_keyboard = InlineKeyboardMarkup().add(
            InlineKeyboardButton("Оплатить", url=payment_url),
            InlineKeyboardButton("Проверить платеж", callback_data=f"check_payment_{payment_url.split('orderId=')[1]}")
        )

        await bot.send_message(
            chat_id,
            f"Вы выбрали материал \"{material_title}\". "
            f"Для оплаты нажмите кнопку 'Оплатить', после оплаты нажмите 'Проверить платеж':",
            reply_markup=pay_keyboard)

@dp.callback_query_handler(lambda call: call.data == "create_order")
async def enter_payment_id(call: types.CallbackQuery):
    global mode
    mode = 'name'
    await bot.answer_callback_query(call.id)
    await bot.send_message(call.message.chat.id, "Введите название игры:")

@dp.message_handler(lambda message: message.text, state=CheckingPayment.waiting_for_payment_id)
async def check_payment_by_id(message: types.Message, state: FSMContext):
    payment_id = message.text

    if payment_id in user_payments.values():
        user_id = [key for key, value in user_payments.items() if value == payment_id][0]
        material_number = user_payments.get(user_id)

        if material_number:
            await bot.send_message(message.chat.id, "Платеж успешен! Вот ваш заказ:")
            await bot.send_document(chat_id=message.chat.id, document=materials[material_number]["file_id"])
        else:
            await bot.send_message(message.chat.id,
                                   "Не удалось найти информацию о заказе. Пожалуйста, проверьте Код платежа и попробуйте снова.")
    else:
        await bot.send_message(message.chat.id,
                               "Не удалось найти информацию о платеже. Пожалуйста, проверьте Код платежа и попробуйте снова.")

    # Завершаем текущее состояние
    await state.finish()


@dp.callback_query_handler(lambda call: call.data == "show_materials")
async def show_materials(call: types.CallbackQuery):
    materials_keyboard = InlineKeyboardMarkup(row_width=1)

    for key, value in materials.items():
        button_text = f"{value['title']} - {value['price']} руб."
        materials_keyboard.add(InlineKeyboardButton(button_text, callback_data=f"buy_{key}"))

    materials_keyboard.add(InlineKeyboardButton("Назад", callback_data="go_back"))
    await bot.edit_message_text("Вот список доступных материалов для подготовки к ЕГЭ по математике:\n\n",
                                chat_id=call.message.chat.id,
                                message_id=call.message.message_id,
                                reply_markup=materials_keyboard)


@dp.callback_query_handler(lambda call: call.data == "go_back")
async def go_back(call: types.CallbackQuery):
    await bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
    await send_welcome_message_user(call.message.chat.id)

"""@dp.callback_query_handler(lambda call: call.data.startswith("buy_"))
async def process_callback_buy(call: types.CallbackQuery):
    material_number = call.data.split("_")[1]

    material_title = materials[material_number]["title"]
    material_price = float(materials[material_number]["price"])

    # Создаем платеж и получаем ссылку на оплату
    payment = create_yookassa_payment(material_price, material_title)
    payment_url = payment.confirmation.confirmation_url

    # Сохраняем payment_id для данного пользователя
    user_id = call.from_user.id
    user_payments[user_id] = payment.id

    if payment_url:
        pay_keyboard = InlineKeyboardMarkup().add(
            InlineKeyboardButton("Оплатить", url=payment_url),
            InlineKeyboardButton("Проверить платеж", callback_data=f"check_payment_{payment_url.split('orderId=')[1]}")
        )

        await bot.edit_message_text(
            f"Вы выбрали материал \"{material_title}\". "
            f"Для оплаты нажмите кнопку 'Оплатить', после оплаты нажмите 'Проверить платеж':",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=pay_keyboard)"""


# payment_confirmed = await check_payment(user_payments.get(call.from_user.id))
@dp.callback_query_handler(lambda call: call.data.startswith("check_payment_"))
async def confirm_payment(call: types.CallbackQuery):
    material_number = call.data.split("_")[1]

    # Получаем payment_id для данного пользователя
    user_id = call.from_user.id
    payment_id = user_payments.get(user_id)

    failed_payment_keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton("Проверить еще раз", callback_data=f"check_payment_{material_number}"),
        InlineKeyboardButton("Сделать новый заказ", callback_data="get_products")
    )

    if payment_id:
        payment_confirmed = await check_payment(payment_id)

        if payment_confirmed:
            await send_welcome_message_user(chat_id)

            welcome_keyboard = InlineKeyboardMarkup().add(
                InlineKeyboardButton("Назад", callback_data="give_idea"))
            await bot.answer_callback_query(call.id, text="Ваш платеж подтвержден!")
            await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                        text="Ваш платеж подтвержден!")
            """ Выводит документ (не работает)"""
            """await bot.send_document(chat_id=call.message.chat.id, document=materials[material_number]["file_id"])"""
        else:
            await bot.answer_callback_query(call.id,
                                            text="Не удалось найти информацию о платеже. Пожалуйста, попробуйте  позже.")
            await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                        text="Не удалось найти информацию о платеже. Пожалуйста, попробуйте проверить позже.",
                                        reply_markup=failed_payment_keyboard)
    else:
        await bot.answer_callback_query(call.id,
                                        text="Не удалось найти информацию о платеже. Пожалуйста, попробуйте проверить позже.")
        await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                    text="Не удалось найти информацию о платеже. Пожалуйста, попробуйте проверить позже.",
                                    reply_markup=failed_payment_keyboard)

#обработка любого сообщения, которого ввел пользователь
@dp.message_handler(content_types="text")
async def get_b(message: types.Message):
    global mode
    global isAdmin
    global contacts
    global name
    global description
    global price
    answer = message.text
    if(not isAdmin):
        if(mode=='contacts'):
            # Insert the value of "it" into the "Contacts" column of the "Proposals" table
            mode = 'idea'
            contacts = answer
            await bot.send_message(message.chat.id, "Введите пожалуйста ваше предложение")
        elif(mode=='idea'):
            conn = sql.connect('Orders.db')
            c = conn.cursor()
            c.execute("INSERT INTO Proposals (Contacts, Idea) VALUES (?,?)", (contacts, answer,))
            # Commit the transaction and close the connection
            conn.commit()
            conn.close()
            await send_welcome_message_user(message.from_user.id)
        elif(mode=='name'):
            name = answer
            await bot.send_message(message.chat.id, "Введите пожалуйста описание продукта")
            mode = 'description'
        elif(mode=='description'):
            description = answer
            await bot.send_message(message.chat.id, "Введите цену")
            mode = 'price'
        elif(mode=='price'):
            price = answer
            await bot.send_message(message.chat.id, "Загрузите картинку снапшота")
            mode = 'snapshot'
        else:
            await bot.send_message(message.chat.id, "Пожалуйста ничего не вводите, пока бот вас не попросит")
    elif(isAdmin):
        if(mode=='name'):
            name = answer
            await bot.send_message(message.chat.id, "Введите пожалуйста описание продукта")
            mode = 'description'
        elif(mode=='description'):
            description = answer
            await bot.send_message(message.chat.id, "Введите цену")
            mode = 'price'
        elif(mode=='price'):
            try:
                price = int(answer)
            except:
                await bot.send_message(message.chat.id, "Цена указывается в целых числах, попробуйте еще раз")
            await bot.send_message(message.chat.id, "Загрузите картинку снапшота")
            mode = 'snapshot'
        else:
            await bot.send_message(message.chat.id, "Пожалуйста ничего не вводите, пока бот вас не попросит")


@dp.message_handler(content_types=types.ContentTypes.PHOTO)
async def handle_photo_message(message: types.Message):
    global mode
    if(isAdmin):
        if (mode == 'snapshot'):
            file_id = message.photo[-1].file_id
            # download the photo file
            photo = await bot.download_file_by_id(file_id)
            image_byte = BytesIO(photo.getvalue())

            conn = sql.connect('Orders.db')
            c = conn.cursor()
            c.execute("INSERT INTO Products (Name, Description, Price, Image) VALUES (?,?,?,?)", (str(name), str(description), 1, image_byte.getvalue(),))
            # Commit the transaction and close the connection
            conn.commit()
            conn.close()
            await send_welcome_message_admin(message.from_user.id)
        else:
            await bot.send_message(message.chat.id, "Пожалуйста ничего не вводите, пока бот вас не попросит")


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
