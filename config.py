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
    settings = { # Example default structure if file is missing
        'screener': {'price_min': 20, 'price_max': 1000, 'volume_surge_factor': 1.5, 'lookback_period': 20},
        'paths': {'stock_list_file': 'stock_list.csv', 'output_dir': 'outputs', 'report_dir': 'outputs/reports', 'token_store_file': 'token_store.json'},
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

# Settings (from config.yaml) - accessed via the 'settings' dictionary
# Example: config.settings['screener']['price_min']
# Example: config.settings['paths']['token_store_file']

# You could also create specific functions for frequently accessed settings if preferred:
# def get_lookback_period():
#    return settings.get('screener', {}).get('lookback_period', 20) # With default

# Validate essential settings loaded correctly
if not all([get_upstox_api_key(), get_upstox_api_secret(), get_upstox_redirect_uri(), get_discord_webhook_url()]):
     print("Warning: One or more environment variables (API Keys, Redirect URI, Webhook URL) are missing in the .env file.")
     # Depending on the script's needs, you might want to exit here
     # raise SystemExit("Missing essential configuration in .env file.")

if not settings:
    raise SystemExit("Failed to load settings from config.yaml")

print("Configuration loaded.")
