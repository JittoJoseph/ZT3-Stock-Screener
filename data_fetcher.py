import time  # NEW: ensure time is imported for time.sleep usage
import config # Now imports the module that loads .env and yaml
import requests
import json
import os
import pandas as pd # Import pandas
from datetime import datetime, timedelta

# Get logger from utils (assuming utils is imported elsewhere or configured globally)
# If running standalone, configure basic logging here
try:
    from utils.helpers import logging # Updated import
except ImportError:
    import logging
    # Define basic config if run standalone and utils.helpers cannot be imported
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')


# Get constants from loaded config
TOKEN_FILE = config.settings['paths']['token_store_file']
API_VERSION = config.settings['upstox']['api_version']

def exchange_code_for_token(auth_code):
    """Exchanges the authorization code for an access token."""
    url = f"https://api.upstox.com/{API_VERSION}/login/authorization/token"
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {
        'code': auth_code,
        'client_id': config.get_upstox_api_key(), # Use accessor function
        'client_secret': config.get_upstox_api_secret(), # Use accessor function
        'redirect_uri': config.get_upstox_redirect_uri(), # Use accessor function
        'grant_type': 'authorization_code'
    }
    try:
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()  # Raise an exception for bad status codes
        token_data = response.json()
        # Add expiry time for checking later (assuming token lasts less than a day for safety)
        # Consider making the token duration configurable or getting it from response if available
        token_data['expires_at'] = (datetime.now() + timedelta(hours=12)).isoformat()
        save_token(token_data)
        print("Access token obtained and saved successfully.")
        return token_data.get('access_token')
    except requests.exceptions.RequestException as e:
        print(f"Error exchanging code for token: {e}")
        response_text = e.response.text if e.response else "No response"
        print(f"Response text: {response_text}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON response from token endpoint: {e}")
        # Attempt to print response text even if JSON decoding fails
        if 'response' in locals() and hasattr(response, 'text'):
             print(f"Response text: {response.text}")
        return None


def save_token(token_data):
    """Saves token data to a file."""
    try:
        with open(TOKEN_FILE, 'w') as f:
            json.dump(token_data, f)
            print(f"Token data saved to {TOKEN_FILE}")
    except IOError as e:
        print(f"Error saving token file {TOKEN_FILE}: {e}")

def load_token():
    """Loads token data from a file and checks expiry."""
    if not os.path.exists(TOKEN_FILE):
        return None
    try:
        with open(TOKEN_FILE, 'r') as f:
            token_data = json.load(f)
            # Check expiry
            expires_at_str = token_data.get('expires_at')
            if expires_at_str:
                expires_at = datetime.fromisoformat(expires_at_str)
                if datetime.now() >= expires_at:
                    print("Access token has expired.")
                    # Optionally, attempt refresh here if refresh token exists and is supported
                    # For now, just indicate expiry
                    return None
            return token_data
    except (IOError, json.JSONDecodeError, ValueError) as e:
        print(f"Error loading or parsing token file: {e}")
        return None

# Store the loaded access token globally within this module
_access_token = None

def get_access_token():
    """Gets the current access token, loading if necessary."""
    global _access_token
    if (_access_token):
        # Quick check if token exists; load_token handles expiry check
        return _access_token

    token_data = load_token()
    if token_data:
        _access_token = token_data.get('access_token')
        # Log token load success for clarity
        logging.info(f"Loaded access token from {TOKEN_FILE}")
        return _access_token
    else:
        # Instructions for the user if token is missing/expired
        print("-" * 60) # Wider separator
        print("ACTION REQUIRED: No valid Upstox access token found.")
        print("Please perform the following steps manually:")
        print("-" * 60)
        print("1. Ensure UPSTOX_API_KEY and UPSTOX_REDIRECT_URI are set in .env")
        api_key = config.get_upstox_api_key()
        redirect_uri = config.get_upstox_redirect_uri()
        if not api_key or not redirect_uri:
             print("\n   ERROR: UPSTOX_API_KEY or UPSTOX_REDIRECT_URI missing in .env file!")
             print("-" * 60)
             return None

        print("\n2. Open this Authorization URL in your web browser:")
        auth_url = (f"https://api.upstox.com/{API_VERSION}/login/authorization/dialog?"
                    f"response_type=code&client_id={api_key}"
                    f"&redirect_uri={redirect_uri}")
        print(f"\n   {auth_url}\n")
        print(f"3. Log in to Upstox and authorize the application.")
        print(f"4. After authorization, your browser will redirect to:")
        print(f"   {redirect_uri}?code=YOUR_AUTH_CODE&...")
        print(f"   Copy the 'YOUR_AUTH_CODE' value from the browser's address bar.")
        print("\n5. Open your terminal/command prompt in the project directory")
        print(f"   (d:\\Projects\\zt-3-screener) and run this command,")
        print(f"   replacing 'PASTE_CODE_HERE' with the code you copied:")
        print(f"\n   python -c \"import data_fetcher; data_fetcher.exchange_code_for_token('PASTE_CODE_HERE')\"\n")
        print("6. Once the token is saved successfully, re-run the script you were trying to execute.")
        print("-" * 60)
        return None


def get_api_headers():
    """Returns the headers required for authenticated API calls."""
    token = get_access_token()
    if not token:
        return None
    return {
        'accept': 'application/json',
        'Authorization': f'Bearer {token}'
    }

# --- Placeholder for the actual API client/session ---
# We don't need a full client object now, just the headers.
# get_upstox_client function is replaced by get_api_headers

def fetch_historical_data(instrument_key, interval='day', to_date=None, from_date=None):
    """
    Fetches historical candle data for a given instrument using the Upstox API v2.
    Converts the candle data into a pandas DataFrame.

    Args:
        instrument_key (str): The Upstox instrument key (e.g., 'NSE_EQ|INE002A01018').
        interval (str): Candle interval ('1minute', '30minute', 'day', 'week', 'month'). Defaults to 'day'.
        to_date (str): The end date in 'YYYY-MM-DD' format. Defaults to today.
        from_date (str): The start date in 'YYYY-MM-DD' format. Required by the documented path.

    Returns:
        pandas.DataFrame: DataFrame with columns ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'open_interest']
                          Returns None if fetching fails or no data is returned.
    """
    headers = get_api_headers()
    if not headers:
        logging.error("Cannot fetch data, authentication failed or token missing.")
        return None

    if not to_date:
        to_date = datetime.now().strftime('%Y-%m-%d')

    if not from_date:
        # Calculate a default from_date if not provided, e.g., 60 days back for daily interval
        # Note: The API docs list from_date as a required path parameter, so this might cause issues if not provided.
        # We need sufficient data for lookback calculations (e.g., 20 days + buffer).
        lookback_days = config.settings['screener']['lookback_period'] + 40 # Fetch buffer
        from_date = (datetime.now() - timedelta(days=lookback_days)).strftime('%Y-%m-%d')
        logging.warning(f"from_date not provided, defaulting to {from_date}")


    # Construct the URL using path parameters as per documentation
    # Example: https://api.upstox.com/v2/historical-candle/NSE_EQ|INE848E01016/day/2024-04-29/2024-03-01
    # Note the order: {instrument_key}/{interval}/{to_date}/{from_date} - This seems counter-intuitive (to before from)
    # Let's try the documented order first.
    historical_data_url = f"https://api.upstox.com/{API_VERSION}/historical-candle/{instrument_key}/{interval}/{to_date}/{from_date}"

    logging.info(f"Fetching historical data for {instrument_key} from {from_date} to {to_date}")
    logging.debug(f"API URL: {historical_data_url}")

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.get(historical_data_url, headers=headers)
            response.raise_for_status()  # Raises exception for 4xx/5xx codes
            data = response.json()
            if data.get('status') != 'success':
                logging.error(f"API request failed for {instrument_key}. Status: {data.get('status')}, Message: {data.get('message', 'N/A')}")
                return None
            candles = data.get('data', {}).get('candles')
            if not candles:
                logging.warning(f"No candle data returned for {instrument_key} for the given period.")
                return None
            # Define column names based on documentation order
            columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'open_interest']
            df = pd.DataFrame(candles, columns=columns)

            # Convert timestamp to datetime objects (adjust format if needed, API uses ISO 8601)
            # Example: "2023-10-01T00:00:00+05:30"
            try:
                # Let pandas infer the format, which usually works well with ISO 8601
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                # Optional: Convert to date if only date part is needed for daily data
                # df['date'] = df['timestamp'].dt.date
            except Exception as e:
                logging.warning(f"Could not parse timestamp column for {instrument_key}: {e}. Leaving as string.")


            # Convert numeric columns
            numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'open_interest']
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col], errors='coerce') # Coerce errors to NaN

            # Sort by timestamp just in case API doesn't guarantee order
            df = df.sort_values(by='timestamp').reset_index(drop=True)

            logging.info(f"Successfully fetched and processed {len(df)} candles for {instrument_key}")
            return df

        except requests.exceptions.HTTPError as http_err:
            if response.status_code == 429:
                delay = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s, etc.
                logging.error(f"HTTP error 429 for {instrument_key}. Attempt {attempt+1}/{max_retries}. Retrying after {delay} second(s).")
                time.sleep(delay)
                continue
            else:
                logging.error(f"HTTP error occurred for {instrument_key}: {http_err}")
                return None
        except Exception as e:
            logging.error(f"An unexpected error occurred during data fetching for {instrument_key}: {e}")
            return None
    logging.error(f"Max retries exceeded for {instrument_key}.")
    return None


# Example usage (for testing later)
if __name__ == '__main__':
    # Ensure utils logging is configured if running directly
    try:
        import utils.helpers # Updated import check
    except ImportError:
        pass # BasicConfig should handle it

    # To test token exchange (run this part manually after getting the code):
    # auth_code = "PASTE_YOUR_AUTH_CODE_HERE"
    # if auth_code and auth_code != "PASTE_YOUR_AUTH_CODE_HERE":
    #     new_token = exchange_code_for_token(auth_code)
    #     if new_token:
    #         logging.info("Token exchange successful.")
    #     else:
    #         logging.error("Token exchange failed.")
    # else:
    #      logging.info("\nTo test token exchange: edit this script, paste the authorization code, and run.")
    #      logging.info("Example command after pasting code:")
    #      logging.info(f"python {__file__}")


    # To test data fetching (after token is stored):
    if get_access_token():
        logging.info("\nAttempting to fetch data...")
        # Need a valid instrument key. Use one from your stock_list.csv if known, e.g., Reliance
        # The exact format 'NSE_EQ|INE...' needs confirmation for v2 API.
        # Let's assume the format is correct for now.
        instrument = "NSE_EQ|INE002A01018" # Example: Reliance Industries Ltd.
        today_str = datetime.now().strftime('%Y-%m-%d')
        # Fetch data for the last ~60 days to ensure enough points for 20-day calculations
        start_date_str = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')

        # Use interval='day' for daily data
        historical_df = fetch_historical_data(instrument, interval='day', to_date=today_str, from_date=start_date_str)

        if historical_df is not None and not historical_df.empty:
            logging.info(f"Data fetched successfully for {instrument}:")
            print(historical_df.head()) # Print first few rows
            print(f"\nDataFrame shape: {historical_df.shape}")
            print(f"Latest date in data: {historical_df['timestamp'].iloc[-1]}")
        else:
            logging.warning(f"Failed to fetch or process data for {instrument}.")
            logging.warning("Check API endpoint, instrument key format, token validity, and date range.")
    else:
        logging.error("\nCannot fetch data without a valid access token. Follow the instructions printed earlier.")
