from Auxiliary.chat import *


@bot.message_handler(commands=["start"])
def start(message_tg):
    message_start.new_line(message_tg)


@bot.message_handler(commands=["contacts"])
def contacts(message_tg):
    message_contacts.new_line(message_tg)


@bot.callback_query_handler(func=lambda call: True)
def callback_reception(call):
    commands = []

    to_message = None
    from_button = getattr(button, call.data)

    if from_button:
        to_message = getattr(button, call.data)(call.message)

    for command in commands:
        if call.data.split(split)[-1] == command:
            command_data = call.data.split(split)[:-1]  # Данные передавающиеся кнопкой
            break
    else:
        if to_message is not None and to_message(
                call.message) is None:  # Вызываем функцию, если там нет return, то делаем old_line
            to_message.old_line(call.message)  # Выводить сообщение к которому ведет кнопка

    bot.answer_callback_query(callback_query_id=call.id, show_alert=False)


@bot.message_handler(content_types=['text'])
def watch(message_tg):
    Message.userSendLogger(message_tg)


if __name__ == '__main__':
    print(f"link: https://t.me/{config.Bot}")
    logger.info(f'{config.Bot} start')

bot.infinity_polling()
