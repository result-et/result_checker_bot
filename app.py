import os
import time
import threading
from flask import Flask, request, jsonify, render_template, abort
from dotenv import load_dotenv
import database
import scraper
import bot

load_dotenv()

app = Flask(__name__)

# Ensure database tables exist
database.init_db()

def pre_populate_db():
    """Checks if the announcements table is empty on startup and populates it if needed."""
    try:
        stats = database.get_stats()
        if stats.get('total_announcements', 0) == 0:
            print("Announcements cache is empty. Pre-populating historical data...")
            scraped_items = scraper.scrape_announcements()
            for item in scraped_items:
                database.add_announcement(
                    announcement_id=item['id'],
                    position=item['position'],
                    location=item['location'],
                    announcement_type=item['announcement_type'],
                    is_matching=item['is_matching']
                )
            print(f"Successfully pre-populated database with {len(scraped_items)} announcements.")
    except Exception as e:
        print(f"Error pre-populating database on startup: {e}")

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Webhook endpoint for Telegram bot
@app.route(f"/{TOKEN}", methods=['POST'])
def telegram_webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = bot.telebot.types.Update.de_json(json_string)
        bot.bot.process_new_updates([update])
        return '', 200
    else:
        abort(403)

# Dashboard frontend
@app.route('/')
def dashboard():
    stats = database.get_stats()
    latest_announcements = database.get_announcements_summary(limit=50)
    
    # Separate matching announcements for a special section
    matching_announcements = [ann for ann in latest_announcements if ann.get('is_matching')]
    
    return render_template(
        'index.html', 
        stats=stats, 
        latest_announcements=latest_announcements,
        matching_announcements=matching_announcements,
        bot_username="ETH_Airlines_Results_Bot"  # A display name helper
    )

# Scraper trigger endpoint (to be called by cron-job.org or manually)
@app.route('/api/check-results', methods=['GET', 'POST'])
def check_results():
    try:
        # 1. Scrape the Ethiopian Airlines careers page
        scraped_items = scraper.scrape_announcements()
        
        new_count = 0
        matching_count = 0
        sent_notifications = 0
        new_items_list = []
        
        # 2. Process each scraped announcement
        for item in scraped_items:
            item_id = item['id']
            
            # Check if this announcement is new
            if database.is_announcement_new(item_id):
                # Save to database
                database.add_announcement(
                    announcement_id=item_id,
                    position=item['position'],
                    location=item['location'],
                    announcement_type=item['announcement_type'],
                    is_matching=item['is_matching']
                )
                
                new_count += 1
                new_items_list.append(item)
                
                # If matching AMT/Pilot, broadcast to Telegram subscribers
                if item['is_matching']:
                    matching_count += 1
                    # Send alert
                    sent_count = bot.broadcast_announcement(item)
                    sent_notifications += sent_count
                    
        return jsonify({
            "status": "success",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "scraped_total": len(scraped_items),
            "new_added": new_count,
            "matching_filtered": matching_count,
            "telegram_notifications_sent": sent_notifications,
            "new_announcements": [
                {
                    "position": item['position'],
                    "location": item['location'],
                    "type": item['announcement_type'],
                    "is_matching": item['is_matching']
                } for item in new_items_list
            ]
        }), 200
        
    except Exception as e:
        print(f"Error during scheduled run: {e}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }), 500

# Set up Webhook in production or run Polling in local development
def setup_bot():
    if WEBHOOK_URL:
        # Clear webhook if already set, then register again
        bot.bot.remove_webhook()
        time.sleep(1)
        
        webhook_endpoint = f"{WEBHOOK_URL}/{TOKEN}"
        # Set new webhook
        bot.bot.set_webhook(url=webhook_endpoint)
        print(f"Production Webhook Registered: {webhook_endpoint}")
    else:
        # Local development polling mode in background thread
        print("WEBHOOK_URL is not set. Launching background polling thread for local testing...")
        
        def run_polling():
            # Standard infinity polling to keep thread alive and reconnect automatically
            bot.bot.infinity_polling()
            
        polling_thread = threading.Thread(target=run_polling, daemon=True)
        polling_thread.start()

# Initialize bot configuration when starting Flask process
# Flask debug mode runs two processes (autoreloader). We run the bot register only once.
if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
    setup_bot()
    # Start database pre-population in a background thread
    # threading.Thread(target=pre_populate_db, daemon=True).start()

if __name__ == '__main__':
    # Run locally
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
