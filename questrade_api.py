#questrade_api.py
import requests
import time
from datetime import datetime, timedelta
from credentials import MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE
import json
import logging
import pymysql
from pymysql.cursors import DictCursor
import os


class QuestradeAPI:
    def __init__(self, user_id=None):
        """
        Initialize the Questrade API with optional user_id.
        If user_id is None, will prompt for user selection.
        """
        # Connect to the database
        self.db = pymysql.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE,
            cursorclass=DictCursor
        )

        self.cursor = self.db.cursor()
        self.user_id = user_id
        self.access_token = None
        self.refresh_token = None
        self.expires_at = None
        self.api_server = None
        
        # If no user_id provided, prompt for selection
        if self.user_id is None:
            self.user_id = self.select_user()
        
        self.load_tokens()

        # If tokens are not loaded or expired, get initial tokens
        if not self.access_token or not self.refresh_token or not self.expires_at:
            self.get_initial_tokens()

    def select_user(self):
        """Prompt user to select which Questrade account owner."""
        self.cursor.execute("SELECT id, username, display_name, is_default FROM qt_users ORDER BY is_default DESC")
        users = self.cursor.fetchall()
        
        if not users:
            raise Exception("No users found in qt_users table. Please add users first.")
        
        print("\nAvailable Users:")
        for user in users:
            default_marker = " (default)" if user['is_default'] else ""
            print(f"{user['id']}: {user['display_name']}{default_marker}")
        
        user_choice = input("\nSelect user (press Enter for default): ").strip()
        
        if user_choice == "":
            # Return the default user
            default_user = next((u for u in users if u['is_default']), users[0])
            return default_user['id']
        else:
            try:
                chosen_id = int(user_choice)
                if any(u['id'] == chosen_id for u in users):
                    return chosen_id
                else:
                    print("Invalid user ID. Using default.")
                    default_user = next((u for u in users if u['is_default']), users[0])
                    return default_user['id']
            except ValueError:
                print("Invalid input. Using default.")
                default_user = next((u for u in users if u['is_default']), users[0])
                return default_user['id']

    def get_account_number(self, account_type):
        """Fetch the account number for the given account type and current user."""
        self.cursor.execute(
            "SELECT account_number FROM qt_accounts WHERE account_type = %s AND user_id = %s", 
            (account_type, self.user_id)
        )
        result = self.cursor.fetchone()
        if result:
            return result['account_number']
        else:
            raise ValueError(f"Account type '{account_type}' not found for user_id {self.user_id} in the database.")

    def load_tokens(self):
        """Load the tokens and API server URL from the database for the current user."""
        self.cursor.execute("SELECT * FROM qt_oauth WHERE user_id = %s", (self.user_id,))
        token_data = self.cursor.fetchone()
        if token_data:
            self.access_token = token_data['access_token']
            self.refresh_token = token_data['refresh_token']
            self.expires_at = token_data['expires_at']
            self.api_server = token_data['api_server']
        else:
            self.access_token = None
            self.refresh_token = None
            self.expires_at = None
            self.api_server = None

    def save_tokens(self, access_token, refresh_token, expires_in, api_server):
        """Save or update the tokens and API server URL in the database for the current user."""
        expires_at = datetime.now() + timedelta(seconds=expires_in)
        
        # Check if there's already a row for this user
        self.cursor.execute("SELECT COUNT(*) as count FROM qt_oauth WHERE user_id = %s", (self.user_id,))
        count = self.cursor.fetchone()['count']

        if count > 0:
            # Update the existing row
            self.cursor.execute(
                "UPDATE qt_oauth SET access_token = %s, refresh_token = %s, expires_at = %s, api_server = %s WHERE user_id = %s",
                (access_token, refresh_token, expires_at, api_server, self.user_id)
            )
        else:
            # Insert a new row if none exist
            self.cursor.execute(
                "INSERT INTO qt_oauth (user_id, access_token, refresh_token, expires_at, api_server) VALUES (%s, %s, %s, %s, %s)",
                (self.user_id, access_token, refresh_token, expires_at, api_server)
            )
        
        self.db.commit()
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires_at = expires_at
        self.api_server = api_server

    def get_initial_tokens(self):
        """Prompt the user for an authorization code and exchange it for initial tokens."""
        self.cursor.execute("SELECT display_name FROM qt_users WHERE id = %s", (self.user_id,))
        user = self.cursor.fetchone()
        user_name = user['display_name'] if user else f"User {self.user_id}"
        
        auth_code = input(f"Enter the authorization code from Questrade for {user_name}: ")

        token_url = "https://login.questrade.com/oauth2/token?grant_type=refresh_token&refresh_token="

        response = requests.post(token_url + auth_code)

        print("Response Status Code:", response.status_code)
        print("Response Text:", response.text)

        if response.status_code == 200:
            token_data = response.json()
            self.save_tokens(
                access_token=token_data['access_token'],
                refresh_token=token_data['refresh_token'],
                expires_in=token_data['expires_in'],
                api_server=token_data['api_server']
            )
            print(f"Tokens successfully obtained and saved for {user_name}.")
        else:
            raise Exception("Failed to obtain tokens. Please check the authorization code and try again.")

    def refresh_access_token(self):
        """Refresh the access token using the refresh token. If refresh fails, prompt for new token."""
        refresh_url = "https://login.questrade.com/oauth2/token"
        params = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
        }
        response = requests.post(refresh_url, params=params)

        if response.status_code == 200:
            token_data = response.json()
            self.save_tokens(
                access_token=token_data['access_token'],
                refresh_token=token_data.get('refresh_token', self.refresh_token),
                expires_in=token_data['expires_in'],
                api_server=token_data['api_server']
            )
        else:
            # Refresh token has expired - prompt for new authorization code
            print("\n⚠️  Refresh token has expired or is invalid.")
            print(f"Response Status Code: {response.status_code}")
            print(f"Response Text: {response.text}")
            
            # Get user name for the prompt
            self.cursor.execute("SELECT display_name FROM qt_users WHERE id = %s", (self.user_id,))
            user = self.cursor.fetchone()
            user_name = user['display_name'] if user else f"User {self.user_id}"
            
            # Prompt for new authorization code
            auth_code = input(f"\nEnter a NEW authorization code from Questrade for {user_name}: ")
            
            token_url = "https://login.questrade.com/oauth2/token?grant_type=refresh_token&refresh_token="
            new_response = requests.post(token_url + auth_code)
            
            if new_response.status_code == 200:
                token_data = new_response.json()
                self.save_tokens(
                    access_token=token_data['access_token'],
                    refresh_token=token_data['refresh_token'],
                    expires_in=token_data['expires_in'],
                    api_server=token_data['api_server']
                )
                print(f"✓ New tokens successfully obtained and saved for {user_name}.")
            else:
                print(f"\nFailed to obtain new tokens.")
                print(f"Response Status Code: {new_response.status_code}")
                print(f"Response Text: {new_response.text}")
                raise Exception("Failed to refresh access token. Please check your credentials.")

    def make_request(self, endpoint):
        """Make a request to the Questrade API."""
        # RELOAD tokens from database before checking expiry
        self.load_tokens()
        
        # If the token is expired, refresh it before making the request
        if not self.expires_at or datetime.now() >= self.expires_at:
            self.refresh_access_token()

        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }

        response = requests.get(f"{self.api_server}/{endpoint}", headers=headers)
        
        # If the access token is invalid, force a token refresh and retry the request
        if response.status_code == 401 and response.json().get("code") == 1017:
            print("Access token is invalid. Attempting to refresh...")
            self.refresh_access_token()
            headers["Authorization"] = f"Bearer {self.access_token}"
            response = requests.get(f"{self.api_server}/{endpoint}", headers=headers)

        if response.text.strip():
            return response.json()
        else:
            raise ValueError("Received an empty response or a non-JSON response from the server.")

    def time_api_call(self, api_function, *args, **kwargs):
        """
        Measure the elapsed time for an API call.
            response, elapsed_time = qt.time_api_call(qt.time)
            print("API Response:", response)
        :param api_function: The API function to call (e.g., self.time).
        :param args: Arguments to pass to the API function.
        :param kwargs: Keyword arguments to pass to the API function.
        :return: A tuple containing the API response and the elapsed time in seconds.
        """
        start_time = time.time()
        response = api_function(*args, **kwargs)
        end_time = time.time()
        
        elapsed_time = end_time - start_time
        print(f"Elapsed time: {elapsed_time:.4f} seconds")

        return response, elapsed_time

    def activities(self, account_type, start_time, end_time):
        """Fetch activities for a given account type within a specified time range."""
        account_id = self.get_account_number(account_type)
        endpoint = f"v1/accounts/{account_id}/activities?startTime={start_time}&endTime={end_time}"
        response = self.make_request(endpoint)
        return response

    def account_balance(self, account_type):
        """Get account balances for the account associated with the given account type."""
        account_number = self.get_account_number(account_type)
        response = self.make_request(f"v1/accounts/{account_number}/balances")
        return response
    
    def time(self):
        """Fetch the current time from the Questrade API."""
        endpoint = "v1/time"
        response = self.make_request(endpoint)
        return response

    def _acquire_oauth_lock(self, timeout=20):
        lock_name = f"qt_oauth_refresh_user_{self.user_id}"
        self.cursor.execute("SELECT GET_LOCK(%s, %s) AS got", (lock_name, timeout))
        return lock_name, self.cursor.fetchone()['got'] == 1

    def _release_oauth_lock(self, lock_name):
        self.cursor.execute("SELECT RELEASE_LOCK(%s) AS rel", (lock_name,))
        self.cursor.fetchone()


    def orders(self, account_type, state_filter=None, order_id=None):
        """
        Fetch orders for the given account type with optional filters.       
        :param account_type: The type of the account (e.g., "TFSA", "MARGIN").
        :param state_filter: Optional. A string to filter orders by state (e.g., "Filled", "Canceled").
        :param order_id: Optional. A specific order ID to retrieve.
        :return: The JSON response from the Questrade API.
        """
        account_number = self.get_account_number(account_type)
        endpoint = f"v1/accounts/{account_number}/orders"
        params = {}

        if state_filter:
            params['stateFilter'] = state_filter
        if order_id:
            endpoint += f"/{order_id}"

        response = self.make_request(endpoint)
        return response

    def positions(self, account_type):
        """Retrieves positions in a specified account."""
        account_number = self.get_account_number(account_type)
        response = self.make_request(f"v1/accounts/{account_number}/positions")
        return response
    
    def positions_acct(self, account_number):
        """Retrieves positions in a specified account."""
        response = self.make_request(f"v1/accounts/{account_number}/positions")
        return response
    
    def accounts(self):
        """Retrieves the accounts associated with the user on behalf of which the API client is authorized."""        
        response = self.make_request(f"v1/accounts")
        return response
    
    def get_candles(self, symbol_id, start_time=None, end_time=None, interval="OneDay"):
        """
        Fetch candlestick data for a given symbol.
        :param symbol_id: The ID of the symbol to fetch candles for.
        :param start_time: Optional. The start time for the data range (ISO 8601 format).
        :param end_time: Optional. The end time for the data range (ISO 8601 format).
        :param interval: Optional. The interval of the candles (default is "OneDay").
        :return: The JSON response from the Questrade API.
        """
        endpoint = f"v1/markets/candles/{symbol_id}"
        params = {"interval": interval}

        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time

        response = self.make_request(f"{endpoint}?{requests.compat.urlencode(params)}")
        return response
    
    def get_quote(self, symbol_id):
        """
        Fetch real-time market quotes for a given symbol.
        :param symbol_id: The ID of the symbol to fetch the quote for.
        :return: The JSON response from the Questrade API.
        """
        endpoint = f"v1/markets/quotes/{symbol_id}"
        response = self.make_request(endpoint)
        return response
    
    def search_symbols(self, prefix):
        """
        Search for symbols using a keyword or prefix.
        :param prefix: The search keyword or prefix to find matching symbols.
        :return: The JSON response from the Questrade API.
        """
        endpoint = f"v1/symbols/search?prefix={prefix}"
        response = self.make_request(endpoint)
        return response
    
    def get_symbol_info(self, symbol_id):
        """
        Fetch detailed information for a given symbol.
        :param symbol_id: The ID of the symbol to fetch information for.
        :return: The JSON response from the Questrade API.
        """
        endpoint = f"v1/symbols/{symbol_id}"
        response = self.make_request(endpoint)
        return response
    
    def get_security_data(self, symbol_id, retries=3):
        for attempt in range(retries):
            try:
                quote_data = self.get_quote(symbol_id).get('quotes', [{}])[0]
                symbol_info = self.get_symbol_info(symbol_id).get('symbols', [{}])[0]

                symbol_info_filtered = {
                    'symbol': symbol_info.get('symbol'),
                    'symbolId': symbol_info.get('symbolId'),
                    'tier': symbol_info.get('tier'),
                    'listingExchange': symbol_info.get('listingExchange'),
                    'description': symbol_info.get('description'),
                    'securityType': symbol_info.get('securityType'),
                    'currency': symbol_info.get('currency'),
                    'prevDayClosePrice': symbol_info.get('prevDayClosePrice'),
                    'highPrice52': symbol_info.get('highPrice52'),
                    'lowPrice52': symbol_info.get('lowPrice52'),
                    'averageVol3Months': symbol_info.get('averageVol3Months'),
                    'averageVol20Days': symbol_info.get('averageVol20Days'),
                    'outstandingShares': symbol_info.get('outstandingShares'),
                    'eps': symbol_info.get('eps'),
                    'pe': symbol_info.get('pe'),
                    'dividend': symbol_info.get('dividend'),
                    'yield': symbol_info.get('yield'),
                    'exDate': symbol_info.get('exDate'),
                    'marketCap': symbol_info.get('marketCap'),
                    'tradeUnit': symbol_info.get('tradeUnit'),
                    'dividendDate': symbol_info.get('dividendDate'),
                    'isTradable': symbol_info.get('isTradable'),
                    'isQuotable': symbol_info.get('isQuotable')
                }

                quote_data_filtered = {
                    'bidPrice': quote_data.get('bidPrice'),
                    'bidSize': quote_data.get('bidSize'),
                    'askPrice': quote_data.get('askPrice'),
                    'askSize': quote_data.get('askSize'),
                    'lastTradePriceTrHrs': quote_data.get('lastTradePriceTrHrs'),
                    'lastTradePrice': quote_data.get('lastTradePrice'),
                    'lastTradeSize': quote_data.get('lastTradeSize'),
                    'lastTradeTick': quote_data.get('lastTradeTick'),
                    'lastTradeTime': quote_data.get('lastTradeTime'),
                    'volume': quote_data.get('volume'),
                    'openPrice': quote_data.get('openPrice'),
                    'highPrice': quote_data.get('highPrice'),
                    'lowPrice': quote_data.get('lowPrice'),
                    'delay': quote_data.get('delay'),
                    'isHalted': quote_data.get('isHalted'),
                    'high52w': quote_data.get('high52w'),
                    'low52w': quote_data.get('low52w'),
                    'VWAP': quote_data.get('VWAP')
                }

                merged_data = {**quote_data_filtered, **symbol_info_filtered}

                def convert_none_to_null(data):
                    if isinstance(data, dict):
                        return {
                            key: 'NULL' if value is None else value
                            for key, value in data.items()
                        }
                    elif isinstance(data, list):
                        return [convert_none_to_null(item) for item in data]
                    elif data is None:
                        return 'NULL'
                    else:
                        return data

                merged_data = convert_none_to_null(merged_data)
                return merged_data

            except Exception as e:
                print(f"Error fetching data for symbol ID {symbol_id}: {e}")
                if attempt < retries - 1:
                    wait_time = (attempt + 1) * 60
                    print(f"Retrying in {wait_time // 60} minute(s)...")
                    time.sleep(wait_time)
                else:
                    print(f"Failed after {retries} attempts. Halting.")
                    raise e

    def is_market_open(self, date):
        """Check if the market is open on the given date."""
        cursor = self.db.cursor()

        if date.weekday() >= 5:  # 5 is Saturday, 6 is Sunday
            cursor.close()
            return False

        cursor.execute("SELECT COUNT(*) FROM market_holidays WHERE holiday_date = %s", (date.strftime('%Y-%m-%d'),))
        is_holiday = cursor.fetchone()[0] > 0
        cursor.close()

        return not is_holiday

    def resume_progress(self, script_name, operation, pattern=None, security_id=None, progress=None):
        """
        Handle saving, loading, or deleting progress in the resume_info table.
        
        :param script_name: Name of the script (e.g., 'fetch_securities', 'update_qt_securities', 'candlestick_update').
        :param operation: Operation type ('load', 'save', or 'delete').
        :param pattern: Optional pattern to save (used in 'fetch_securities').
        :param security_id: Optional security ID to save (used in 'update_qt_securities' and 'candlestick_update').
        :param progress: Optional progress to save (used in 'candlestick_update').
        :return: If operation is 'load', returns the last processed pattern or security ID.
        """
        try:
            if operation == 'save':
                if script_name == 'AlphaSweep':
                    self.cursor.execute("""
                        INSERT INTO resume_info (script_name, last_processed_pattern, last_processed_date)
                        VALUES (%s, %s, NOW())
                        ON DUPLICATE KEY UPDATE 
                            last_processed_pattern = VALUES(last_processed_pattern), 
                            last_processed_date = NOW()
                    """, (script_name, pattern))

                elif script_name in ['update_qt_securities', 'candlestick_update']:
                    additional_info = json.dumps({'progress': progress}) if progress is not None else None
                    self.cursor.execute("""
                        INSERT INTO resume_info (script_name, last_processed_security_id, last_processed_date, additional_info)
                        VALUES (%s, %s, NOW(), %s)
                        ON DUPLICATE KEY UPDATE
                            last_processed_security_id = VALUES(last_processed_security_id),
                            last_processed_date = NOW(),
                            additional_info = VALUES(additional_info)
                    """, (script_name, security_id, additional_info))

                self.db.commit()
                logging.info(f"Progress saved for {script_name}. Security ID: {security_id}, Progress: {progress}")
            
            elif operation == 'load':
                self.cursor.execute("SELECT * FROM resume_info WHERE script_name = %s ORDER BY id DESC LIMIT 1", (script_name,))
                result = self.cursor.fetchone()
                if result:
                    logging.info(f"Progress loaded for {script_name}. Result: {result}")
                else:
                    logging.warning(f"No progress found for {script_name}.")
                
                if script_name == 'AlphaSweep':
                    return result['last_processed_pattern'] if result else None

                elif script_name in ['update_qt_securities', 'candlestick_update']:
                    if result and result.get('additional_info'):
                        result['additional_info'] = json.loads(result['additional_info'])
                    return result

            elif operation == 'delete':
                self.cursor.execute("DELETE FROM resume_info WHERE script_name = %s", (script_name,))
                self.db.commit()
                logging.info(f"Progress deleted for {script_name}.")

        except Exception as e:
            logging.error(f"Error in resume_progress for {script_name} ({operation}): {e}")
            self.db.rollback()
            raise