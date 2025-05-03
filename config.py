import os
import yaml
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Load application settings from config.yaml
CONFIG_YAML_PATH = "config.yaml"
settings = {}

try:
    with open(CONFIG_YAML_PATH, 'r') as f:
        settings = yaml.safe_load(f)
except FileNotFoundError:
    print(f"Error: {CONFIG_YAML_PATH} not found.")
    # Provide default settings or raise an error
    settings = { # Example default structure with 4 rules (removed min_avg_volume)
        'screener': {
            # Rule 1: Trend Alignment
            'ema_period_short': 20,
            'ema_period_long': 50,
            
            # Rule 2: Proximity to 50-Day High
            'lookback_period': 50,
            'price_drop_percent_min': 0.0,
            'price_drop_percent_max': 10.0,
            
            # Rule 3: Volume Ratio Filter
            'avg_volume_lookback': 50,
            'volume_surge_min': 2.0,
            'volume_surge_max': 2.5,
            
            # Rule 4: Price Range Filter
            'min_price': 25.0,
            'max_price': 1500.0,
            'enable_max_price_limit': True
        },
        'paths': {'stock_list_file': 'stock_list.csv', 'valid_stock_list_file': 'valid_stock_list.csv', 'output_dir': 'outputs', 'report_dir': 'outputs/reports', 'token_store_file': 'token_store.json'},
        'reporting': {'max_reports': 2},
        'upstox': {'api_version': 'v2'}
    }
    print("Warning: Using default settings.")
except yaml.YAMLError as e:
    print(f"Error parsing {CONFIG_YAML_PATH}: {e}")
    # Handle error appropriately
    raise SystemExit(f"Could not parse {CONFIG_YAML_PATH}")

# --- Accessor functions or direct access ---

# Secrets (from .env)
def get_upstox_api_key():
    return os.getenv("UPSTOX_API_KEY")

def get_upstox_api_secret():
    return os.getenv("UPSTOX_API_SECRET")

def get_upstox_redirect_uri():
    return os.getenv("UPSTOX_REDIRECT_URI")

def get_discord_webhook_url():
    return os.getenv("DISCORD_WEBHOOK_URL")

def get_discord_stocklist_webhook_url():
    """Gets the Discord webhook URL specifically for stock list validation reports."""
    return os.getenv("DISCORD_STOCKLIST_WEBHOOK_URL")

# Settings (from config.yaml) - accessed via the 'settings' dictionary
# Example: config.settings['screener']['price_min']
# Example: config.settings['paths']['token_store_file']

# You could also create specific functions for frequently accessed settings if preferred:
# def get_lookback_period():
#    return settings.get('screener', {}).get('lookback_period', 20) # With default

# Validate essential settings loaded correctly
# Update validation to check the main webhook, the stocklist one is optional for this script
if not all([get_upstox_api_key(), get_upstox_api_secret(), get_upstox_redirect_uri()]):
     # Removed get_discord_webhook_url() check here as it's not essential for all parts
     print("Warning: One or more environment variables (API Keys, Redirect URI) are missing in the .env file.")
     # Depending on the script's needs, you might want to exit here
     # raise SystemExit("Missing essential configuration in .env file.")

# Add specific check for the main webhook if needed elsewhere
# if not get_discord_webhook_url():
#    print("Warning: DISCORD_WEBHOOK_URL is missing in the .env file.")

if not settings:
    raise SystemExit("Failed to load settings from config.yaml")

print("Configuration loaded.")
