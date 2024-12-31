import logging
import mysql.connector
from mysql.connector import Error
from telegram_bot import send_telegram_notification, send_most_viewed_telegram_notification
import time
import requests
from requests.exceptions import ConnectionError, Timeout, RequestException
from utils import format_market_cap, parse_market_cap, check_rug_status 
logging.basicConfig(level=logging.INFO)
skipList=[] 
# Function to create a database connection
def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password='meow',
            database='token_db'
        )
        if conn.is_connected():
            logging.debug("Connected to the database")
            return conn
        else:
            logging.debug("not connected to db")
    except Error as e:
        logging.info(f"Error connecting to database: {e}")
        return None
def setup_tables():
    # Create table if it doesn't exist
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS ai_tokens (
                id INT AUTO_INCREMENT PRIMARY KEY,
                url VARCHAR(255),
                chainId VARCHAR(255),
                tokenAddress VARCHAR(255) NOT NULL,
                description TEXT,
                marketcap TEXT,
                token_holders BIGINT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                CONSTRAINT unique_tokenAddress UNIQUE (tokenAddress)
                );

                ''')
                 # Trending Tokens Table
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS trending_tokens (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    mint VARCHAR(255) UNIQUE,
                    name VARCHAR(255),
                    symbol VARCHAR(50),
                    uri TEXT,
                    update_authority VARCHAR(255),
                    visits INT,
                    score INT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                ''')
        finally:
            conn.commit()
            conn.close()


# Step 3: Store the filtered AI tokens in the MySQL database
def store_tokens(tokens):
    conn=get_db_connection()
    cursor= conn.cursor()
    for token in tokens:
        chain_id = token.get('chainId')
        token_address = token.get('tokenAddress')
        if chain_id == "solana":
            if not check_rug_status(token_address):
                logging.info(f"Token {token_address} on Solana chain failed the rug check.")
                continue
        if chain_id != "base" and chain_id !="solana":
            continue
        insert_query = """
        INSERT INTO ai_tokens (url, chainId, tokenAddress, description, created_at, last_updated)
        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ON DUPLICATE KEY UPDATE 
            description = VALUES(description),
            last_updated = CURRENT_TIMESTAMP;
        """
        data = (
            token.get('url'),
            token.get('chainId'),
            token.get('tokenAddress'),
            token.get('description')
        )
        try:
            cursor.execute(insert_query, data)
            conn.commit()
            # Check if a new record is inserted
           # last_id = cursor.fetchone()[0]
            if cursor.rowcount == 1:  # New record inserted
                logging.info(f"Inserted new token: {token.get('tokenAddress')}")
                message = f"New AI Token Found:" + str(token.get('url'))
                send_telegram_notification(message)  # send notifications immediately
            else:
                logging.info(f"Updated token: {token.get('tokenAddress')}")
        except Error as e:
                logging.info(f"Error inserting/updating token {token.get('tokenAddress')}: {e}")
    cursor.close()
    conn.close()

# Function to update marketcap and token holders in the database
def update_token_info(token_address):
    api_url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
    max_retries = 3
    retry_delay = 5  # seconds

    for attempt in range(max_retries):
        try:
            response = requests.get(api_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                conn = get_db_connection()
                cursor = conn.cursor()
                 # Safely access 'pairs' with .get() to avoid NoneType errors
                pairs = data.get('pairs', [])
                # Parse the response to extract marketCap and other details
                if pairs:
                    pair = pairs[0]   # Assuming we use the first pair in the response
                    market_cap = pair.get('marketCap', None)
                    url = pair.get('url', None)
                    # Replace 'tokenHolders' with the actual equivalent field if available in API response
                    token_holders = pair.get('liquidity', {}).get('base', None)  # Example placeholder

                    if market_cap is not None and token_holders is not None:
                        formatted_market_cap = format_market_cap(market_cap)
                        if(market_cap>500000 and token_address not in skipList):
                             message= f"AI token market cap reached:" + str(formatted_market_cap) + "token: " +str(url)
                             skipList.append(token_address)
                             send_telegram_notification(message)
                     # Update the database
                        update_query = """
                        UPDATE ai_tokens
                        SET marketcap = %s, token_holders = %s
                        WHERE tokenAddress = %s
                        """
                        cursor.execute(update_query, (formatted_market_cap, token_holders, token_address))
                        conn.commit()
                        logging.debug(f"Updated token: {token_address}, MarketCap: {formatted_market_cap}, Token Holders: {token_holders}")
                        cursor.close()
                        conn.close()
                        return
                    else:
                            logging.info(f"MarketCap or Token Holders missing for token: {token_address}")
                else:
                        logging.info(f"No pairs found in API response for token: {token_address}")
                        return
            else:
                    logging.info(f"Failed to fetch data for token: {token_address}, Status Code: {response.status_code}")
        except ConnectionError as ce:
                logging.info(f"Connection error occurred: {ce}")
        except Timeout as te:
                logging.info(f"Request timed out: {te}")
        except RequestException as re:
                logging.info(f"An error occurred while making the request: {re}")
        except Exception as e:
                logging.info(f"Unexpected error: {e}")
        logging.info(f"Retrying in {retry_delay} seconds... (Attempt {attempt + 1}/{max_retries})")
        time.sleep(retry_delay)        
        # If all retries fail, log the issue or take alternative action
    logging.info(f"Failed to fetch data for token: {token_address} after {max_retries} attempts.")
    return None  # Return None or handle this case in the caller


# Function to delete old records with market cap below 100k
def clear_old_low_marketcap_records():
    logging.info("clearing records")
    """
    Deletes records from the database where marketCap < 100k and created_at is older than today.
    Handles marketCap stored as formatted strings (e.g., "1M", "500K").
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Retrieve all records with their market cap and parse it
        select_query = """
        SELECT id, marketCap 
        FROM ai_tokens 
        WHERE DATE(created_at) < CURDATE();
        """
        cursor.execute(select_query)
        records = cursor.fetchall()

        # Prepare IDs for deletion
        delete_ids = []
        for record in records:
            record_id, market_cap_str = record
            market_cap_value = parse_market_cap(market_cap_str)
            if market_cap_value < 100000:
                delete_ids.append(record_id)

        # Delete records if any match the condition
        if delete_ids:
            format_strings = ",".join(["%s"] * len(delete_ids))
            delete_query = f"DELETE FROM ai_tokens WHERE id IN ({format_strings})"
            cursor.execute(delete_query, tuple(delete_ids))
            conn.commit()
            logging.info(f"Deleted {cursor.rowcount} records with market cap below 100k and older than today.")
        else:
             logging.info("No records matched the criteria for deletion.")
    except Error as e:
         logging.info(f"Error while clearing old records: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Function to clear the trending tokens table every 24 hours
def clear_trending_table():
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM trending_tokens WHERE created_at < NOW() - INTERVAL 24 HOUR;")
                conn.commit()
                logging.info("Cleared old records from trending_tokens table.")
        except Error as e:
            logging.error(f"Error clearing trending tokens table: {e}")
        finally:
            conn.close()

# Function to store trending tokens in the database
def store_trending_tokens(tokens):
    conn = get_db_connection()
    if conn:
        try:
            new_tokens = []
            with conn.cursor() as cursor:
                for token in tokens:
                    insert_query = '''
                    INSERT INTO trending_tokens (mint, name, symbol, uri, update_authority, visits, score)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE 
                        visits = VALUES(visits),
                        score = VALUES(score),
                        uri = VALUES(uri),
                        update_authority = VALUES(update_authority);
                    '''
                    data = (
                        token["mint"],
                        token["metadata"]["name"],
                        token["metadata"]["symbol"],
                        token["metadata"]["uri"],
                        token["metadata"]["updateAuthority"],
                        token["visits"],
                        token["score"]
                    )
                    cursor.execute(insert_query, data)
                    if cursor.rowcount == 1:
                        new_tokens.append(token)  # New token added
                conn.commit()
            return new_tokens
        except Error as e:
            logging.error(f"Error storing trending tokens: {e}")
        finally:
            conn.close()
    return []