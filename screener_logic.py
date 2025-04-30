import pandas as pd
import numpy as np
import math
from utils.helpers import logging
import config

# --- Configuration ---
LOOKBACK_PERIOD = config.settings['screener']['lookback_period'] # 50
MIN_CLOSE_PRICE = 25.0 # 25
PRICE_DROP_FROM_HIGH_PERCENT_MAX = 10.0
PRICE_DROP_FROM_HIGH_PERCENT_MIN = 0.0
EMA_PERIOD_LONG = 50 # Renamed for clarity
EMA_PERIOD_SHORT = 20 # New short EMA period
AVG_VOLUME_LOOKBACK = 50 # 50
VOLUME_SURGE_MULTIPLIER_MIN = 2.0
VOLUME_SURGE_MULTIPLIER_MAX = 2.5

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
        'avg_volume_50d': None,
        'timestamp': None,
        'passed_rule1': False,
        'passed_rule2': False,
        'passed_rule3': False,
        'passed_rule4': False,
        'passed_rule5': False,
        'passed_rule6': False,
        'rules_passed_count': 0,
        'metrics': {},
        'failed_overall': True,
        'reason': None
    }

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
        avg_volume_50d = avg_volume_df['volume'].mean()

        results.update({
            'close': latest_close,
            'period_high': period_high,
            'period_low': period_low,
            'volume': latest_volume,
            'avg_volume_50d': avg_volume_50d,
            'timestamp': latest_timestamp,
        })

        # --- Handle potential NaN/Zero values ---
        # Include latest_ema_short in the check
        if pd.isna(latest_close) or pd.isna(latest_volume) or pd.isna(period_high) or pd.isna(period_low) or pd.isna(avg_volume_50d) or pd.isna(latest_ema_long) or pd.isna(latest_ema_short) or period_high == 0 or period_low == 0 or avg_volume_50d == 0:
            logging.warning(f"[{symbol}] Skipping due to NaN/zero values in critical data (Close: {latest_close}, Vol: {latest_volume}, High: {period_high}, Low: {period_low}, AvgVol: {avg_volume_50d}, EMA{EMA_PERIOD_LONG}: {latest_ema_long}, EMA{EMA_PERIOD_SHORT}: {latest_ema_short}).")
            results['reason'] = "NaN/Zero in critical data"
            return results

        # --- Apply Screening Conditions (Now 6 Rules) ---
        rules_passed_count = 0

        price_drop_pct = 100 * ((period_high - latest_close) / period_high)
        volume_ratio = latest_volume / avg_volume_50d if avg_volume_50d > 0 else 0

        results['metrics'] = {
            'price_drop_pct': price_drop_pct,
            'close_price': latest_close,
            'ema_50': latest_ema_long, # Keep key as ema_50 for compatibility? Or change? Let's keep for now.
            'ema_20': latest_ema_short, # Add new EMA metric
            'volume': latest_volume,
            'avg_volume_50d': avg_volume_50d,
            'volume_ratio': volume_ratio
        }

        # Rule 1: Price drop < 10% (50d high)
        if price_drop_pct < PRICE_DROP_FROM_HIGH_PERCENT_MAX:
            results['passed_rule1'] = True
            rules_passed_count += 1

        # Rule 2: Price drop > 0% (50d high)
        if price_drop_pct > PRICE_DROP_FROM_HIGH_PERCENT_MIN:
             results['passed_rule2'] = True
             rules_passed_count += 1

        # Rule 3: Close > EMA(50)
        if latest_close > latest_ema_long:
            results['passed_rule3'] = True
            rules_passed_count += 1

        # Rule 4: Current price > 25
        if latest_close > MIN_CLOSE_PRICE:
            results['passed_rule4'] = True
            rules_passed_count += 1

        # Rule 5: Volume Ratio between 2.0x and 2.5x Average Volume (50d) - Updated Check
        if VOLUME_SURGE_MULTIPLIER_MIN < volume_ratio < VOLUME_SURGE_MULTIPLIER_MAX:
            results['passed_rule5'] = True
            rules_passed_count += 1

        # Rule 6: EMA(20) > EMA(50) - New Rule
        if latest_ema_short > latest_ema_long:
            results['passed_rule6'] = True
            rules_passed_count += 1

        # Update total count (now 6 rules)
        results['rules_passed_count'] = rules_passed_count

        # --- Logging Detailed Checks ---
        logging.debug(f"[{symbol}] Latest Close: {latest_close:.2f}, Latest Vol: {latest_volume:,.0f}, Avg Vol ({AVG_VOLUME_LOOKBACK}D): {avg_volume_50d:,.0f}")
        logging.debug(f"[{symbol}] Period High ({LOOKBACK_PERIOD}D): {period_high:.2f}, Period Low ({LOOKBACK_PERIOD}D): {period_low:.2f}")
        logging.debug(f"[{symbol}] EMA({EMA_PERIOD_SHORT}): {latest_ema_short:.2f}, EMA({EMA_PERIOD_LONG}): {latest_ema_long:.2f}") # Log both EMAs
        logging.debug(f"[{symbol}] Rule 1 (% Drop < {PRICE_DROP_FROM_HIGH_PERCENT_MAX}%): {price_drop_pct:.2f}% -> {'PASS' if results['passed_rule1'] else 'FAIL'}")
        logging.debug(f"[{symbol}] Rule 2 (% Drop > {PRICE_DROP_FROM_HIGH_PERCENT_MIN}%): {price_drop_pct:.2f}% -> {'PASS' if results['passed_rule2'] else 'FAIL'}")
        logging.debug(f"[{symbol}] Rule 3 (Close > EMA({EMA_PERIOD_LONG})): {latest_close:.2f} > {latest_ema_long:.2f} -> {'PASS' if results['passed_rule3'] else 'FAIL'}")
        logging.debug(f"[{symbol}] Rule 4 (Close > {MIN_CLOSE_PRICE}): {latest_close:.2f} -> {'PASS' if results['passed_rule4'] else 'FAIL'}")
        logging.debug(f"[{symbol}] Rule 5 ({VOLUME_SURGE_MULTIPLIER_MIN}x < Vol Ratio < {VOLUME_SURGE_MULTIPLIER_MAX}x): {volume_ratio:.2f}x -> {'PASS' if results['passed_rule5'] else 'FAIL'}") # Updated Rule 5 log
        logging.debug(f"[{symbol}] Rule 6 (EMA({EMA_PERIOD_SHORT}) > EMA({EMA_PERIOD_LONG})): {latest_ema_short:.2f} > {latest_ema_long:.2f} -> {'PASS' if results['passed_rule6'] else 'FAIL'}")
        logging.debug(f"[{symbol}] Total Rules Passed: {rules_passed_count}/6") # Updated total


        # --- Final Check: All 6 conditions must be met ---
        all_rules_passed = (
            results['passed_rule1'] and
            results['passed_rule2'] and
            results['passed_rule3'] and
            results['passed_rule4'] and
            results['passed_rule5'] and
            results['passed_rule6'] # Add rule 6 check
        )

        if all_rules_passed:
            results['failed_overall'] = False
            results['reason'] = "Passed all criteria"
            logging.info(f"[{symbol}] Passed all 6 screening conditions.") # Updated count
        else:
            results['failed_overall'] = True
            failed_rules = []
            if not results['passed_rule1']: failed_rules.append("Rule1(Drop%<10)")
            if not results['passed_rule2']: failed_rules.append("Rule2(Drop%>0)")
            if not results['passed_rule3']: failed_rules.append(f"Rule3(Close>EMA{EMA_PERIOD_LONG})")
            if not results['passed_rule4']: failed_rules.append(f"Rule4(Price>{MIN_CLOSE_PRICE})")
            if not results['passed_rule5']: failed_rules.append(f"Rule5({VOLUME_SURGE_MULTIPLIER_MIN}x<Vol<{VOLUME_SURGE_MULTIPLIER_MAX}x)") # Updated failure reason text
            if not results['passed_rule6']: failed_rules.append(f"Rule6(EMA{EMA_PERIOD_SHORT}>EMA{EMA_PERIOD_LONG})") # Add rule 6 failure reason
            results['reason'] = f"Failed: {', '.join(failed_rules)}"
            logging.info(f"[{symbol}] Did not pass all screening conditions. Passed {results['rules_passed_count']}/6 rules.") # Updated count

        return results

    except Exception as e:
        logging.error(f"[{symbol}] Error during screening logic application: {e}")
        import traceback
        logging.error(traceback.format_exc())
        results['reason'] = f"Error: {e}"
        results['failed_overall'] = True # Ensure marked as failed
        return results
