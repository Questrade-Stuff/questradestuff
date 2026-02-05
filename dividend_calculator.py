from questrade_api import QuestradeAPI
from credentials import MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE
import pymysql
from pymysql.cursors import DictCursor
import os
from datetime import datetime, timedelta

os.system('clear')

# Global variable for Questrade API instance
qt = None

# Function to connect to MySQL database
def connect_to_db():
    return pymysql.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        cursorclass=DictCursor
    )

# Function to fetch and filter active accounts
def get_active_accounts():
    questrade_accounts = qt.accounts()['accounts']
    active_accounts = [account for account in questrade_accounts if account['status'] == 'Active']
    active_accounts.sort(key=lambda x: not x['isPrimary'])
    return active_accounts

# Function to display available accounts
def display_accounts(accounts):
    print("\nAvailable Accounts:")
    for idx, account in enumerate(accounts, start=1):
        print(f"{idx}: {account['type']} ({'Primary' if account['isPrimary'] else 'Secondary'})")

# Function to get user-selected account index
def get_chosen_account_index(accounts):
    chosen_index = input("Choose Account (press Enter to select the primary account): ")
    if chosen_index == "":
        return 0
    else:
        chosen_index = int(chosen_index) - 1
        if 0 <= chosen_index < len(accounts):
            return chosen_index
        else:
            print("Invalid choice.")
            return None

# Function to get dividend frequency from the database
def get_dividend_frequency(symbol):
    connection = connect_to_db()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT frequency FROM div_freq WHERE symbol = %s"
            cursor.execute(sql, (symbol,))
            result = cursor.fetchone()
            if result:
                return result['frequency']
            else:
                return None
    finally:
        connection.close()

# Function to add or update dividend frequency in the database
def add_or_update_dividend_frequency(symbol, frequency):
    connection = connect_to_db()
    try:
        with connection.cursor() as cursor:
            sql = "INSERT INTO div_freq (symbol, frequency) VALUES (%s, %s) ON DUPLICATE KEY UPDATE frequency = %s"
            cursor.execute(sql, (symbol, frequency, frequency))
        connection.commit()
    finally:
        connection.close()

# Function to calculate the expected dividend for a given security
def calculate_expected_dividend(symbol, quantity, dividend, frequency):
    if frequency == 'monthly':
        annual_dividend = dividend * 12
    elif frequency == 'quarterly':
        annual_dividend = dividend * 4
    else:
        annual_dividend = 0
    return annual_dividend * quantity

# Function to display securities and calculate totals
def display_securities_with_totals(account_number):
    positions = qt.positions_acct(account_number)
    securities = []
    six_months_ago = datetime.now() - timedelta(days=180)
    excluded_stocks = []
    total_market_value = 0
    total_annual_dividends = 0

    for position in positions['positions']:
        # Calculate total market value for all positions
        if position['currentMarketValue'] is not None and position['currentMarketValue'] > 0:
            total_market_value += position['currentMarketValue']
        
        # Skip positions with zero quantity or no market value for dividend calculations
        if position['openQuantity'] == 0 or position['currentMarketValue'] is None or position['currentMarketValue'] == 0:
            if position['currentMarketValue'] is None or position['currentMarketValue'] == 0:
                excluded_stocks.append(f"{position.get('symbol', 'Unknown')} was excluded because it had a zero or None balance.")
            continue
        
        symbol_info = qt.get_symbol_info(position['symbolId'])
        if 'symbols' in symbol_info and len(symbol_info['symbols']) > 0:
            symbol = symbol_info['symbols'][0]['symbol']
            name = symbol_info['symbols'][0]['description']
            market_value = position['currentMarketValue']
            quantity = position['openQuantity']
            dividend = symbol_info['symbols'][0].get('dividend', 0)
            ex_date_str = symbol_info['symbols'][0].get('exDate')

            # Check if ex-date is older than 6 months
            ex_date_old = False
            if ex_date_str:
                try:
                    ex_date = datetime.strptime(ex_date_str.split('T')[0], '%Y-%m-%d')
                    if ex_date < six_months_ago:
                        ex_date_old = True
                        excluded_stocks.append(f"{symbol} was excluded because the exDate is older than 6 months.")
                except ValueError:
                    excluded_stocks.append(f"{symbol} was excluded due to invalid ex-date format.")
                    continue

            # Get dividend frequency from the database
            frequency = get_dividend_frequency(symbol)
            if frequency is None:
                # Prompt user for the dividend frequency
                frequency_input = input(f"Frequency for {symbol} (enter 'm' for monthly or 'q' for quarterly): ").strip().lower()
                if frequency_input in ['m', 'q']:
                    frequency = 'monthly' if frequency_input == 'm' else 'quarterly'
                    add_or_update_dividend_frequency(symbol, frequency)
                else:
                    print(f"Invalid input for {symbol}. Skipping...")
                    excluded_stocks.append(f"{symbol} was excluded due to invalid frequency input.")
                    continue
            
            # Skip if ex-date is old
            if ex_date_old:
                continue
            
            expected_dividend = calculate_expected_dividend(symbol, quantity, dividend, frequency)
            
            # Calculate yield
            if market_value > 0:
                yield_percent = (expected_dividend / market_value) * 100
            else:
                yield_percent = 0
            
            securities.append({
                'name': name,
                'market_value': market_value,
                'expected_dividend': expected_dividend,
                'yield_percent': yield_percent
            })
            
            total_annual_dividends += expected_dividend

    # Sort securities by yield percentage (highest to lowest)
    securities.sort(key=lambda x: x['yield_percent'], reverse=True)

    # Calculate the length of the longest security name
    max_name_length = max(len(security['name']) for security in securities) if securities else 20
    max_name_length = max(max_name_length, len("Name of Security")) + 3

    # Display formatted securities
    print(f"\nDividend-Bearing Securities in Account {account_number}:\n")
    print(f"{'Name of Security'.ljust(max_name_length)} {'Market Value':>15} {'Expected Dividend':>20} {'Yield (%)':>10}")
    print("-" * (max_name_length + 50))
    
    for security in securities:
        name = security['name'].ljust(max_name_length)
        market_value = f"${security['market_value']:,.2f}"
        expected_dividend = f"${security['expected_dividend']:,.2f}"
        yield_percent = f"{security['yield_percent']:.2f}%"
        print(f"{name} {market_value:>15} {expected_dividend:>20} {yield_percent:>10}")
    
    # Display summary
    print("=" * (max_name_length + 50))
    total_monthly_dividends = total_annual_dividends / 12
    
    print(f"\n{'Total Current Market Value:':<40} ${total_market_value:,.2f}")
    print(f"{'Total Monthly Dividends:':<40} ${total_monthly_dividends:,.2f}")
    
    if total_market_value > 0:
        total_yield = (total_annual_dividends / total_market_value) * 100
        print(f"{'Total Portfolio Yield:':<40} {total_yield:.2f}%")
    else:
        print("Total Current Market Value is zero, unable to calculate yield.")
    
    # Print excluded stocks
    if excluded_stocks:
        print("\n--- Excluded Stocks ---")
        for excluded_stock in excluded_stocks:
            print(excluded_stock)

# Main script logic
def main():
    global qt
    
    # Initialize Questrade API - this will prompt for user selection
    qt = QuestradeAPI()
    
    active_accounts = get_active_accounts()
    display_accounts(active_accounts)
    chosen_index = get_chosen_account_index(active_accounts)

    if chosen_index is not None:
        chosen_account = active_accounts[chosen_index]
        print(f"\nYou chose: {chosen_account['type']} account with number {chosen_account['number']}")
        
        # Display securities with summary
        display_securities_with_totals(chosen_account['number'])

if __name__ == "__main__":
    main()