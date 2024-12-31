import requests
import requests
from fastapi import FastAPI
import logging
import time
from utils import format_market_cap, filter_ai_tokens
from db_operations import store_tokens, get_db_connection, store_trending_tokens
from requests.exceptions import ConnectionError, Timeout, RequestException
from datetime import datetime, timedelta
# Initialize FastAPI app
app = FastAPI()
# API Route: Fetch and return AI tokens
# Dexscreener API URL
DEX_API_URL = "https://api.dexscreener.com/token-profiles/latest/v1"

# RugCheck API URL
RUGCHECK_API_URL = "https://api.rugcheck.xyz/v1/stats/recent"

@app.get("/ai-tokens")
def get_ai_tokens():
    try:
        # Fetch tokens from Dexscreener
        data = fetch_dexscreener_tokens()
        # Access the relevant list of tokens
        if data:
            logging.debug("Total Objects " + str(len(data)))
        # Filter AI-related tokens
            ai_tokens = filter_ai_tokens(data)
            logging.debug("AI tokens fetched")
        
            if ai_tokens:
                logging.debug(f"Found {len(ai_tokens)} AI tokens. Storing in the database...")
                store_tokens(ai_tokens)  # Store the filtered tokens in DB
            else:
                logging.debug("No AI tokens found in the data.")
            return ai_tokens
    except Exception as e:
        return {"error": str(e)}

# Function to fetch data from Dexscreener
def fetch_dexscreener_tokens():
    max_retries = 3
    retry_delay = 5  # seconds
    for attempt in range(max_retries):
        try:
            logging.info("Fetching data from Dexscreener API...")
            response = requests.get(DEX_API_URL, timeout=10)
            if response:
                response.raise_for_status()  # Raise HTTPError for bad responses
                return response.json()  # Return parsed JSON data
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
    logging.info(f"Failed to fetch data after {max_retries} attempts.")
    return None  # Return None or handle this case in the caller
 # Compile regular expressions for case-insensitive matching of whole words

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
                    # Replace 'tokenHolders' with the actual equivalent field if available in API response
                    token_holders = pair.get('liquidity', {}).get('base', None)  # Example placeholder

                    if market_cap is not None and token_holders is not None:
                     # Update the database
                        formatted_market_cap = format_market_cap(market_cap)
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

# Function to fetch trending tokens from RugCheck API
def fetch_trending_tokens():
    try:
        response = requests.get(RUGCHECK_API_URL, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching trending tokens: {e}")
        return []
    
# Trending Token Tracker
def track_trending_tokens():
    logging.info("Tracking trending tokens...")
    tokens = fetch_trending_tokens()
    if tokens:
        new_tokens = store_trending_tokens("trending_tokens", tokens, "mint")
        if new_tokens:
            logging.info(f"New trending tokens found: {len(new_tokens)}")
            (new_tokens, "Trending")