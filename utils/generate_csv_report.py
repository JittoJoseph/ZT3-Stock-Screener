import sys
import os
import pandas as pd
import time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import project modules
import config
from utils.helpers import logging, load_stock_list
from data_fetcher import fetch_historical_data, get_access_token
from screener_logic import EMA_PERIOD_SHORT, EMA_PERIOD_LONG, AVG_VOLUME_LOOKBACK, LOOKBACK_PERIOD

# Constants for price filtering
MIN_PRICE = 25.0
MAX_PRICE = 1500.0

# Constants for data fetching
FETCH_INTERVAL = 'day'
LOOKBACK_DAYS = LOOKBACK_PERIOD + 60  # More buffer for calculations
EXCHANGE = "NSE"
INSTRUMENT_TYPE = "EQ"

def calculate_metrics(df, symbol, isin):
    """
    Calculate technical metrics for a given stock without applying screening rules.
    Similar to screener_logic.apply_screening but without filtering.
    """
    if df is None or df.empty or len(df) < max(LOOKBACK_PERIOD, AVG_VOLUME_LOOKBACK + 1, EMA_PERIOD_LONG):
        logging.warning(f"[{symbol}] Insufficient data for analysis. Skipping.")
        return None
    
    try:
        # Sort data by timestamp
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        # Calculate EMAs
        df['ema_short'] = df['close'].ewm(span=EMA_PERIOD_SHORT, adjust=False).mean()
        df['ema_long'] = df['close'].ewm(span=EMA_PERIOD_LONG, adjust=False).mean()
        
        # Get latest values
        latest_candle = df.iloc[-1]
        latest_close = latest_candle['close']
        latest_volume = latest_candle['volume']
        latest_timestamp = latest_candle['timestamp']
        latest_ema_long = latest_candle['ema_long']
        latest_ema_short = latest_candle['ema_short']
        
        # Calculate period high/low
        lookback_df = df.iloc[-LOOKBACK_PERIOD:]
        period_high = lookback_df['high'].max()
        period_low = lookback_df['low'].min()
        
        # Calculate average volume
        avg_volume_df = df.iloc[-(AVG_VOLUME_LOOKBACK + 1):-1]
        avg_volume = avg_volume_df['volume'].mean()
        
        # Calculate volume ratio and price drop %
        volume_ratio = latest_volume / avg_volume if avg_volume > 0 else 0
        price_drop_pct = 100 * ((period_high - latest_close) / period_high) if period_high > 0 else 0
        
        # Filter by price range
        if not (MIN_PRICE <= latest_close <= MAX_PRICE):
            return None
            
        return {
            'symbol': symbol,
            'isin': isin,
            'close': latest_close,
            'ema_20': latest_ema_short,
            'ema_50': latest_ema_long,
            'period_high': period_high,
            'period_low': period_low,
            'volume': latest_volume,
            'avg_volume_50d': avg_volume,
            'volume_ratio': volume_ratio,
            'price_drop_pct': price_drop_pct,
            'timestamp': latest_timestamp
        }
        
    except Exception as e:
        logging.error(f"[{symbol}] Error calculating metrics: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return None

def process_stock(stock, to_date_str, from_date_str):
    """Process a single stock to fetch data and calculate metrics."""
    symbol = stock['symbol']
    isin = stock['isin']
    instrument_key = f"{EXCHANGE}_{INSTRUMENT_TYPE}|{isin}"
    
    logging.info(f"Processing: {symbol} ({instrument_key})")
    
    try:
        historical_df = fetch_historical_data(
            instrument_key=instrument_key,
            interval=FETCH_INTERVAL,
            to_date=to_date_str,
            from_date=from_date_str
        )
        
        if historical_df is None:
            logging.warning(f"[{symbol}] No data fetched. Skipping.")
            return None
        
        return calculate_metrics(historical_df, symbol, isin)
        
    except Exception as e:
        logging.error(f"[{symbol}] Exception during processing: {e}")
        return None

def generate_csv_report():
    """Main function to generate CSV report with stock metrics."""
    start_time = time.time()
    logging.info("=" * 50)
    logging.info("Starting CSV Report Generation")
    logging.info("=" * 50)
    
    # 0. Ensure token exists
    if not get_access_token():
        logging.error("Cannot generate report without a valid access token. Exiting.")
        return
    
    # 1. Load validated stock list
    valid_stock_list_file = config.settings['paths']['valid_stock_list_file']
    logging.info(f"Loading validated stock list from: {valid_stock_list_file}")
    
    if not os.path.exists(valid_stock_list_file):
        logging.error(f"Validated stock list '{valid_stock_list_file}' not found.")
        return
    
    stocks_to_scan = load_stock_list(valid_stock_list_file)
    if not stocks_to_scan:
        logging.error(f"No stocks loaded from '{valid_stock_list_file}'. Exiting.")
        return
    
    logging.info(f"Loaded {len(stocks_to_scan)} stocks for analysis.")
    
    # 2. Define date range
    to_date_str = datetime.now().strftime('%Y-%m-%d')
    from_date_str = (datetime.now() - timedelta(days=LOOKBACK_DAYS)).strftime('%Y-%m-%d')
    
    # 3. Process stocks and calculate metrics
    logging.info("Starting data fetching and metrics calculation...")
    all_metrics = []
    fetch_errors = 0
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(process_stock, stock, to_date_str, from_date_str): stock for stock in stocks_to_scan}
        for future in as_completed(futures):
            metrics = future.result()
            if metrics is not None:
                all_metrics.append(metrics)
            else:
                fetch_errors += 1
    
    # 4. Create CSV report
    if all_metrics:
        # Create DataFrame and save to CSV
        df = pd.DataFrame(all_metrics)
        
        # Create analysis directory if it doesn't exist
        analysis_dir = os.path.join(project_root, "analysis")
        os.makedirs(analysis_dir, exist_ok=True)
        
        # Format the timestamp for filename
        today_date = datetime.now().strftime('%Y%m%d')
        csv_filename = os.path.join(analysis_dir, f"analysis_{today_date}.csv")
        
        # Select and reorder columns
        columns = ['symbol', 'isin', 'close', 'ema_20', 'ema_50', 'period_high', 
                  'period_low', 'volume', 'avg_volume_50d', 'volume_ratio', 'price_drop_pct']
        
        df = df[columns]
        
        # Save to CSV
        df.to_csv(csv_filename, index=True)
        logging.info(f"CSV report generated: {csv_filename}")
        logging.info(f"Total stocks in report: {len(df)}")
    else:
        logging.warning("No stock data available for CSV report.")
    
    processing_time = time.time() - start_time
    logging.info(f"CSV report generation completed in {processing_time:.2f} seconds")
    logging.info(f"Data fetch errors: {fetch_errors}")
    logging.info("=" * 50)

if __name__ == "__main__":
    generate_csv_report()
