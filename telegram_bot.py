import telebot
import logging
subscribed_users = []
import threading

aiBOT_token = "<INPUT YOUR TELEGRAM TOKEN>"
aiBot = telebot.TeleBot(aiBOT_token)
mostViewed_bot_token= "<INPUT YOUR TELEGRAM TOKEN>"
mostViewed_bot = telebot.TeleBot(mostViewed_bot_token)
# Set up logging
logging.basicConfig(level=logging.INFO)
# Handle /start command
@aiBot.message_handler(commands=['start'])
def handle_start(message):
    chat_id = message.chat.id
    if chat_id not in subscribed_users:
        subscribed_users.append(chat_id)
        aiBot.send_message(chat_id, "You have subscribed to AI tokens notifications!")
    else:
        aiBot.send_message(chat_id, "You are already subscribed!")

# subscribed_users.append("7150168192")
# Handle /start command
@mostViewed_bot.message_handler(commands=['start'])
def handle_start(message):
    chat_id = message.chat.id
    if chat_id not in subscribed_users:
        subscribed_users.append(chat_id)
        mostViewed_bot.send_message(chat_id, "You have subscribed to latest solana viewed tokens!")
    else:
        mostViewed_bot.send_message(chat_id, "You are already subscribed!")

def send_telegram_notification(message):      
    logging.info("send notification to telegram")
    for user_id in subscribed_users:
        try:
            aiBot.send_message(user_id, message)
        except Exception as e:
            print(f"Failed to send message to {user_id}: {e}")

def send_most_viewed_telegram_notification(token):      
    logging.info("send most viewed notification .")
    token_address=token["mint"]
    score=token["score"]
    visits= token["visits"]
    message = f"new most viewed Token Found with score : " + str(score) + " "+ "and visits " +str(visits)+ "  " +"https://dexscreener.com/solana/"+str(token_address)
    for user_id in subscribed_users:
        try:
            mostViewed_bot.send_message(user_id, message)
        except Exception as e:
            print(f"Failed to send message to {user_id}: {e}")

def start_ai_bot():
    aiBot.polling(non_stop=True)

def start_most_viewed_bot():
    mostViewed_bot.polling(non_stop=True)

bot_thread = threading.Thread(target=start_ai_bot)
bot_thread.start()

mostViewed_bot_thread = threading.Thread(target=start_most_viewed_bot)
mostViewed_bot_thread.start()