import pandas as pd
import numpy as np
import math # Import math for isnan check
from utils.helpers import logging
import config # Import config module

# --- Configuration ---
LOOKBACK_PERIOD = config.settings['screener']['lookback_period'] # Now 50 from config
# New Rules Constants
MIN_CLOSE_PRICE = 25.0 # Updated minimum price to 25
PRICE_DROP_FROM_HIGH_PERCENT_MAX = 10.0
PRICE_DROP_FROM_HIGH_PERCENT_MIN = 0.0 # Explicitly 0 for the lower bound check
EMA_PERIOD = 50 # Updated EMA Period to 50
AVG_VOLUME_LOOKBACK = 50 # Updated Days for average volume calculation to 50
VOLUME_SURGE_MULTIPLIER = 2.0 # Increased from 1.5 to 2.0

# VOLUME_MULTIPLIER from config is replaced by VOLUME_SURGE_MULTIPLIER
# Price limits from config are replaced by MIN_CLOSE_PRICE

def apply_screening(df, symbol):
    """
    Applies the 5 screening conditions (Rule 3 is now Close > EMA(50))
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
        'avg_volume_50d': None, # Changed key name
        'timestamp': None,
        'passed_rule1': False, # Price drop < 10% (50d High)
        'passed_rule2': False, # Price drop > 0% (50d High)
        'passed_rule3': False, # Close > EMA(50) - Updated Rule
        'passed_rule4': False, # Close > 25 - Updated Rule
        'passed_rule5': False, # Volume > 2.0x Avg Vol (50d) - Updated Rule
        'rules_passed_count': 0,
        'metrics': {}, # Store calculated metrics for reporting
        'failed_overall': True, # Assume failure initially
        'reason': None # Reason for early exit or failure
    }

    # Check for sufficient data (Need enough for EMA calculation too)
    required_candles = max(LOOKBACK_PERIOD, AVG_VOLUME_LOOKBACK + 1, EMA_PERIOD) # Ensure enough for 50-day calculations
    if df is None or df.empty:
        logging.warning(f"[{symbol}] No data provided for screening.")
        results['reason'] = "No data"
        return results # Return partial results

    if len(df) < required_candles:
         logging.warning(f"[{symbol}] Insufficient data ({len(df)} candles) for lookback/avg volume/EMA ({required_candles} required). Skipping.")
         results['reason'] = f"Insufficient data ({len(df)} < {required_candles})"
         return results # Return partial results

    try:
        # Ensure data is sorted by timestamp ascending
        df = df.sort_values('timestamp').reset_index(drop=True)

        # Calculate EMA(50)
        df['ema_50'] = df['close'].ewm(span=EMA_PERIOD, adjust=False).mean() # EMA_PERIOD is now 50

        # Get the latest candle's data
        latest_candle = df.iloc[-1]
        latest_close = latest_candle['close']
        latest_volume = latest_candle['volume']
        latest_timestamp = latest_candle['timestamp']
        latest_ema_50 = latest_candle['ema_50'] # Get the latest EMA value

        # Calculate high and low over the 50-day lookback period
        lookback_df = df.iloc[-LOOKBACK_PERIOD:] # LOOKBACK_PERIOD is now 50
        period_high = lookback_df['high'].max()
        period_low = lookback_df['low'].min()

        # Calculate 50-day average volume (excluding today's volume)
        avg_volume_df = df.iloc[-(AVG_VOLUME_LOOKBACK + 1):-1] # AVG_VOLUME_LOOKBACK is now 50
        avg_volume_50d = avg_volume_df['volume'].mean()

        results.update({
            'close': latest_close,
            'period_high': period_high,
            'period_low': period_low,
            'volume': latest_volume,
            'avg_volume_50d': avg_volume_50d, # Updated key name
            'timestamp': latest_timestamp,
        })

        # --- Handle potential NaN/Zero values ---
        # Include latest_ema_50 in the check
        if pd.isna(latest_close) or pd.isna(latest_volume) or pd.isna(period_high) or pd.isna(period_low) or pd.isna(avg_volume_50d) or pd.isna(latest_ema_50) or period_high == 0 or period_low == 0 or avg_volume_50d == 0:
            logging.warning(f"[{symbol}] Skipping due to NaN/zero values in critical data (Close: {latest_close}, Vol: {latest_volume}, High: {period_high}, Low: {period_low}, AvgVol: {avg_volume_50d}, EMA50: {latest_ema_50}).") # Updated log
            results['reason'] = "NaN/Zero in critical data"
            return results # Return partial results

        # --- Apply New Screening Conditions and Track Pass/Fail ---
        rules_passed_count = 0

        price_drop_pct = 100 * ((period_high - latest_close) / period_high)
        volume_ratio = latest_volume / avg_volume_50d if avg_volume_50d > 0 else 0 # Use avg_volume_50d

        results['metrics'] = {
            'price_drop_pct': price_drop_pct,
            'close_price': latest_close,
            'ema_50': latest_ema_50, # Updated key name
            'volume': latest_volume,
            'avg_volume_50d': avg_volume_50d, # Updated key name
            'volume_ratio': volume_ratio
        }

        # Rule 1: Price drop < 10% (based on 50d high)
        if price_drop_pct < PRICE_DROP_FROM_HIGH_PERCENT_MAX:
            results['passed_rule1'] = True
            rules_passed_count += 1

        # Rule 2: Price drop > 0% (based on 50d high)
        if price_drop_pct > PRICE_DROP_FROM_HIGH_PERCENT_MIN:
             results['passed_rule2'] = True
             rules_passed_count += 1

        # Rule 3: Close > EMA(50) - New Rule
        if latest_close > latest_ema_50: # Use latest_ema_50
            results['passed_rule3'] = True
            rules_passed_count += 1

        # Rule 4: Current price > 25 - Updated Rule
        if latest_close > MIN_CLOSE_PRICE: # MIN_CLOSE_PRICE is now 25.0
            results['passed_rule4'] = True
            rules_passed_count += 1

        # Rule 5: Volume > 2.0x Average Volume (50d) - Updated Check
        if volume_ratio > VOLUME_SURGE_MULTIPLIER: # volume_ratio now uses 50d avg
            results['passed_rule5'] = True
            rules_passed_count += 1

        # Update total count (still 5 rules)
        results['rules_passed_count'] = rules_passed_count

        # --- Logging Detailed Checks ---
        logging.debug(f"[{symbol}] Latest Close: {latest_close:.2f}, Latest Vol: {latest_volume:,.0f}, Avg Vol ({AVG_VOLUME_LOOKBACK}D): {avg_volume_50d:,.0f}") # Updated avg vol period
        logging.debug(f"[{symbol}] Period High ({LOOKBACK_PERIOD}D): {period_high:.2f}, Period Low ({LOOKBACK_PERIOD}D): {period_low:.2f}") # Updated lookback period
        logging.debug(f"[{symbol}] EMA({EMA_PERIOD}): {latest_ema_50:.2f}") # Log EMA 50
        logging.debug(f"[{symbol}] Rule 1 (% Drop < {PRICE_DROP_FROM_HIGH_PERCENT_MAX}%): {price_drop_pct:.2f}% -> {'PASS' if results['passed_rule1'] else 'FAIL'}")
        logging.debug(f"[{symbol}] Rule 2 (% Drop > {PRICE_DROP_FROM_HIGH_PERCENT_MIN}%): {price_drop_pct:.2f}% -> {'PASS' if results['passed_rule2'] else 'FAIL'}")
        logging.debug(f"[{symbol}] Rule 3 (Close > EMA({EMA_PERIOD})): {latest_close:.2f} > {latest_ema_50:.2f} -> {'PASS' if results['passed_rule3'] else 'FAIL'}") # Updated EMA period
        logging.debug(f"[{symbol}] Rule 4 (Close > {MIN_CLOSE_PRICE}): {latest_close:.2f} -> {'PASS' if results['passed_rule4'] else 'FAIL'}") # Updated price check
        logging.debug(f"[{symbol}] Rule 5 (Vol > {VOLUME_SURGE_MULTIPLIER}x Avg): {volume_ratio:.2f}x -> {'PASS' if results['passed_rule5'] else 'FAIL'}")
        logging.debug(f"[{symbol}] Total Rules Passed: {rules_passed_count}/5")


        # --- Final Check: All 5 conditions must be met for overall pass ---
        all_rules_passed = (
            results['passed_rule1'] and
            results['passed_rule2'] and
            results['passed_rule3'] and # Check uses the updated rule flag
            results['passed_rule4'] and
            results['passed_rule5']
        )

        if all_rules_passed:
            results['failed_overall'] = False
            results['reason'] = "Passed all criteria"
            logging.info(f"[{symbol}] Passed all 5 screening conditions.")
        else:
            results['failed_overall'] = True
            failed_rules = []
            if not results['passed_rule1']: failed_rules.append("Rule1(Drop%<10)")
            if not results['passed_rule2']: failed_rules.append("Rule2(Drop%>0)")
            if not results['passed_rule3']: failed_rules.append(f"Rule3(Close>EMA{EMA_PERIOD})") # Updated EMA period
            if not results['passed_rule4']: failed_rules.append(f"Rule4(Price>{MIN_CLOSE_PRICE})") # Updated price rule text
            if not results['passed_rule5']: failed_rules.append(f"Rule5(Vol>{VOLUME_SURGE_MULTIPLIER}x)") # Updated failure reason text
            results['reason'] = f"Failed: {', '.join(failed_rules)}"
            logging.info(f"[{symbol}] Did not pass all screening conditions. Passed {results['rules_passed_count']}/5 rules.")

        return results # Return the detailed results dictionary regardless of pass/fail

    except Exception as e:
        logging.error(f"[{symbol}] Error during screening logic application: {e}")
        import traceback
        logging.error(traceback.format_exc())
        results['reason'] = f"Error: {e}"
        results['failed_overall'] = True # Ensure marked as failed
        return results # Return partial results with error
