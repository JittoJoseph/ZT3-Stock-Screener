import pandas as pd
import numpy as np
import config
from utils.helpers import logging

def apply_screening(df, symbol):
    """
    Applies the screening conditions to the historical data DataFrame for a single stock.

    Args:
        df (pd.DataFrame): DataFrame containing historical data with columns
                           ['timestamp', 'open', 'high', 'low', 'close', 'volume'].
                           Must be sorted by timestamp ascending.
        symbol (str): The stock symbol (for logging purposes).

    Returns:
        dict: A dictionary containing screening results if the stock passes,
              otherwise None.
              The dict includes: 'symbol', 'isin' (placeholder), 'close',
              'breakout_level', 'volume_surge_pct', 'ema_20'.
              Returns None if data is insufficient or conditions are not met.
    """
    if df is None or df.empty:
        logging.warning(f"[{symbol}] No data provided for screening.")
        return None

    # --- Configuration ---
    lookback = config.settings['screener']['lookback_period']
    vol_factor = config.settings['screener']['volume_surge_factor']
    min_price = config.settings['screener']['price_min']
    max_price = config.settings['screener']['price_max']

    # Ensure we have enough data for lookback calculations (+1 for today)
    if len(df) < lookback + 1:
        logging.warning(f"[{symbol}] Insufficient data for lookback period {lookback} (have {len(df)} days).")
        return None

    # --- Get Today's and Previous Data ---
    # Assuming the last row is the most recent data ('today')
    today = df.iloc[-1]
    previous_data = df.iloc[-(lookback + 1):-1] # Last 'lookback' days *before* today

    if len(previous_data) != lookback:
         logging.warning(f"[{symbol}] Incorrect number of previous days ({len(previous_data)}) for lookback {lookback}.")
         return None

    # --- Calculations ---
    # 1. Breakout Level (Highest close of the lookback period)
    highest_close_lookback = previous_data['close'].max()

    # 2. Average Volume (Average volume of the lookback period)
    avg_volume_lookback = previous_data['volume'].mean()

    # 3. EMA (Calculate EMA on the 'close' price for the entire period available, then get the latest value)
    # Ensure EMA calculation handles potential NaNs if data starts sparse
    df['ema_20'] = df['close'].ewm(span=lookback, adjust=False).mean()
    today_ema_20 = df['ema_20'].iloc[-1] # Get EMA value for 'today'

    # --- Apply Conditions ---
    # Condition 1: Breakout
    breakout_cond = today['close'] > highest_close_lookback
    if not breakout_cond:
        logging.debug(f"[{symbol}] Failed Breakout: Close ({today['close']:.2f}) <= Lookback High ({highest_close_lookback:.2f})")
        return None

    # Condition 2: Volume Surge
    # Avoid division by zero if avg_volume_lookback is 0 or NaN
    volume_surge_pct = 0
    if avg_volume_lookback and not np.isnan(avg_volume_lookback) and avg_volume_lookback > 0:
        volume_surge_pct = ((today['volume'] - avg_volume_lookback) / avg_volume_lookback) * 100
        volume_cond = today['volume'] > (vol_factor * avg_volume_lookback)
    else:
        volume_cond = False # Cannot meet condition if average volume is zero/NaN

    if not volume_cond:
        logging.debug(f"[{symbol}] Failed Volume: Volume ({today['volume']}) <= Factor ({vol_factor}) * Avg Volume ({avg_volume_lookback:.0f})")
        return None

    # Condition 3: Price Range
    price_range_cond = min_price <= today['close'] <= max_price
    if not price_range_cond:
        logging.debug(f"[{symbol}] Failed Price Range: Close ({today['close']:.2f}) not in [{min_price:.2f}, {max_price:.2f}]")
        return None

    # Condition 4: Trend (Above EMA)
    trend_cond = today['close'] > today_ema_20
    if not trend_cond:
        logging.debug(f"[{symbol}] Failed Trend: Close ({today['close']:.2f}) <= EMA(20) ({today_ema_20:.2f})")
        return None

    # --- Passed All Conditions ---
    logging.info(f"[{symbol}] Passed all screening conditions.")
    result = {
        'symbol': symbol,
        # 'isin': df['isin'].iloc[-1], # Assuming ISIN might be added to df later
        'close': round(today['close'], 2),
        'breakout_level': round(highest_close_lookback, 2),
        'volume_surge_pct': round(volume_surge_pct, 2),
        'ema_20': round(today_ema_20, 2),
        'timestamp': today['timestamp'] # Keep the timestamp of the screening day
    }
    return result


# Example usage (for testing later)
if __name__ == '__main__':
    logging.info("Testing screener_logic module...")

    # Create a dummy DataFrame for testing
    dates = pd.to_datetime(pd.date_range(end=datetime.now(), periods=30, freq='B')) # 30 business days
    data = {
        'timestamp': dates,
        'open': np.random.uniform(90, 110, 30),
        'high': np.random.uniform(110, 120, 30),
        'low': np.random.uniform(80, 90, 30),
        'close': np.linspace(90, 150, 30), # Simulate a rising price
        'volume': np.random.randint(100000, 500000, 30)
    }
    test_df = pd.DataFrame(data)

    # --- Test Case 1: Should Pass ---
    logging.info("\n--- Test Case 1: Expected Pass ---")
    test_df_pass = test_df.copy()
    # Ensure last day meets conditions
    lookback_period = config.settings['screener']['lookback_period']
    prev_closes = test_df_pass['close'].iloc[-(lookback_period + 1):-1]
    prev_volumes = test_df_pass['volume'].iloc[-(lookback_period + 1):-1]

    test_df_pass.iloc[-1, test_df_pass.columns.get_loc('close')] = prev_closes.max() + 10 # Breakout
    test_df_pass.iloc[-1, test_df_pass.columns.get_loc('volume')] = prev_volumes.mean() * (config.settings['screener']['volume_surge_factor'] + 0.1) # Volume surge
    # Price range and EMA should be met by the linspace data

    result_pass = apply_screening(test_df_pass, "TESTPASS")
    if result_pass:
        logging.info(f"Test Case 1 Result: PASSED screening. Data: {result_pass}")
    else:
        logging.error("Test Case 1 Result: FAILED screening (unexpected).")


    # --- Test Case 2: Fail Breakout ---
    logging.info("\n--- Test Case 2: Expected Fail (Breakout) ---")
    test_df_fail_bo = test_df_pass.copy()
    test_df_fail_bo.iloc[-1, test_df_fail_bo.columns.get_loc('close')] = prev_closes.max() - 1 # Fail breakout

    result_fail_bo = apply_screening(test_df_fail_bo, "TESTFAIL_BO")
    if not result_fail_bo:
        logging.info("Test Case 2 Result: Correctly FAILED screening.")
    else:
        logging.error(f"Test Case 2 Result: PASSED screening (unexpected). Data: {result_fail_bo}")

    # --- Test Case 3: Fail Volume ---
    logging.info("\n--- Test Case 3: Expected Fail (Volume) ---")
    test_df_fail_vol = test_df_pass.copy()
    test_df_fail_vol.iloc[-1, test_df_fail_vol.columns.get_loc('volume')] = prev_volumes.mean() * (config.settings['screener']['volume_surge_factor'] - 0.1) # Fail volume

    result_fail_vol = apply_screening(test_df_fail_vol, "TESTFAIL_VOL")
    if not result_fail_vol:
        logging.info("Test Case 3 Result: Correctly FAILED screening.")
    else:
        logging.error(f"Test Case 3 Result: PASSED screening (unexpected). Data: {result_fail_vol}")

    # --- Test Case 4: Fail Price Range (Too Low) ---
    logging.info("\n--- Test Case 4: Expected Fail (Price Low) ---")
    test_df_fail_pr_low = test_df_pass.copy()
    test_df_fail_pr_low.iloc[-1, test_df_fail_pr_low.columns.get_loc('close')] = config.settings['screener']['price_min'] - 1 # Fail price range low

    result_fail_pr_low = apply_screening(test_df_fail_pr_low, "TESTFAIL_PRLOW")
    if not result_fail_pr_low:
        logging.info("Test Case 4 Result: Correctly FAILED screening.")
    else:
        logging.error(f"Test Case 4 Result: PASSED screening (unexpected). Data: {result_fail_pr_low}")

    # --- Test Case 5: Fail Trend (Below EMA) ---
    logging.info("\n--- Test Case 5: Expected Fail (Trend/EMA) ---")
    test_df_fail_ema = test_df_pass.copy()
    # Force EMA to be higher than close
    test_df_fail_ema['ema_20_temp'] = test_df_fail_ema['close'].ewm(span=lookback_period, adjust=False).mean()
    test_df_fail_ema.iloc[-1, test_df_fail_ema.columns.get_loc('close')] = test_df_fail_ema['ema_20_temp'].iloc[-1] - 1 # Set close just below calculated EMA

    result_fail_ema = apply_screening(test_df_fail_ema, "TESTFAIL_EMA") # Reruns EMA calc inside
    if not result_fail_ema:
        logging.info("Test Case 5 Result: Correctly FAILED screening.")
    else:
        logging.error(f"Test Case 5 Result: PASSED screening (unexpected). Data: {result_fail_ema}")

    logging.info("\nScreener_logic module test finished.")
