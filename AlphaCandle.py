#AlphaCandle.py
import sys
import os
import time
import pymysql
from pymysql.err import MySQLError
from pymysql.cursors import DictCursor
from datetime import datetime, timedelta
from pytz import timezone
from questrade_api import QuestradeAPI
from credentials import MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE

# Initialize Questrade API
qt = QuestradeAPI(user_id=1)

# Database configuration
db_config = {
    'host': MYSQL_HOST,
    'user': MYSQL_USER,
    'password': MYSQL_PASSWORD,
    'database': MYSQL_DATABASE,
    'cursorclass': DictCursor  # Use DictCursor for dictionary results
}

# General helper function to handle MySQL operations
def execute_query(cursor, query, params=None):
    cursor.execute(query, params)
    return cursor.fetchall()

def ensure_connection(cursor):
    """
    Reconnect to the database if the connection is lost.
    """
    try:
        cursor.connection.ping(reconnect=True)
    except MySQLError as err:
        print(f"Error reconnecting to database: {err}")
        raise

def get_existing_data_range(cursor, symbolId):
    """
    Fetch the min and max dates for a given security in the candlestick_data table.
    """
    query = """
        SELECT MIN(start) AS min_date, MAX(start) AS max_date
        FROM candlestick_data
        WHERE symbolID = %s
    """
    cursor.execute(query, (symbolId,))
    result = cursor.fetchone()
    return result['min_date'], result['max_date']

def insert_candlestick_data(connection, cursor, candlestick_data):
    """
    Insert or update candlestick data in the database.
    """
    insert_query = """
        INSERT INTO candlestick_data (
            symbolID, start, end, open, high, low, close, volume, VWAP
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            open = VALUES(open),
            high = VALUES(high),
            low = VALUES(low),
            close = VALUES(close),
            volume = VALUES(volume),
            VWAP = VALUES(VWAP)
    """
    cursor.executemany(insert_query, candlestick_data)
    connection.commit()

def fetch_candles(qt, symbolId, start_iso, end_iso, retries=5):
    """
    Fetch candlestick data from Questrade API with retry logic.
    """
    attempts = 0
    while attempts < retries:
        try:
            candles = qt.get_candles(
                symbolId,
                start_time=start_iso,
                end_time=end_iso,
                interval='OneMinute'
            )
            return candles.get('candles', [])
        except Exception as e:
            attempts += 1
            wait_time = attempts * 30  # Wait longer with each retry
            print(f"Error fetching data: {e}, retrying in {wait_time} seconds...")
            time.sleep(wait_time)
    print(f"Failed to fetch data after {retries} attempts.")
    return None

def delete_old_data(connection, cursor, symbolId, days_to_keep=400):
    """
    Delete candlestick data older than a specified number of days.
    """
    cutoff_date = datetime.now(timezone('UTC')) - timedelta(days=days_to_keep)
    delete_query = """
        DELETE FROM candlestick_data
        WHERE symbolID = %s AND start < %s
    """
    cursor.execute(delete_query, (symbolId, cutoff_date))
    connection.commit()

def process_security_data(cursor, connection, security, start_date, end_date):
    """
    Fetch data for a security between start_date and end_date, skipping weekends and holidays.
    """
    symbolId = security['symbolId']
    eastern = timezone('US/Eastern')
    current_end = end_date
    consecutive_no_data_days = 0
    max_no_data_days = 8

    while current_end >= start_date:
        # Skip weekends
        if current_end.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
            current_end -= timedelta(days=1)
            continue

        # Check if the date is a holiday
        cursor.execute("SELECT COUNT(*) FROM market_holidays WHERE holiday_date = %s", (current_end,))
        if cursor.fetchone()['COUNT(*)'] > 0:
            print(f"Skipping holiday: {current_end}")
            current_end -= timedelta(days=1)
            continue

        # Define market open and close times
        market_open_time = eastern.localize(datetime.combine(current_end, datetime.strptime('09:30', '%H:%M').time()))
        market_close_time = eastern.localize(datetime.combine(current_end, datetime.strptime('16:00', '%H:%M').time()))
        start_iso = market_open_time.isoformat()
        end_iso = market_close_time.isoformat()

        # Debugging line to track data fetching
        print(f"Fetching candles for symbolID {symbolId} from {start_iso} to {end_iso}")

        candle_list = fetch_candles(qt, symbolId, start_iso, end_iso)

        if not candle_list:
            consecutive_no_data_days += 1
            if consecutive_no_data_days >= max_no_data_days:
                print(f"Skipping security {symbolId} after {max_no_data_days} consecutive no-data days.")
                return
        else:
            consecutive_no_data_days = 0
            candlestick_data = [
                (
                    symbolId,
                    candle['start'],
                    candle['end'],
                    candle['open'],
                    candle['high'],
                    candle['low'],
                    candle['close'],
                    candle['volume'],
                    candle.get('VWAP')
                )
                for candle in candle_list
            ]
            insert_candlestick_data(connection, cursor, candlestick_data)

        # Move to the previous day
        current_end -= timedelta(days=1)


def update_candlestick_data():
    """
    Main function to update candlestick data for all tradable securities.
    """
    try:
        connection = pymysql.connect(**db_config)
        cursor = connection.cursor()
        print("Connected to the database.")

        # Fetch all tradable securities
        securities = execute_query(cursor, "SELECT symbolId FROM qt_securities")
        total_securities = len(securities)

        for idx, security in enumerate(securities, start=1):
            symbolId = security['symbolId']
            min_date, max_date = get_existing_data_range(cursor, symbolId)
            start_date = (max_date + timedelta(days=1)).date() if max_date else (datetime.now(timezone('US/Eastern')) - timedelta(days=200)).date()
            end_date = datetime.now(timezone('US/Eastern')).date()

            if start_date <= end_date:
                print(f"\nProcessing security {symbolId} ({idx}/{total_securities})")
                process_security_data(cursor, connection, security, start_date, end_date)

                # Delete old data
                delete_old_data(connection, cursor, symbolId)

        print("\nSuccessfully updated candlestick data for all securities.")

    except MySQLError as e:
        print(f"MySQL error occurred during the update process: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

def is_cron_run():
    """
    Check if the script is run by cron by looking at the LOGNAME variable.
    Adjust this logic if cron on your system uses a different environment variable or value.
    """
    return os.getenv("LOGNAME") is None or os.getenv("LOGNAME") == "root"

if __name__ == "__main__":
    try:
        while True:
            # Check the current time
            current_time = datetime.now().time()
            end_time = datetime.strptime("16:30", "%H:%M").time()  # 4:30 PM

            if current_time >= end_time:
                print(f"Ending script as it's past 4:30 PM (current time: {current_time}).")
                break

            print(f"\n{'='*60}")
            print(f"Starting update cycle at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*60}")
            
            update_candlestick_data()
            
            # Check time again before sleeping to avoid unnecessary wait
            current_time = datetime.now().time()
            if current_time >= end_time:
                print(f"Ending script as it's past 4:30 PM (current time: {current_time}).")
                break
            
            print(f"\nSleeping for 1 hour... (next run at approximately {(datetime.now() + timedelta(hours=1)).strftime('%H:%M:%S')})")
            # Sleep for 1 hour
            time.sleep(3600)
            
    except KeyboardInterrupt:
        print("\nTracking stopped by user.")
    except Exception as e:
        print(f"\nFatal error in main loop: {e}")
        sys.exit(1)
