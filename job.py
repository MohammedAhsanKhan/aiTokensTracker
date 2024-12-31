import logging
import time
from api_client import get_ai_tokens, fetch_trending_tokens
from telegram_bot import send_most_viewed_telegram_notification
from db_operations import get_db_connection,update_token_info, clear_old_low_marketcap_records, clear_trending_table, store_trending_tokens
logging.basicConfig(level=logging.INFO)
# Step 4: Create the batch job that runs every 10 minutes
def aiTrackerJob():
    logging.info("Running the batch job to fetch and store new AI tokens..")
    get_ai_tokens()
    token_addresses=[]
    # Fetch token addresses from the database
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT tokenAddress FROM ai_tokens")
                token_addresses = [row[0] for row in cursor.fetchall()]
        finally:
            conn.close()
    # Update marketcap and token holders for each token
    for token_address in token_addresses:
        update_token_info(token_address)
        # clear the old records after 5 seconds
    time.sleep(5)
    clear_old_low_marketcap_records()

# Trending Token Tracker
def trendingTokensJob():
    logging.info("Tracking trending tokens...")
    tokens = fetch_trending_tokens()
    if tokens:
        new_tokens = store_trending_tokens(tokens)
        if new_tokens:
            logging.info(f"New trending tokens found: {len(new_tokens)}")
            for token in new_tokens:
                 send_most_viewed_telegram_notification(token)     
    time.sleep(5)
    clear_trending_table()