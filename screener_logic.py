import pandas as pd
import numpy as np
import math
from utils.helpers import logging
import config # Imports the config module (config.py)

# --- Configuration from config.settings ---
screener_config = config.settings['screener'] # Get the screener sub-dictionary

LOOKBACK_PERIOD = screener_config['lookback_period']
MIN_CLOSE_PRICE = screener_config['min_price']
MAX_PRICE = screener_config['max_price']
ENABLE_MAX_PRICE_LIMIT = screener_config['enable_max_price_limit']
PRICE_DROP_FROM_HIGH_PERCENT_MAX = screener_config['price_drop_percent_max']
PRICE_DROP_FROM_HIGH_PERCENT_MIN = screener_config['price_drop_percent_min']
EMA_PERIOD_LONG = screener_config['ema_period_long']
EMA_PERIOD_SHORT = screener_config['ema_period_short']
AVG_VOLUME_LOOKBACK = screener_config['avg_volume_lookback'] # Use specific setting
VOLUME_SURGE_MULTIPLIER_MIN = screener_config['volume_surge_min']
VOLUME_SURGE_MULTIPLIER_MAX = screener_config['volume_surge_max']

# Determine total rules based on config
TOTAL_RULES = 7 if ENABLE_MAX_PRICE_LIMIT else 6

def apply_screening(df, symbol):
    """
    Applies the 6 screening conditions (Rule 3 is now Close > EMA(50))
    and returns detailed results including pass/fail status for each rule
    and the total number of rules passed.

    Args:
        df (pd.DataFrame): DataFrame with historical candle data.
        symbol (str): The stock symbol.

    Returns:
        dict: A dictionary containing screening results (symbol, metrics,
              pass/fail status for each rule, rules_passed_count),
              including failure details.
    """
    results = {
        'symbol': symbol,
        'close': None,
        'period_high': None,
        'period_low': None,
        'volume': None,
        'avg_volume_50d': None, # Keep key name consistent for now, value uses AVG_VOLUME_LOOKBACK
        'timestamp': None,
        'passed_rule1': False, # Drop% < MAX %
        'passed_rule2': False, # Drop% > MIN %
        'passed_rule3': False, # Close > EMA(LONG)
        'passed_rule4': False, # Close > MinPrice
        'passed_rule5': False, # MIN < Vol Ratio < MAX
        'passed_rule6': False, # EMA(SHORT) > EMA(LONG)
        # Rule 7 is conditional
        'rules_passed_count': 0,
        'metrics': {},
        'failed_overall': True,
        'reason': None
    }
    # Add Rule 7 pass status only if enabled
    if ENABLE_MAX_PRICE_LIMIT:
        results['passed_rule7'] = False # Close <= MaxPrice

    # Check for sufficient data (Need enough for both EMA calculations)
    required_candles = max(LOOKBACK_PERIOD, AVG_VOLUME_LOOKBACK + 1, EMA_PERIOD_LONG, EMA_PERIOD_SHORT) # Use longest period
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
        df['ema_long'] = df['close'].ewm(span=EMA_PERIOD_LONG, adjust=False).mean() # EMA(50)
        df['ema_short'] = df['close'].ewm(span=EMA_PERIOD_SHORT, adjust=False).mean() # EMA(20)

        latest_candle = df.iloc[-1]
        latest_close = latest_candle['close']
        latest_volume = latest_candle['volume']
        latest_timestamp = latest_candle['timestamp']
        latest_ema_long = latest_candle['ema_long'] # EMA(50)
        latest_ema_short = latest_candle['ema_short'] # EMA(20)

        lookback_df = df.iloc[-LOOKBACK_PERIOD:]
        period_high = lookback_df['high'].max()
        period_low = lookback_df['low'].min()

        avg_volume_df = df.iloc[-(AVG_VOLUME_LOOKBACK + 1):-1]
        avg_volume_lookback_val = avg_volume_df['volume'].mean() # Use the specific lookback

        results.update({
            'close': latest_close,
            'period_high': period_high,
            'period_low': period_low,
            'volume': latest_volume,
            'avg_volume_50d': avg_volume_lookback_val, # Store calculated avg vol here
            'timestamp': latest_timestamp,
        })

        # --- Handle potential NaN/Zero values ---
        if pd.isna(latest_close) or pd.isna(latest_volume) or pd.isna(period_high) or pd.isna(period_low) or pd.isna(avg_volume_lookback_val) or pd.isna(latest_ema_long) or pd.isna(latest_ema_short) or period_high == 0 or period_low == 0 or avg_volume_lookback_val == 0:
            logging.warning(f"[{symbol}] Skipping due to NaN/zero values in critical data (Close: {latest_close}, Vol: {latest_volume}, High: {period_high}, Low: {period_low}, AvgVol: {avg_volume_lookback_val}, EMA{EMA_PERIOD_LONG}: {latest_ema_long}, EMA{EMA_PERIOD_SHORT}: {latest_ema_short}).")
            results['reason'] = "NaN/Zero in critical data"
            return results

        # --- Apply Screening Conditions ---
        rules_passed_count = 0

        price_drop_pct = 100 * ((period_high - latest_close) / period_high) if period_high > 0 else 0
        volume_ratio = latest_volume / avg_volume_lookback_val if avg_volume_lookback_val > 0 else 0

        results['metrics'] = {
            'price_drop_pct': price_drop_pct,
            'close_price': latest_close,
            'ema_50': latest_ema_long, # Key name kept for compatibility
            'ema_20': latest_ema_short, # Key name kept for compatibility
            'volume': latest_volume,
            'avg_volume_50d': avg_volume_lookback_val, # Key name kept for compatibility
            'volume_ratio': volume_ratio
        }

        # Rule 1: Price drop < MAX %
        if price_drop_pct < PRICE_DROP_FROM_HIGH_PERCENT_MAX:
            results['passed_rule1'] = True
            rules_passed_count += 1

        # Rule 2: Price drop > MIN %
        if price_drop_pct > PRICE_DROP_FROM_HIGH_PERCENT_MIN:
             results['passed_rule2'] = True
             rules_passed_count += 1

        # Rule 3: Close > EMA(LONG)
        if latest_close > latest_ema_long:
            results['passed_rule3'] = True
            rules_passed_count += 1

        # Rule 4: Current price > MinPrice
        if latest_close > MIN_CLOSE_PRICE:
            results['passed_rule4'] = True
            rules_passed_count += 1

        # Rule 5: Volume Ratio between Min/Max
        if VOLUME_SURGE_MULTIPLIER_MIN < volume_ratio < VOLUME_SURGE_MULTIPLIER_MAX:
            results['passed_rule5'] = True
            rules_passed_count += 1

        # Rule 6: EMA(SHORT) > EMA(LONG)
        if latest_ema_short > latest_ema_long:
            results['passed_rule6'] = True
            rules_passed_count += 1

        # Rule 7: Current price <= MaxPrice (Conditional)
        rule7_passed = True # Assume pass if rule is disabled
        if ENABLE_MAX_PRICE_LIMIT:
            if latest_close <= MAX_PRICE:
                results['passed_rule7'] = True
                rules_passed_count += 1
                rule7_passed = True
            else:
                results['passed_rule7'] = False
                rule7_passed = False

        # Update total count
        results['rules_passed_count'] = rules_passed_count

        # --- Logging Detailed Checks ---
        logging.debug(f"[{symbol}] Latest Close: {latest_close:.2f}, Latest Vol: {latest_volume:,.0f}, Avg Vol ({AVG_VOLUME_LOOKBACK}D): {avg_volume_lookback_val:,.0f}") # Use calculated avg vol
        logging.debug(f"[{symbol}] Period High ({LOOKBACK_PERIOD}D): {period_high:.2f}, Period Low ({LOOKBACK_PERIOD}D): {period_low:.2f}")
        logging.debug(f"[{symbol}] EMA({EMA_PERIOD_SHORT}): {latest_ema_short:.2f}, EMA({EMA_PERIOD_LONG}): {latest_ema_long:.2f}")
        logging.debug(f"[{symbol}] Rule 1 (% Drop < {PRICE_DROP_FROM_HIGH_PERCENT_MAX}%): {price_drop_pct:.2f}% -> {'PASS' if results['passed_rule1'] else 'FAIL'}")
        logging.debug(f"[{symbol}] Rule 2 (% Drop > {PRICE_DROP_FROM_HIGH_PERCENT_MIN}%): {price_drop_pct:.2f}% -> {'PASS' if results['passed_rule2'] else 'FAIL'}")
        logging.debug(f"[{symbol}] Rule 3 (Close > EMA({EMA_PERIOD_LONG})): {latest_close:.2f} > {latest_ema_long:.2f} -> {'PASS' if results['passed_rule3'] else 'FAIL'}")
        logging.debug(f"[{symbol}] Rule 4 (Close > {MIN_CLOSE_PRICE}): {latest_close:.2f} -> {'PASS' if results['passed_rule4'] else 'FAIL'}")
        logging.debug(f"[{symbol}] Rule 5 ({VOLUME_SURGE_MULTIPLIER_MIN}x < Vol Ratio < {VOLUME_SURGE_MULTIPLIER_MAX}x): {volume_ratio:.2f}x -> {'PASS' if results['passed_rule5'] else 'FAIL'}")
        logging.debug(f"[{symbol}] Rule 6 (EMA({EMA_PERIOD_SHORT}) > EMA({EMA_PERIOD_LONG})): {latest_ema_short:.2f} > {latest_ema_long:.2f} -> {'PASS' if results['passed_rule6'] else 'FAIL'}")
        if ENABLE_MAX_PRICE_LIMIT:
            logging.debug(f"[{symbol}] Rule 7 (Close <= {MAX_PRICE}): {latest_close:.2f} -> {'PASS' if results['passed_rule7'] else 'FAIL'}")
        logging.debug(f"[{symbol}] Total Rules Passed: {rules_passed_count}/{TOTAL_RULES}")


        # --- Final Check: All applicable conditions must be met ---
        # Base rules (1-6)
        all_rules_passed = (
            results['passed_rule1'] and
            results['passed_rule2'] and
            results['passed_rule3'] and
            results['passed_rule4'] and
            results['passed_rule5'] and
            results['passed_rule6']
        )
        # Add rule 7 check if enabled
        if ENABLE_MAX_PRICE_LIMIT:
            all_rules_passed = all_rules_passed and results['passed_rule7']

        if all_rules_passed:
            results['failed_overall'] = False
            results['reason'] = "Passed all criteria"
            logging.info(f"[{symbol}] Passed all {TOTAL_RULES} screening conditions.") # Use TOTAL_RULES
        else:
            results['failed_overall'] = True
            failed_rules = []
            if not results['passed_rule1']: failed_rules.append(f"Rule1(Drop%<{PRICE_DROP_FROM_HIGH_PERCENT_MAX})") # Use config value
            if not results['passed_rule2']: failed_rules.append(f"Rule2(Drop%>{PRICE_DROP_FROM_HIGH_PERCENT_MIN})") # Use config value
            if not results['passed_rule3']: failed_rules.append(f"Rule3(Close>EMA{EMA_PERIOD_LONG})")
            if not results['passed_rule4']: failed_rules.append(f"Rule4(Price>{MIN_CLOSE_PRICE})")
            if not results['passed_rule5']: failed_rules.append(f"Rule5({VOLUME_SURGE_MULTIPLIER_MIN}x<Vol<{VOLUME_SURGE_MULTIPLIER_MAX}x)")
            if not results['passed_rule6']: failed_rules.append(f"Rule6(EMA{EMA_PERIOD_SHORT}>EMA{EMA_PERIOD_LONG})")
            if ENABLE_MAX_PRICE_LIMIT and not results['passed_rule7']: # Add rule 7 failure reason if enabled and failed
                failed_rules.append(f"Rule7(Price<={MAX_PRICE})")
            results['reason'] = f"Failed: {', '.join(failed_rules)}"
            logging.info(f"[{symbol}] Did not pass all screening conditions. Passed {results['rules_passed_count']}/{TOTAL_RULES} rules.") # Use TOTAL_RULES

        return results

    except Exception as e:
        logging.error(f"[{symbol}] Error during screening logic application: {e}")
        import traceback
        logging.error(traceback.format_exc())
        results['reason'] = f"Error: {e}"
        results['failed_overall'] = True # Ensure marked as failed
        return results
