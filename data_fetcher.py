import config # Now imports the module that loads .env and yaml
import requests
import json
import os
from datetime import datetime, timedelta

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
    if _access_token:
        # Quick check if token exists; load_token handles expiry check
        return _access_token

    token_data = load_token()
    if token_data:
        _access_token = token_data.get('access_token')
        return _access_token
    else:
        # Instructions for the user if token is missing/expired
        print("-" * 40)
        print("ACTION REQUIRED: No valid access token found.")
        print("1. Ensure UPSTOX_API_KEY and UPSTOX_REDIRECT_URI are set in .env")
        api_key = config.get_upstox_api_key()
        redirect_uri = config.get_upstox_redirect_uri()
        if not api_key or not redirect_uri:
             print("   Error: API Key or Redirect URI missing in .env file.")
             return None

        print("2. Generate the authorization URL:")
        auth_url = (f"https://api.upstox.com/{API_VERSION}/login/authorization/dialog?"
                    f"response_type=code&client_id={api_key}"
                    f"&redirect_uri={redirect_uri}")
        print(f"\n   {auth_url}\n")
        print(f"3. Open the URL in your browser, log in, and authorize.")
        print(f"4. You will be redirected to '{redirect_uri}'.")
        print(f"5. Copy the 'code' value from the URL query parameters (e.g., ...?code=YOUR_CODE_HERE&...).")
        print(f"6. Run the token exchange function manually or via a helper script:")
        print(f"   Example: python -c \"import data_fetcher; data_fetcher.exchange_code_for_token('PASTE_CODE_HERE')\"")
        print("-" * 40)
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

def fetch_historical_data(instrument_key, interval='1day', to_date=None, from_date=None):
    """
    Fetches historical candle data for a given instrument using direct API calls.
    Requires the specific API endpoint for historical data.
    """
    headers = get_api_headers()
    if not headers:
        print("Error: Cannot fetch data, authentication failed or token missing.")
        return None

    # --- Need the correct Upstox API v2 endpoint for historical data ---
    # This needs confirmation from Upstox API v2 documentation.
    # Example structure based on common patterns:
    # historical_data_endpoint = f"https://api.upstox.com/{API_VERSION}/historical-candle/{instrument_key}/{interval}/{from_date}/{to_date}"
    # Or it might use query parameters:
    historical_data_base_url = f"https://api.upstox.com/{API_VERSION}/historical-candle"

    params = {
        'instrumentKey': instrument_key,
        'interval': interval,
        'to_date': to_date,     # Format likely 'YYYY-MM-DD'
        'from_date': from_date  # Format likely 'YYYY-MM-DD'
    }

    print(f"Placeholder: Fetching data for {instrument_key} via API...")
    try:
        # response = requests.get(historical_data_base_url, headers=headers, params=params) # Correct endpoint/structure needed
        # response.raise_for_status()
        # data = response.json()
        # Process the response (likely needs conversion to DataFrame, structure depends on API)
        # Example structure assumption: data = {'status': 'success', 'data': {'candles': [...]}}
        # return data.get('data', {}).get('candles')
        print(f"Placeholder: Would call GET {historical_data_base_url} with params: {params}")
        print("Actual API endpoint and response structure for historical data needed.")
        return None # Return None until endpoint is confirmed and implemented
    except requests.exceptions.RequestException as e:
        print(f"Error fetching historical data for {instrument_key}: {e}")
        # if e.response is not None:
        #     print(f"Response status: {e.response.status_code}")
        #     print(f"Response text: {e.response.text}")
        return None
    except (KeyError, json.JSONDecodeError) as e:
        print(f"Error processing data for {instrument_key}: {e}")
        # if 'response' in locals() and hasattr(response, 'text'):
        #      print(f"Response text: {response.text}")
        return None


# Example usage (for testing later)
if __name__ == '__main__':
    # To test token exchange (run this part manually after getting the code):
    # auth_code = "PASTE_YOUR_AUTH_CODE_HERE"
    # if auth_code and auth_code != "PASTE_YOUR_AUTH_CODE_HERE":
    #     new_token = exchange_code_for_token(auth_code)
    #     if new_token:
    #         print("Token exchange successful.")
    #     else:
    #         print("Token exchange failed.")
    # else:
    #      print("\nTo test token exchange: edit this script, paste the authorization code, and run.")
    #      print("Example command after pasting code:")
    #      print(f"python {__file__}")


    # To test data fetching (after token is stored):
    if get_access_token():
        print("\nAttempting to fetch data (requires correct endpoint)...")
        # Need a valid instrument key, e.g., from Upstox documentation or another API call
        # Example: Reliance NSE Equity: "NSE_EQ|INE002A01018" (Format needs verification for v2 API)
        # instrument = "NSE_EQ|INE002A01018"
        # today = datetime.now().strftime('%Y-%m-%d')
        # lookback_days = config.settings['screener']['lookback_period'] + 20 # Fetch extra buffer
        # start_date = (datetime.now() - timedelta(days=lookback_days)).strftime('%Y-%m-%d')
        # data = fetch_historical_data(instrument, interval='1day', to_date=today, from_date=start_date)
        # if data:
        #     print("Data fetched successfully (structure depends on API):")
        #     # print(data) # Raw data
        # else:
        #     print("Failed to fetch data (check endpoint and instrument key).")
        pass # Keep placeholder until endpoint is known
    else:
        print("\nCannot fetch data without a valid access token. Follow the instructions above.")
