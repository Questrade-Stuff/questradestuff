#!/usr/bin/env python3
"""
opening_rebound_score.py
Compute a daily “opening‑rebound (✓‑mark) score” for every security that has
09:30–10:00 1‑minute candles in the local MySQL database and maintain a 30‑day
EMA of that score.

Tables used / created:
  • candlestick_data   – minute candles you already collect
  • market_holidays    – yyyy‑mm‑dd rows to skip
  • pattern_scores     – (symbolId, date, opening_rebound_score)
  • ema_scores         – (symbolId, ema_score, last_updated)
"""

import pymysql
from pymysql.cursors import DictCursor
from datetime import timedelta
from questrade_api import QuestradeAPI
from credentials import (
    MYSQL_HOST,
    MYSQL_USER,
    MYSQL_PASSWORD,
    MYSQL_DATABASE,
)

# ─────────────────────────── PARAMETERS ────────────────────────────
DROP_WINDOW_MIN    = 10            # minutes (09:30→09:39)
EVAL_END_TIME      = "10:00:00"    # exclusive upper bound
MAX_LINGER_MIN     = 10
EMA_PERIOD_DAYS    = 30
DROP_WEIGHT        = 0.5
RECO_WEIGHT        = 0.3
LINGER_WEIGHT      = 0.2
# ────────────────────────────────────────────────────────────────────

qt = QuestradeAPI(user_id=1)  # still handy for ad‑hoc queries later

def connect_to_db():
    return pymysql.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        cursorclass=DictCursor,
    )

# -------------------------------------------------------------------
# 1. Data utilities
# -------------------------------------------------------------------
def get_candlestick_data(symbol_id, trade_date):
    """Return all 09:30–09:59 candles (inclusive/exclusive) for one day."""
    conn = connect_to_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT *
                FROM candlestick_data
                WHERE symbolId = %s
                  AND DATE(start) = %s
                  AND TIME(start) >= '09:30:00'
                  AND TIME(start) <  %s
                ORDER BY start ASC
                """,
                (symbol_id, trade_date, EVAL_END_TIME),
            )
            return cur.fetchall()
    finally:
        conn.close()

# -------------------------------------------------------------------
# 2. Scoring
# -------------------------------------------------------------------
def calculate_opening_rebound_score(candles):
    """Return 0‑100 float or None if not enough data."""
    if len(candles) < DROP_WINDOW_MIN:
        return None

    open_px = candles[0]["open"]

    # Low during the first 10 minutes
    lows = [c["low"] for c in candles[:DROP_WINDOW_MIN]]
    low_px = min(lows)
    low_idx = lows.index(low_px)          # index of first occurrence
    low_ts = candles[low_idx]["start"]

    # Percentage drop from open to low
    pct_drop = (open_px - low_px) / open_px * 100.0

    # Rebound measured at 10:00 candle close (last candle we fetched)
    close10_px = candles[-1]["close"]
    denom = open_px - low_px
    if denom == 0.0:
        pct_reco = 0.0
    else:
        pct_reco = (close10_px - low_px) / denom * 100.0
    pct_reco = max(0.0, min(100.0, pct_reco))  # clamp 0–100

    # Linger = number of minutes the low price persisted (capped)
    linger = sum(1 for c in candles if c["low"] == low_px)
    linger = min(linger, MAX_LINGER_MIN)

    raw = (
        DROP_WEIGHT   * pct_drop +
        RECO_WEIGHT   * pct_reco +
        LINGER_WEIGHT * (1 - linger / MAX_LINGER_MIN) * 100
    )
    return round(max(0.0, min(100.0, raw)), 2)

# -------------------------------------------------------------------
# 3. Persistence helpers
# -------------------------------------------------------------------
def store_opening_rebound_score(symbol_id, trade_date, score):
    conn = connect_to_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO pattern_scores (symbolId, date, opening_rebound_score)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE opening_rebound_score = VALUES(opening_rebound_score)
                """,
                (symbol_id, trade_date, score),
            )
        conn.commit()
    finally:
        conn.close()

def calculate_ema(symbol_id):
    conn = connect_to_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT opening_rebound_score
                FROM pattern_scores
                WHERE symbolId = %s
                ORDER BY date DESC
                LIMIT %s
                """,
                (symbol_id, EMA_PERIOD_DAYS),
            )
            scores = [row["opening_rebound_score"] for row in cur.fetchall()]
    finally:
        conn.close()

    if not scores:
        return None

    scores.reverse()                      # chronological order
    ema = scores[0]
    multiplier = 2 / (len(scores) + 1)
    for s in scores[1:]:
        ema = (s - ema) * multiplier + ema
    return round(ema, 2)

def store_ema(symbol_id, ema):
    conn = connect_to_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ema_scores (symbolId, ema_score, last_updated)
                VALUES (%s, %s, NOW())
                ON DUPLICATE KEY UPDATE
                    ema_score = VALUES(ema_score),
                    last_updated = NOW()
                """,
                (symbol_id, ema),
            )
        conn.commit()
    finally:
        conn.close()

# -------------------------------------------------------------------
# 4. Main driver: iterate securities & days
# -------------------------------------------------------------------
def main():
    conn = connect_to_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT symbolId FROM candlestick_data")
            securities = [row["symbolId"] for row in cur.fetchall()]

            for symbol_id in securities:
                print(f"▶ {symbol_id}")

                # identify min/max available dates
                cur.execute(
                    """
                    SELECT MAX(DATE(start)) AS max_d, MIN(DATE(start)) AS min_d
                    FROM candlestick_data
                    WHERE symbolId = %s
                    """,
                    (symbol_id,),
                )
                row = cur.fetchone()
                max_date, min_date = row["max_d"], row["min_d"]
                if not max_date:
                    continue

                # last score date
                cur.execute(
                    """
                    SELECT MAX(date) AS last_d
                    FROM pattern_scores
                    WHERE symbolId = %s
                    """,
                    (symbol_id,),
                )
                last_d = cur.fetchone()["last_d"]
                work_date = (last_d + timedelta(days=1)) if last_d else min_date

                while work_date and work_date <= max_date:
                    if work_date.weekday() == 0:           # Monday
                        work_date += timedelta(days=1)
                        continue
                    cur.execute(
                        "SELECT 1 FROM market_holidays WHERE holiday_date=%s",
                        (work_date,),
                    )
                    if cur.fetchone():
                        work_date += timedelta(days=1)
                        continue

                    candles = get_candlestick_data(symbol_id, work_date)
                    score = calculate_opening_rebound_score(candles)
                    if score is not None:
                        store_opening_rebound_score(symbol_id, work_date, score)
                        print(f"  {work_date}: score {score}")
                    work_date += timedelta(days=1)

                ema = calculate_ema(symbol_id)
                if ema is not None:
                    store_ema(symbol_id, ema)
                    print(f"  EMA‑{EMA_PERIOD_DAYS} = {ema}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
