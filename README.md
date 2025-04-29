# ZT-3 Daily Breakout Screener

A Python application to screen Indian stocks listed on the NSE daily based on specific technical breakout criteria using the Upstox API. It generates an HTML report and sends alerts to Discord.

## Features

- **Daily Stock Screening:** Runs daily to identify potential breakout opportunities.
- **Upstox API Integration:** Fetches historical daily candle data directly from Upstox (v2 API).
- **Configurable Criteria:** Screening parameters (lookback period, volume multiplier, price limits) are configurable via `config.yml`.
- **Specific Conditions:** Screens based on:
  1.  **Price Breakout:** Close > Highest Close of the last N days (excluding today).
  2.  **Volume Surge:** Volume > N times the average volume of the last N days.
  3.  **Price Range:** Close price within a defined min/max range.
  4.  **Trend Filter:** Close > 20-day EMA.
- **HTML Reports:** Generates a detailed HTML report listing shortlisted stocks and their metrics.
- **Discord Notifications:** Sends real-time alerts to a configured Discord channel with the list of passing stocks (or a "no results" message) and execution time. Optionally attaches the HTML report.
- **Report Management:** Automatically keeps only the latest few reports, deleting older ones.
- **Token Management:** Handles Upstox API access token fetching and storage. Includes instructions for initial manual authorization.

## Prerequisites

- Python 3.8+
- Pip (Python package installer)
- An active Upstox account.
- Upstox API Key and Secret ([Upstox Developer Console](https://developer.upstox.com/)).
- A Discord Webhook URL for notifications.

## Setup

1.  **Clone the Repository:**

    ```bash
    git clone https://github.com/JittoJoseph/ZT3-Stock-Screener.git
    cd zt-3-screener
    ```

2.  **Install Dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment Variables:**

    - Create a file named `.env` in the project root directory.
    - Add your Upstox API credentials and Discord webhook URL:
      ```dotenv
      # .env
      UPSTOX_API_KEY=your_api_key
      UPSTOX_API_SECRET=your_api_secret
      UPSTOX_REDIRECT_URI=your_redirect_uri # e.g., http://127.0.0.1
      DISCORD_WEBHOOK_URL=your_discord_webhook_url
      ```
    - Ensure the `UPSTOX_REDIRECT_URI` matches the one configured in your Upstox developer app settings.

4.  **Configure Screener Settings:**

    - Review and adjust parameters in `config.yml` as needed (e.g., `lookback_period`, `volume_multiplier`, `price_limits`, file paths).

5.  **Prepare Stock List:**

    - Create or update `stock_list.csv` with the `symbol` and `isin` of the stocks you want to scan.
      ```csv
      # stock_list.csv
      symbol,isin
      RELIANCE,INE002A01018
      TCS,INE467B01029
      # ... more stocks
      ```
    - **(Optional but Recommended):** Run the validation script (`utils/validate_isins.py`, if available) to create a `validated_stock_list.csv`. The `main.py` script currently expects this validated file. Adjust `config.yml` if using the raw `stock_list.csv`.

6.  **Initial API Authentication:**
    - The first time you run the script (or after a token expires), it will detect no valid access token.
    - Follow the instructions printed in the console:
      - Open the provided authorization URL in your browser.
      - Log in to Upstox and authorize the application.
      - Copy the `code` parameter from the redirect URL in your browser's address bar.
      - Run the provided `python -c "..."` command in your terminal, pasting the copied code.
    - This will generate the `token_store.json` file containing your access token.

## Usage

Run the main script from the project's root directory:

```bash
python main.py
```

The screener will:

1.  Load configuration and the stock list.
2.  Fetch data for each stock.
3.  Apply screening logic.
4.  Generate an HTML report in the `outputs/reports/` directory (if stocks pass).
5.  Send a notification to your Discord channel.
6.  Clean up old reports.

## Configuration Files

- **`.env`**: Stores sensitive credentials (API keys, webhook URL). **Do not commit this file to version control.**
- **`config.yml`**: Contains non-sensitive settings like screener parameters, file paths, API version, etc.
- **`stock_list.csv` / `validated_stock_list.csv`**: List of stocks (Symbol, ISIN) to be screened.

## Output

- **HTML Report:** Found in `outputs/reports/`. Contains a table of shortlisted stocks with details like Close Price, Breakout Level, Volume Surge %, EMA(20), and Volume.
- **Discord Message:** An embed message sent to the configured webhook URL, listing symbols and prices of passing stocks, or indicating no stocks passed.

## Disclaimer

This tool is for educational and informational purposes only. Trading stocks involves significant risk. Use this tool at your own risk and always perform your own due diligence before making any trading decisions. The author is not responsible for any financial losses incurred.
