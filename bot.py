import os
import telebot
from dotenv import load_dotenv
import database

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set!")

# Threaded=False is required for single-threaded environment when using Flask webhook routing.
bot = telebot.TeleBot(TOKEN, threaded=False)

@bot.message_handler(commands=['start'])
def handle_start(message):
    chat_id = message.chat.id
    if database.add_user(chat_id):
        reply = (
            "✈️ **Ethiopian Airlines Careers Results Bot** ✈️\n\n"
            "Welcome! You have successfully subscribed to career results notifications.\n\n"
            "🎯 You will receive immediate alerts when new announcements matching **AMT (Aircraft Maintenance Technician)** or **Pilot** positions are posted.\n\n"
            "ℹ️ **Commands:**\n"
            "📋 /status - Check subscription status\n"
            "❌ /stop - Unsubscribe from alerts\n"
            "❓ /help - Show help details"
        )
    else:
        reply = "⚠️ An error occurred while subscribing. Please try again later."
    
    send_telegram_msg(chat_id, reply)

@bot.message_handler(commands=['stop', 'unsubscribe'])
def handle_stop(message):
    chat_id = message.chat.id
    if database.remove_user(chat_id):
        reply = "❌ You have successfully unsubscribed. You will no longer receive result notifications."
    else:
        reply = "⚠️ An error occurred while unsubscribing. Please try again."
    
    send_telegram_msg(chat_id, reply)

@bot.message_handler(commands=['status'])
def handle_status(message):
    chat_id = message.chat.id
    is_subbed = database.is_user_subscribed(chat_id)
    if is_subbed:
        reply = (
            "🔔 **Subscription Status: ACTIVE**\n\n"
            "You are set to receive alerts for:\n"
            "• Aircraft Maintenance Technicians (AMT)\n"
            "• Pilot positions\n\n"
            "To turn off alerts, use /stop."
        )
    else:
        reply = (
            "🔕 **Subscription Status: INACTIVE**\n\n"
            "You are currently not subscribed. Use /start to subscribe and start receiving announcements."
        )
    
    send_telegram_msg(chat_id, reply)

@bot.message_handler(commands=['help'])
def handle_help(message):
    chat_id = message.chat.id
    reply = (
        "✈️ **Ethiopian Airlines Careers Results Bot Help** ✈️\n\n"
        "This bot monitors the Ethiopian Airlines results portal for new announcements related to Aircraft Maintenance and Pilot careers.\n\n"
        "**Commands:**\n"
        "🚀 /start - Subscribe to matching results\n"
        "📋 /status - Verify your subscription status\n"
        "❌ /stop - Unsubscribe\n"
        "❓ /help - Display this command helper guide"
    )
    
    send_telegram_msg(chat_id, reply)

def send_telegram_msg(chat_id, text, markdown=True):
    """
    Sends a message to a specific chat ID. If markdown parsing fails,
    retries in plain text mode to guarantee message delivery.
    """
    try:
        if markdown:
            bot.send_message(chat_id, text, parse_mode="Markdown", disable_web_page_preview=True)
        else:
            bot.send_message(chat_id, text, disable_web_page_preview=True)
        return True
    except Exception as e:
        err_msg = str(e).lower()
        if "can't parse entities" in err_msg or "bad request" in err_msg:
            # Fallback to plain text if Markdown parsing fails
            try:
                # Remove Markdown asterisks/brackets to make clean plain text
                clean_text = text.replace("**", "").replace("*", "").replace("`", "")
                bot.send_message(chat_id, clean_text, disable_web_page_preview=True)
                return True
            except Exception as e2:
                print(f"Fallback plain text sending failed to chat {chat_id}: {e2}")
        else:
            print(f"Error sending message to chat {chat_id}: {e}")
            
        # Clean up database if user blocked bot, kicked it, or chat was deleted
        if "blocked" in err_msg or "chat not found" in err_msg or "kicked" in err_msg or "deactivated" in err_msg:
            print(f"Auto-unsubscribing inactive chat ID: {chat_id}")
            database.remove_user(chat_id)
            
        return False

def broadcast_announcement(announcement):
    """
    Broadcasts a new matching result announcement to all subscribed Telegram users.
    """
    users = database.get_all_users()
    if not users:
        print("No active subscribers to notify.")
        return 0
        
    position = announcement.get("position", "Unknown Position")
    location = announcement.get("location", "Ethiopian Airlines")
    ann_type = announcement.get("announcement_type", "ANNOUNCEMENT")
    desc = announcement.get("description", "")
    
    # Truncate description to fit Telegram message limits
    max_desc_len = 2000
    if len(desc) > max_desc_len:
        desc = desc[:max_desc_len] + "\n\n*(Description truncated. View full details online)*"
        
    message = (
        f"✈️ **NEW RESULT ANNOUNCEMENT** ✈️\n\n"
        f"📌 **Position:** {position}\n"
        f"📍 **Location:** {location}\n"
        f"📢 **Type:** {ann_type}\n\n"
        f"📝 **Description:**\n"
        f"{desc}\n\n"
        f"🔗 [View Careers Page](https://corporate.ethiopianairlines.com/AboutEthiopian/careers/results)"
    )
    
    sent_count = 0
    for chat_id in users:
        if send_telegram_msg(chat_id, message, markdown=True):
            sent_count += 1
            
    return sent_count
