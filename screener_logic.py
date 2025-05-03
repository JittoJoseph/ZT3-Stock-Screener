import pandas as pd
import numpy as np
import math
from utils.helpers import logging
import config # Imports the config module (config.py)

# --- Configuration from config.settings ---
screener_config = config.settings['screener'] # Get the screener sub-dictionary

# Rule 1: Trend Alignment
EMA_PERIOD_SHORT = screener_config['ema_period_short']
EMA_PERIOD_LONG = screener_config['ema_period_long']

# Rule 2: Proximity to 50-Day High
LOOKBACK_PERIOD = screener_config['lookback_period']
PRICE_DROP_FROM_HIGH_PERCENT_MIN = screener_config['price_drop_percent_min']
PRICE_DROP_FROM_HIGH_PERCENT_MAX = screener_config['price_drop_percent_max']

# Rule 3: Volume Ratio Filter
AVG_VOLUME_LOOKBACK = screener_config['avg_volume_lookback']
VOLUME_SURGE_MULTIPLIER_MIN = screener_config['volume_surge_min']
VOLUME_SURGE_MULTIPLIER_MAX = screener_config['volume_surge_max']

# Rule 4: Price Range Filter
MIN_CLOSE_PRICE = screener_config['min_price']
MAX_PRICE = screener_config['max_price']

TOTAL_RULES = 4

def apply_screening(df, symbol):
    """
    Applies the 4 screening conditions and returns detailed results including 
    pass/fail status for each rule and the total number of rules passed.

    Args:
        df (pd.DataFrame): DataFrame with historical candle data.
        symbol (str): The stock symbol.

    Returns:
        dict: A dictionary containing screening results.
    """
    results = {
        'symbol': symbol,
        'close': None,
        'period_high': None,
        'period_low': None,
        'volume': None,
        'avg_volume_50d': None,
        'timestamp': None,
        'passed_rule1': False, # Trend Alignment: Close > EMA(20) > EMA(50)
        'passed_rule2': False, # Proximity: 0% < Drop% < 10%
        'passed_rule3': False, # Volume Ratio: Between 2.0x and 2.5x
        'passed_rule4': False, # Price Range: ₹25 < Close < ₹1500
        # Rule 5 (Liquidity Filter) removed
        'rules_passed_count': 0,
        'metrics': {},
        'failed_overall': True,
        'reason': None
    }

    # Check for sufficient data
    required_candles = max(LOOKBACK_PERIOD, AVG_VOLUME_LOOKBACK + 1, EMA_PERIOD_LONG, EMA_PERIOD_SHORT)
    if df is None or df.empty:
        logging.warning(f"[{symbol}] No data provided for screening.")
        results['reason'] = "No data"
        return results

    if len(df) < required_candles:
         logging.warning(f"[{symbol}] Insufficient data ({len(df)} candles) for lookback/avg volume/EMAs ({required_candles} required). Skipping.")
         results['reason'] = f"Insufficient data ({len(df)} < {required_candles})"
         return results

    try:
        df = df.sort_values('timestamp').reset_index(drop=True)

        # Calculate EMAs
        df['ema_short'] = df['close'].ewm(span=EMA_PERIOD_SHORT, adjust=False).mean() # EMA(20)
        df['ema_long'] = df['close'].ewm(span=EMA_PERIOD_LONG, adjust=False).mean()   # EMA(50)

        latest_candle = df.iloc[-1]
        latest_close = latest_candle['close']
        latest_volume = latest_candle['volume']
        latest_timestamp = latest_candle['timestamp']
        latest_ema_short = latest_candle['ema_short'] # EMA(20)
        latest_ema_long = latest_candle['ema_long']   # EMA(50)

        lookback_df = df.iloc[-LOOKBACK_PERIOD:]
        period_high = lookback_df['high'].max()
        period_low = lookback_df['low'].min()

        avg_volume_df = df.iloc[-(AVG_VOLUME_LOOKBACK + 1):-1]
        avg_volume_lookback_val = avg_volume_df['volume'].mean()

        results.update({
            'close': latest_close,
            'period_high': period_high,
            'period_low': period_low,
            'volume': latest_volume,
            'avg_volume_50d': avg_volume_lookback_val,
            'timestamp': latest_timestamp,
        })

        # --- Handle potential NaN/Zero values ---
        if pd.isna(latest_close) or pd.isna(latest_volume) or pd.isna(period_high) or pd.isna(period_low) or pd.isna(avg_volume_lookback_val) or pd.isna(latest_ema_long) or pd.isna(latest_ema_short) or period_high == 0 or period_low == 0 or avg_volume_lookback_val == 0:
            logging.warning(f"[{symbol}] Skipping due to NaN/zero values in critical data (Close: {latest_close}, Vol: {latest_volume}, High: {period_high}, Low: {period_low}, AvgVol: {avg_volume_lookback_val}, EMA{EMA_PERIOD_SHORT}: {latest_ema_short}, EMA{EMA_PERIOD_LONG}: {latest_ema_long}).")
            results['reason'] = "NaN/Zero in critical data"
            return results

        # --- Apply New Screening Conditions ---
        rules_passed_count = 0

        price_drop_pct = 100 * ((period_high - latest_close) / period_high) if period_high > 0 else 0
        volume_ratio = latest_volume / avg_volume_lookback_val if avg_volume_lookback_val > 0 else 0

        results['metrics'] = {
            'price_drop_pct': price_drop_pct,
            'close_price': latest_close,
            'ema_20': latest_ema_short,
            'ema_50': latest_ema_long,
            'volume': latest_volume,
            'avg_volume_50d': avg_volume_lookback_val,
            'volume_ratio': volume_ratio
        }

        # Rule 1: Trend Alignment - Close > EMA(20) > EMA(50)
        if latest_close > latest_ema_short > latest_ema_long:
            results['passed_rule1'] = True
            rules_passed_count += 1

        # Rule 2: Proximity to 50-Day High - 0% < Price Drop < 10%
        if PRICE_DROP_FROM_HIGH_PERCENT_MIN < price_drop_pct < PRICE_DROP_FROM_HIGH_PERCENT_MAX:
             results['passed_rule2'] = True
             rules_passed_count += 1

        # Rule 3: Volume Ratio Filter - Between 2.0x and 2.5x
        if VOLUME_SURGE_MULTIPLIER_MIN < volume_ratio < VOLUME_SURGE_MULTIPLIER_MAX:
            results['passed_rule3'] = True
            rules_passed_count += 1

        # Rule 4: Price Range Filter - ₹25 < Close < ₹1500
        if MIN_CLOSE_PRICE < latest_close < MAX_PRICE:
            results['passed_rule4'] = True
            rules_passed_count += 1

        # Rule 5 (Liquidity Filter) removed

        # Update total count
        results['rules_passed_count'] = rules_passed_count

        # --- Logging Detailed Checks ---
        logging.debug(f"[{symbol}] Latest Close: {latest_close:.2f}, Latest Vol: {latest_volume:,.0f}, Avg Vol ({AVG_VOLUME_LOOKBACK}D): {avg_volume_lookback_val:,.0f}")
        logging.debug(f"[{symbol}] Period High ({LOOKBACK_PERIOD}D): {period_high:.2f}, Period Low ({LOOKBACK_PERIOD}D): {period_low:.2f}")
        logging.debug(f"[{symbol}] EMA({EMA_PERIOD_SHORT}): {latest_ema_short:.2f}, EMA({EMA_PERIOD_LONG}): {latest_ema_long:.2f}")
        logging.debug(f"[{symbol}] Rule 1 (Close > EMA({EMA_PERIOD_SHORT}) > EMA({EMA_PERIOD_LONG})): {latest_close:.2f} > {latest_ema_short:.2f} > {latest_ema_long:.2f} -> {'PASS' if results['passed_rule1'] else 'FAIL'}")
        logging.debug(f"[{symbol}] Rule 2 ({PRICE_DROP_FROM_HIGH_PERCENT_MIN}% < Drop < {PRICE_DROP_FROM_HIGH_PERCENT_MAX}%): {price_drop_pct:.2f}% -> {'PASS' if results['passed_rule2'] else 'FAIL'}")
        logging.debug(f"[{symbol}] Rule 3 ({VOLUME_SURGE_MULTIPLIER_MIN}x < Vol Ratio < {VOLUME_SURGE_MULTIPLIER_MAX}x): {volume_ratio:.2f}x -> {'PASS' if results['passed_rule3'] else 'FAIL'}")
        logging.debug(f"[{symbol}] Rule 4 (₹{MIN_CLOSE_PRICE} < Price < ₹{MAX_PRICE}): {latest_close:.2f} -> {'PASS' if results['passed_rule4'] else 'FAIL'}")
        logging.debug(f"[{symbol}] Total Rules Passed: {rules_passed_count}/{TOTAL_RULES}")

        # --- Final Check: All conditions must be met ---
        if rules_passed_count == TOTAL_RULES:  # Must pass all 4 rules
            results['failed_overall'] = False
            results['reason'] = "Passed all criteria"
            logging.info(f"[{symbol}] Passed all {TOTAL_RULES} screening conditions.")
        else:
            results['failed_overall'] = True
            failed_rules = []
            if not results['passed_rule1']: failed_rules.append(f"Rule1(Trend)")
            if not results['passed_rule2']: failed_rules.append(f"Rule2(Drop%)")
            if not results['passed_rule3']: failed_rules.append(f"Rule3(VolRatio)")
            if not results['passed_rule4']: failed_rules.append(f"Rule4(PriceRange)")
            results['reason'] = f"Failed: {', '.join(failed_rules)}"
            logging.info(f"[{symbol}] Did not pass all screening conditions. Passed {results['rules_passed_count']}/{TOTAL_RULES} rules.")

        return results

    except Exception as e:
        logging.error(f"[{symbol}] Error during screening logic application: {e}")
        import traceback
        logging.error(traceback.format_exc())
        results['reason'] = f"Error: {e}"
        results['failed_overall'] = True
        return results
