# This script sequentially sweeps Questrade for new securities
# The script will remember where it left off using the resume_info table
# The script will perform a first pass filter, only securities traded in CAD and are a Stock
# Valid securities will be added to the table qt_securities

from questrade_api import QuestradeAPI
from credentials import MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE
import pymysql.cursors
import itertools
import urllib.error
import time

# Initialize Questrade API with hardcoded user_id for automated/cron execution
# user_id=1 means this will always run as xx without prompting
qt = QuestradeAPI(user_id=1)

# MySQL database connection setup
db_config = {
    'host': MYSQL_HOST,
    'user': MYSQL_USER,
    'password': MYSQL_PASSWORD,
    'database': MYSQL_DATABASE,
    'cursorclass': pymysql.cursors.DictCursor
}
try:
    # Connect to MySQL database
    db_connection = pymysql.connect(**db_config)
    with db_connection.cursor() as cursor:
        print("Connected to the database.")

        # Fetch the last processed pattern for AlphaSweep from resume_info
        last_pattern = qt.resume_progress('AlphaSweep', 'load')
        print(f"Resuming from pattern: {last_pattern}")

        # Define the patterns
        patterns = [
            'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 
            'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z',
            '0', '1', '2', '3', '4', '5', '6', '7', '8', '9'
        ]

        # Extend patterns to include common two-letter and three-letter combinations
        letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        two_letter_combinations = [''.join(pair) for pair in itertools.product(letters, repeat=2)]
        three_letter_combinations = [''.join(triplet) for triplet in itertools.product(letters, repeat=3)]
        patterns.extend(two_letter_combinations)
        patterns.extend(three_letter_combinations)

        # Determine the starting index based on the last processed pattern
        start_index = 0
        if last_pattern:
            start_index = patterns.index(last_pattern) + 1

        # Process each pattern. If the loop completes successfully, the else block will clear the progress.
        for pattern in patterns[start_index:]:
            print(f"Fetching securities for pattern: {pattern}")
            retry_count = 0
            max_retries = 5

            while retry_count < max_retries:
                # Optional delay if needed
                if max_retries > 3:
                    qt.time()
                try:
                    search_results = qt.search_symbols(pattern)
                    for security in search_results.get('symbols', []):
                        if (security['currency'] == 'CAD' and 
                            security['securityType'] == 'Stock' and 
                            security['isTradable'] == True and 
                            security['isQuotable'] == True):
                            symbolId = security['symbolId']
                            symbol = security['symbol']
                            description = security['description']
                            print(f"Matched tradable and quotable security in CAD: {symbolId}, {symbol}, {description}")

                            # Insert or update the security in the database
                            cursor.execute("""
                                INSERT INTO qt_securities (symbolId, symbol, description)
                                VALUES (%s, %s, %s)
                                ON DUPLICATE KEY UPDATE symbol=%s, description=%s
                            """, (symbolId, symbol, description, symbol, description))
                            db_connection.commit()
                    
                    # Successfully processed the current pattern; save progress and break the retry loop
                    qt.resume_progress('AlphaSweep', 'save', pattern=pattern)
                    break

                except urllib.error.URLError as e:
                    retry_count += 1
                    print(f"Network error fetching securities for pattern {pattern}: {e}. Retrying {retry_count}/{max_retries}...")
                    qt.time()
                    time.sleep(5)  # Delay before retrying

                except Exception as e:
                    retry_count += 1
                    if "429" in str(e):
                        print(f"Rate limit hit. Retrying after delay {retry_count}/{max_retries}...")
                        qt.time()
                        time.sleep(60)  # Delay longer if rate limited
                    else:
                        print(f"Error fetching securities for pattern {pattern}: {e}. Retrying {retry_count}/{max_retries}...")
                        qt.time()
                        time.sleep(5)  # Delay before retrying

            if retry_count == max_retries:
                print(f"Failed to fetch securities for pattern {pattern} after {max_retries} attempts. Saving progress and stopping.")
                qt.resume_progress('AlphaSweep', 'save', pattern=pattern)
                break
        else:
            # This block executes if no break occurred in the for loop,
            # meaning all patterns were processed successfully.
            print("All patterns processed successfully. Clearing progress marker.")
            qt.resume_progress('AlphaSweep', 'delete')

    db_connection.close()
    print("Successfully fetched and updated securities.")

except Exception as e:
    print(f'Error fetching securities: {e}')
