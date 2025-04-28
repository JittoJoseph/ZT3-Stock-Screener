import pandas as pd
import numpy as np
import math # Import math for isnan check
from utils.helpers import logging
import config # Import config module

# --- Configuration ---
LOOKBACK_PERIOD = config.settings['screener']['lookback_period']
VOLUME_MULTIPLIER = config.settings['screener']['volume_multiplier']
MIN_PRICE = config.settings['screener']['price_limits']['min_price']
# Get max price settings from config
MAX_PRICE = config.settings['screener']['price_limits']['max_price']
ENABLE_MAX_PRICE_LIMIT = config.settings['screener']['price_limits']['enable_max_price_limit']
EMA_PERIOD = 20 # Fixed EMA period

def apply_screening(df, symbol):
    """
    Applies the breakout, volume, price range, and trend conditions to the historical data.

    Args:
        df (pd.DataFrame): DataFrame with historical candle data. Must contain
                           ['timestamp', 'close', 'high', 'low', 'volume'].
        symbol (str): The stock symbol (for logging purposes).

    Returns:
        dict: A dictionary containing screening results if conditions are met,
              otherwise None.
    """
    if df is None or df.empty:
        logging.warning(f"[{symbol}] No data provided for screening.")
        return None

    try:
        # Ensure data is sorted by timestamp ascending
        df = df.sort_values('timestamp').reset_index(drop=True)

        # Calculate required indicators
        df['ema_20'] = df['close'].ewm(span=EMA_PERIOD, adjust=False).mean()
        df['avg_vol_20'] = df['volume'].rolling(window=LOOKBACK_PERIOD).mean()
        # Calculate highest close of the lookback period *excluding* the latest candle
        df['highest_close_prev_20'] = df['close'].rolling(window=LOOKBACK_PERIOD).max().shift(1)

        # Get the latest candle's data
        latest_candle = df.iloc[-1]

        # --- Apply Screening Conditions ---
        # 1. Breakout Condition
        breakout_level = latest_candle['highest_close_prev_20']
        # Handle potential NaN in breakout_level before comparison
        breakout_condition = not pd.isna(breakout_level) and latest_candle['close'] > breakout_level

        # 2. Volume Condition
        avg_volume = latest_candle['avg_vol_20']
        # Handle potential NaN in avg_volume and latest_candle['volume']
        volume_condition = (
            not pd.isna(avg_volume) and avg_volume > 0 and
            not pd.isna(latest_candle['volume']) and
            latest_candle['volume'] > (avg_volume * VOLUME_MULTIPLIER)
        )

        # 3. Price Range Condition (Modified)
        min_price_condition = latest_candle['close'] >= MIN_PRICE
        # Apply max price limit only if enabled in config
        if ENABLE_MAX_PRICE_LIMIT:
            max_price_condition = latest_candle['close'] <= MAX_PRICE
            price_range_condition = min_price_condition and max_price_condition
            price_range_log = f"{MIN_PRICE} <= Close <= {MAX_PRICE}"
        else:
            # If max price limit is disabled, only check min price
            price_range_condition = min_price_condition
            price_range_log = f"Close >= {MIN_PRICE} (Max limit disabled)"

        # 4. Trend Condition
        ema_value = latest_candle['ema_20']
        # Handle potential NaN in ema_value
        trend_condition = not pd.isna(ema_value) and latest_candle['close'] > ema_value

        # --- Logging Detailed Checks ---
        logging.debug(f"[{symbol}] Latest Close: {latest_candle['close']:.2f}")
        # Handle NaN for breakout level logging
        breakout_level_str = f"{breakout_level:.2f}" if not pd.isna(breakout_level) else "NaN"
        logging.debug(f"[{symbol}] Breakout Level (Highest Close Prev {LOOKBACK_PERIOD}D): {breakout_level_str} -> {'PASS' if breakout_condition else 'FAIL'}")

        # Safely format volume log line, handling potential NaN
        avg_vol_str = f"{avg_volume:.0f}" if not pd.isna(avg_volume) else "NaN"
        req_vol_str = f"{(avg_volume * VOLUME_MULTIPLIER):.0f}" if not pd.isna(avg_volume) else "NaN"
        latest_vol_str = f"{latest_candle['volume']}" if not pd.isna(latest_candle['volume']) else "NaN"
        logging.debug(f"[{symbol}] Latest Volume: {latest_vol_str} | Avg Vol ({LOOKBACK_PERIOD}D): {avg_vol_str} | Required: > {req_vol_str} -> {'PASS' if volume_condition else 'FAIL'}")

        logging.debug(f"[{symbol}] Price Range Check ({price_range_log}): {latest_candle['close']:.2f} -> {'PASS' if price_range_condition else 'FAIL'}")
        # Handle NaN for EMA logging
        ema_value_str = f"{ema_value:.2f}" if not pd.isna(ema_value) else "NaN"
        logging.debug(f"[{symbol}] EMA({EMA_PERIOD}): {ema_value_str} | Close > EMA -> {'PASS' if trend_condition else 'FAIL'}")

        # --- Final Check: All conditions must be met ---
        if breakout_condition and volume_condition and price_range_condition and trend_condition:
            logging.info(f"[{symbol}] Passed all screening conditions.")
            # Ensure avg_volume is not NaN or zero before calculating surge percentage
            if not pd.isna(avg_volume) and avg_volume > 0 and not pd.isna(latest_candle['volume']):
                volume_surge_pct = ((latest_candle['volume'] / avg_volume) - 1) * 100
            else:
                volume_surge_pct = float('inf') # Or handle as appropriate, maybe 0 or None

            latest_volume = latest_candle['volume']
            # --- Remove Debug Log ---
            # logging.debug(f"[{symbol}] Volume value being returned: {latest_volume} (Type: {type(latest_volume)})")
            # --- End Remove Debug Log ---

            return {
                'symbol': symbol,
                'close': latest_candle['close'],
                'breakout_level': breakout_level,
                'volume_surge_pct': volume_surge_pct,
                'ema_20': ema_value,
                'timestamp': latest_candle['timestamp'],
                'volume': latest_volume
            }
        else:
            logging.info(f"[{symbol}] Did not pass all screening conditions.")
            return None

    except Exception as e:
        logging.error(f"[{symbol}] Error during screening logic application: {e}")
        # Optionally log traceback for debugging
        import traceback
        logging.error(traceback.format_exc()) # Add traceback for detailed error info
        return None
