import logging
import re
import requests
logging.basicConfig(level=logging.INFO)
def format_market_cap(value):
    """
    Formats a market cap value to a human-readable format.
    E.g., 1000000 -> 1M, 1000 -> 1K, 1000000000 -> 1B
    """
    if value >= 1000000000:
        return f"{value / 1000000000:.1f}B"  # For billions
    elif value >= 1000000:
        return f"{value / 1000000:.1f}M"  # For millions
    elif value >= 1000:
        return f"{value / 1000:.1f}K"  # For thousands
    else:
        return str(value)  # For values less than 1000
    
# Function to filter AI-related tokens
def filter_ai_tokens(tokens):
    keywords = ["AI", "Neural", "Machine", "Learning", "Intelligence" , "VIRTUALS", "Pudgy"]
    filtered_tokens = []
    patterns = [re.compile(r'\b' + re.escape(keyword.lower()) + r'\b', re.IGNORECASE) for keyword in keywords]
    count = 0
    for token in tokens:
        # Check if the token contains any AI-related keywords in its "name" field
        token_description = token.get("description", "").lower()
                # Check for matches with any of the AI-related keywords
        matched_keywords = [keyword for keyword, pattern in zip(keywords, patterns) if pattern.search(token_description)]
        if matched_keywords:
            filtered_tokens.append(token)
            count += 1
            logging.info(f"Matched keywords: {matched_keywords}")
    logging.info("Tokens filtered: " + str(count))
    return filtered_tokens

def parse_market_cap(value):
    if value:
        """
        Converts a formatted market cap value (e.g., "1M", "500K") back to a numerical value.
        """
        if value.endswith("B"):
            return float(value[:-1]) * 1_000_000_000  # Convert billions to numeric
        elif value.endswith("M"):
            return float(value[:-1]) * 1_000_000  # Convert millions to numeric
        elif value.endswith("K"):
            return float(value[:-1]) * 1_000  # Convert thousands to numeric
        else:
            return float(value)  # If no suffix, return as is
    else:
        return 0

def check_rug_status(token_address):
    logging.info(f"rug check of token_address: {token_address}")
    """
    Checks if the token is marked as 'GOOD' on rugcheck.xyz.
    """
    rugcheck_url = f"https://api.rugcheck.xyz/v1/tokens/{token_address}/report"
    try:
        response = requests.get(rugcheck_url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            score = data.get('score', '')
            if score>=0 and score<=400:
                return True  
        else:
            logging.info(f"Failed to fetch rug check status for {token_address}, Status Code: {response.status_code}")
    except Exception as e:
        logging.info(f"Error checking rug status for {token_address}: {e}")
    return False