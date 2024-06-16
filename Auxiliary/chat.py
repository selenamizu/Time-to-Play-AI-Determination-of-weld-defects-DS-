import telebot
from loguru import logger
from Auxiliary import config
from time import sleep
from ultralytics import YOLO
import os
import torch

bot = telebot.TeleBot(config.BOT_TOKEN, parse_mode='html')


class Message:
    def __init__(self, text: str, buttons=None, *from_buttons, func=lambda *args: None, photo=None):
        self.__text = text  # Текст сообщения
        self.__buttons = buttons  # Двумерный кортеж с кнопками в виде InlineKeyboardButton
        self.__board_tg = None  # Клавиатура кнопок под сообщением: InlineKeyboardMarkup
        self.__photo = photo
        if buttons:
            self.__board_tg = telebot.types.InlineKeyboardMarkup()
            for row in (map(lambda x: x.button_tg, buttons1D) for buttons1D in buttons):
                self.__board_tg.row(*row)
        for from_button in from_buttons:  # Кнопки которые ведут к этому сообщению
            from_button.to_messages += (self,)
        self.__func = func  # Функция, которая должна происходить при вызове сообщения

    def __call__(self, *args):
        return self.__func(*args)

    def __getitem__(self, item):
        return self.__buttons[item[0]][item[1]]

    def new_line(self, message_tg, delete_message=True, userSendLogger=True):
        if userSendLogger:
            self.userSendLogger(message_tg)
        if delete_message:
            try:
                bot.delete_message(message_tg.chat.id, message_tg.id)
            except:
                pass
        return self.__botSendMessage(message_tg)

    def old_line(self, message_tg, text=None, userSendLogger=False):
        if userSendLogger:
            self.userSendLogger(message_tg, text)
        if self.__photo is not None:
            return self.new_line(message_tg)
        return self.__botEditMessage(message_tg)

    @staticmethod
    def __trueText(text, message_tg):
        return text.replace("<ID>", str(message_tg.chat.id)).replace("<USERNAME>", str(message_tg.chat.username))

    @staticmethod
    def userSendLogger(message_tg, text=None):
        if text is None:
            if '\n' in message_tg.text:
                logger.info(f'{message_tg.from_user.username} ({message_tg.chat.id}): \n{message_tg.text}')
            else:
                logger.info(f'{message_tg.from_user.username} ({message_tg.chat.id}): {message_tg.text}')
        else:
            if '\n' in text:
                logger.info(f'{message_tg.chat.username} ({message_tg.chat.id}): \n{text}')
            else:
                logger.info(f'{message_tg.chat.username} ({message_tg.chat.id}): {text}')

    def __botSendMessage(self, message_tg, parse_mode='MARKDOWN', indent=3):
        text = self.__trueText(self.__text, message_tg)
        botMessage = bot.send_message(chat_id=message_tg.chat.id, text=text,
                                      reply_markup=self.__board_tg, parse_mode=parse_mode) \
            if self.__photo is None else bot.send_photo(
            chat_id=message_tg.chat.id, photo=self.__photo, caption=text,
            reply_markup=self.__board_tg, parse_mode=parse_mode)

        if self.__board_tg is None:
            if '\n' in text:
                logger.info(f"{config.Bot} ({botMessage.chat.username}, {message_tg.chat.id}):\n{text}\n")
            else:
                logger.info(f"{config.Bot} ({botMessage.chat.username}, {message_tg.chat.id}): {text}")
        else:
            reply_markup_text = ''
            for reply_markup1 in botMessage.json['reply_markup']['inline_keyboard']:

                for reply_markup2 in reply_markup1:
                    reply_markup_text += f'[{reply_markup2["text"]}]' + (' ' * indent)
                reply_markup_text = reply_markup_text[:-indent]

                reply_markup_text += '\n'
            reply_markup_text = reply_markup_text[:-1]
            logger.info(
                f"{config.Bot} ({botMessage.chat.username}, {message_tg.chat.id}):\n{text}\n{reply_markup_text}\n")
        return botMessage

    def __botEditMessage(self, message_tg, parse_mode='MARKDOWN', indent=3):
        text = self.__trueText(self.__text, message_tg)
        try:
            botMessage = bot.edit_message_text(chat_id=message_tg.chat.id, message_id=message_tg.id, text=text,
                                               reply_markup=self.__board_tg,
                                               parse_mode=parse_mode)
        except:
            try:
                bot.delete_message(chat_id=message_tg.chat.id, message_id=message_tg.id)
            except:
                pass
            botMessage = bot.send_message(chat_id=message_tg.chat.id, text=text,
                                          reply_markup=self.__board_tg, parse_mode=parse_mode)

        if self.__board_tg is None:
            if '\n' in text:
                logger.info(f"{config.Bot} ({botMessage.chat.username}, {message_tg.chat.id}):\n{text}\n")
            else:
                logger.info(f"{config.Bot} ({botMessage.chat.username}, {message_tg.chat.id}): {text}")
        else:
            reply_markup_text = ''
            for reply_markup1 in botMessage.json['reply_markup']['inline_keyboard']:

                for reply_markup2 in reply_markup1:
                    reply_markup_text += f'[{reply_markup2["text"]}]' + (' ' * indent)
                reply_markup_text = reply_markup_text[:-indent]

                reply_markup_text += '\n'
            reply_markup_text = reply_markup_text[:-1]
            logger.info(
                f"{config.Bot} ({botMessage.chat.username}, {message_tg.chat.id}):\n{text}\n{reply_markup_text}\n")
        return botMessage


class Button:
    instances = list()  # Список со всеми объектами класса

    def __init__(self, text: str, callback_data: str, *to_messages: Message,
                 func=lambda to_messages, message_tg: None):
        self.text = text  # текст кнопки
        self.callback_data = callback_data  # Скрытые (уникальные) данные, несущиеся кнопкой
        self.button_tg = telebot.types.InlineKeyboardButton(
            self.text, callback_data=self.callback_data)  # кнопка в виде объекта InlineKeyboardButton
        self.to_messages = to_messages  # Сообщения, к которым ведёт кнопка
        self.__func = func  # Функция отбора сообщения из to_messages на основе предыдущего сообщения / вспомогательное
        self.instances.append(self)

    def __call__(self, message_tg,
                 userSendLogger=True) -> Message:  # При вызове кновки отдаем сообщение к которому будем идти
        if userSendLogger:
            Message.userSendLogger(message_tg, f'[{self.text}]')
        if self.__func(self.to_messages, message_tg) is not None:
            return self.__func(self.to_messages, message_tg)
        if self.to_messages:
            return self.to_messages[0]

    def __getattr__(self, callback_data):  # выполняем поиск кнопки по её скрытым данным, т.к они уникальные
        for instance in self.instances:
            if instance.callback_data == callback_data:
                return instance


# Functions for button
def delete_message(_, message_tg):
    bot.delete_message(message_tg.chat.id, message_tg.id)


def clear_next_step_handler(_, message_tg):
    bot.clear_step_handler_by_chat_id(
        message_tg.chat.id)  # просто очищаем step_handler
    # ничего не возращаем, чтобы дальше шло как с обычными кнопками


# Functions for message
def check(from_message):
    botMessage = message_check.old_line(from_message)
    try:
        bot.register_next_step_handler(botMessage, check_processing_decorator(botMessage))
    except Exception as e:
        print(e)
    return True


def check_processing_decorator(botMessage):
    def check_processing(message_tg):
        nonlocal botMessage

        Message.userSendLogger(message_tg, "<FILE>")
        botMessage = message_check_processing.old_line(botMessage)
        bot.delete_message(message_tg.chat.id, message_tg.id)

        try:
            # Получаем файл фото
            file = message_tg.photo[-1] if message_tg.photo else message_tg.document
            file_info = bot.get_file(
                file.file_id)  # Поставить индекс в соответствии с качеством (от худжего к лучшему)

            src_received = f"images/received/{file_info.file_path.split('/')[-1]}"
            src_processed = f"images/processed/{file_info.file_path.split('/')[-1]}"

            if not os.path.exists(src_received):
                assert file_info.file_path.split('.')[-1] in ('jpg', 'jpeg', 'png'), 'Файл не является изображением'

                downloaded_file = bot.download_file(file_info.file_path)

                # Очищаем папку
                folder_path = "images/received"
                if len(os.listdir(folder_path)) >= 5:
                    images_lst = list(map(lambda image_name: os.path.join(folder_path, image_name),
                                          os.listdir(folder_path)))
                    os.remove(min(images_lst, key=os.path.getctime))

                # Сохраняем файл
                with open(src_received, 'wb') as new_file:
                    new_file.write(downloaded_file)

            # Check image
            model = YOLO("Auxiliary/model/filter.pt")
            result = model(src_received)[0]

            assert result.probs.data.argmax(), "Изображение не соответствует задаче"

            # ML processing
            model = YOLO('Auxiliary/model/best.pt')  # pretrained YOLOv8n model

            # Run batched inference on a list of images
            result = model(src_received)[0]  # return Result object
            objects = list(map(result.names.get, result.boxes.cls.to(torch.int).tolist()))
            quantity = {obj.title(): objects.count(obj) for obj in set(objects)}

            if not os.path.exists(src_processed):
                # Очищаем папку
                folder_path = "images/processed"
                if len(os.listdir(folder_path)) >= 5:
                    images_lst = list(map(lambda image_name: os.path.join(folder_path, image_name),
                                          os.listdir(folder_path)))
                    os.remove(min(images_lst, key=os.path.getctime))

                # Сохраняем файл
                result.save(filename=src_processed)  # save to disk

            # Send result
            with open(src_processed, 'rb') as image:
                Message(f"*Было найдено {len(objects)} деффектов!*\n" +
                        (f"_Описание:_\n" +
                         "\n".join(f'*{key}:* `{value}`' for key, value in
                                   sorted(quantity.items(), reverse=True, key=lambda data: data[1]))
                         if len(objects) else "_Поздравляем, данный шов пригоден_"),
                        ((button.check_again,), (button.back_to_start,),), photo=image).old_line(
                    botMessage)

        except:
            botMessage = Message("*Данный файл не является изображением со швами!*").old_line(botMessage)
            sleep(3)
            message_check(botMessage)

    return check_processing


# Buttons
button = Button('', '')

Button("Загрузить", "check")
Button("Загрузить снова", "check_again")

Button("🔙 Назад 🔙", "back_to_start")

Button("❌ Отменить ❌", "cancel_check", func=clear_next_step_handler)
Button("❌ Закрыть ❌", "close", func=delete_message)

# Messages
message_contacts = Message("*Наши контакты:*\n"
                           "├ `Родионова Кристина` -> @Sefixnep\n"
                           "├ `Березина Алёна` -> @mizzzu23\n"
                           "├ `Рябов Денис` -> @denpower\n"
                           "├ `Андрей Глинский` -> @AI\_glinsky\n"
                           "└ `Дементьев Эдуард` -> @SilaVelesa",
                           ((button.close,),))

message_start = Message("*Привет <USERNAME>*!\n"
                        "_Этот бот поможет Вам определить дефекты сварочных швов, давайте приступим.\n"
                        "Вы можете загрузить одно изображение, которое хотите проверить._",
                        ((button.check,),),
                        button.cancel_check, button.back_to_start)

message_check = Message("*Отправьте одно изображение для обработки:*",
                        ((button.cancel_check,),),
                        button.check,
                        button.check_again,
                        func=check)

message_check_processing = Message("Изображение обрабатывается")

message_error = Message("Данный файл не является изображением!")
