#!/usr/bin/env python3
"""
daily_ema_scoreboard.py
Show the highest‑EMA tickers after basic liquidity & price filters.
"""

import pymysql
from pymysql.cursors import DictCursor
from questrade_api import QuestradeAPI
from credentials import (
    MYSQL_HOST,
    MYSQL_USER,
    MYSQL_PASSWORD,
    MYSQL_DATABASE,
)

qt = QuestradeAPI(user_id=1)

# ──────────────── connection helper ────────────────
def connect_to_db():
    return pymysql.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        cursorclass=DictCursor,
    )

# ──────────────── parameters (prompt or defaults) ────────────────
def ask(prompt, default, cast):
    try:
        val = input(f"{prompt} [default {default}]: ").strip()
        return cast(val) if val else default
    except Exception:
        return default

MIN_EMA   = ask("Cut‑off EMA score",        20.0,  float)
MIN_PRICE = ask("Minimum last trade price", 0.12,  float)
MIN_VOL   = ask("Minimum 3‑mo avg vol",     5000,  int)
LIMIT     = ask("How many rows to show",    20,    int)

# ──────────────── query & display ────────────────
def fetch_top_ema():
    q = """
        SELECT es.symbolId            AS ID,
               qs.symbol              AS Symbol,
               qs.description         AS Name,
               es.ema_score           AS EMA,
               qs.lastTradePrice      AS Price,
               qs.averageVol3Months   AS AvgVol
        FROM   ema_scores es
        JOIN   qt_securities qs USING (symbolId)
        WHERE  es.ema_score      >= %s
          AND  qs.lastTradePrice >= %s
          AND  qs.averageVol3Months >= %s
        ORDER  BY es.ema_score DESC
        LIMIT  %s
    """
    conn = connect_to_db()
    try:
        with conn.cursor() as cur:
            cur.execute(q, (MIN_EMA, MIN_PRICE, MIN_VOL, LIMIT))
            return cur.fetchall()
    finally:
        conn.close()

def main():
    rows = fetch_top_ema()
    if not rows:
        print("No securities met the criteria.")
        return

    print(
        f"\nTop EMA winners (≥{MIN_EMA}, price ≥{MIN_PRICE}, vol ≥{MIN_VOL})\n"
        f"{'ID':<10}{'Symbol':<8}{'Name':<38}{'EMA':>7}{'Price':>10}{'AvgVol':>12}"
    )
    print("-" * 85)
    for r in rows:
        print(
            f"{r['ID']:<10}{r['Symbol']:<8}"
            f"{r['Name'][:37]:<38}"
            f"{r['EMA']:>7.2f}{r['Price']:>10.2f}{r['AvgVol']:>12,d}"
        )

if __name__ == "__main__":
    main()
