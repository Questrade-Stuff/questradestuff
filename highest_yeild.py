import pymysql
from pymysql.cursors import DictCursor
from questrade_api import QuestradeAPI
from credentials import MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Initialize Questrade API
qt = QuestradeAPI()

# Configuration - set to True to use automatic web scraping, False for manual entry
AUTO_FETCH_FREQUENCY = True  # Change this to switch between modes

# Connect to the MySQL database
def connect_to_db():
    return pymysql.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        cursorclass=DictCursor
    )

# Fetch all active accounts from Questrade
def get_active_accounts():
    questrade_accounts = qt.accounts()['accounts']
    active_accounts = [account for account in questrade_accounts if account['status'] == 'Active']
    active_accounts.sort(key=lambda x: not x['isPrimary'])
    return active_accounts

# Display available accounts for selection
def display_accounts(accounts):
    print("Available Accounts:")
    for idx, account in enumerate(accounts, start=1):
        print(f"{idx}: {account['type']} ({'Primary' if account['isPrimary'] else 'Secondary'})")

# Get user's selected account index
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

# Get number of securities to display
def get_number_of_securities():
    num_input = input("How many securities to display? (press Enter for default 5): ").strip()
    if num_input == "":
        return 5
    try:
        num = int(num_input)
        if num > 0:
            return num
        else:
            print("Invalid number. Using default of 5.")
            return 5
    except ValueError:
        print("Invalid input. Using default of 5.")
        return 5

# Fetch the top 100 highest yielding securities from the database
def get_top_yielding_securities():
    connection = connect_to_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM qt_securities
                WHERE yield IS NOT NULL AND yield > 0 AND exDate IS NOT NULL AND exDate > %s
                ORDER BY yield DESC
                LIMIT 100
            """, ((datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d %H:%M:%S'),))
            return cursor.fetchall()
    finally:
        connection.close()

# Get current positions held in the specified account
def get_current_holdings(account_number):
    positions = qt.positions_acct(account_number)
    return {position['symbolId'] for position in positions['positions'] if position['openQuantity'] > 0}

# Get dividend frequency from the database
def get_dividend_frequency(symbol):
    connection = connect_to_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT frequency FROM div_freq WHERE symbol = %s", (symbol,))
            result = cursor.fetchone()
            return result['frequency'] if result else None
    finally:
        connection.close()

# Update dividend frequency in the database
def add_or_update_dividend_frequency(symbol, frequency):
    connection = connect_to_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO div_freq (symbol, frequency) VALUES (%s, %s) ON DUPLICATE KEY UPDATE frequency = %s",
                (symbol, frequency, frequency)
            )
        connection.commit()
    finally:
        connection.close()

# Display all stored dividend frequencies
def display_all_frequencies():
    connection = connect_to_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT symbol, frequency FROM div_freq ORDER BY symbol")
            results = cursor.fetchall()
            
            if not results:
                print("\nNo dividend frequencies stored in the database.")
                return
            
            print("\n" + "="*60)
            print("Stored Dividend Frequencies")
            print("="*60)
            for idx, row in enumerate(results, start=1):
                print(f"{idx}: {row['symbol']:<15} - {row['frequency']}")
            print("="*60)
            
            # Ask if user wants to edit
            edit_choice = input("\nEnter the number to edit a frequency, or press Enter to return: ").strip()
            
            if edit_choice.isdigit():
                idx = int(edit_choice) - 1
                if 0 <= idx < len(results):
                    symbol = results[idx]['symbol']
                    current_freq = results[idx]['frequency']
                    print(f"\nEditing {symbol} (current: {current_freq})")
                    new_freq = input("Enter new frequency (m=monthly, q=quarterly, or type full name): ").strip().lower()
                    
                    if new_freq == 'm':
                        new_freq = 'monthly'
                    elif new_freq == 'q':
                        new_freq = 'quarterly'
                    elif new_freq not in ['monthly', 'quarterly', 'semi-annually', 'annually']:
                        print("Invalid frequency. No changes made.")
                        return
                    
                    add_or_update_dividend_frequency(symbol, new_freq)
                    print(f"Updated {symbol} to {new_freq}")
                else:
                    print("Invalid selection.")
            
    finally:
        connection.close()

# Fetch distribution frequency from TMX using Playwright
def fetch_distribution_from_tmx(symbol, browser):
    url = f"https://money.tmx.com/en/quote/{symbol}/key-data"
    
    try:
        page = browser.new_page()
        page.goto(url, wait_until='networkidle', timeout=20000)
        
        # Wait a bit for dynamic content to load
        page.wait_for_timeout(2000)
        
        # Try multiple possible selectors
        selectors = [
            '.Item__Desc-sc-sgueh0-4',
            '[class*="Item__Desc"]',
            'div[class*="Desc"]'
        ]
        
        for selector in selectors:
            try:
                items = page.locator(selector).all()
                if items:
                    for item in items:
                        text = item.text_content().strip()
                        if text in ["Monthly", "Quarterly", "Annually", "Semi-Annually"]:
                            page.close()
                            return text.lower()
            except:
                continue
        
        # If selectors don't work, try getting all text and searching
        page_content = page.content()
        text_lower = page_content.lower()
        
        if 'monthly' in text_lower and 'distribution' in text_lower:
            page.close()
            return 'monthly'
        elif 'quarterly' in text_lower and 'distribution' in text_lower:
            page.close()
            return 'quarterly'
        elif 'annually' in text_lower and 'distribution' in text_lower:
            page.close()
            return 'annually'
        
        page.close()
        return None
        
    except PlaywrightTimeoutError:
        print(f"[Timeout: {symbol}] Could not load page in time")
        if 'page' in locals():
            page.close()
        return None
    except Exception as e:
        print(f"[Error: {symbol}] {e}")
        if 'page' in locals():
            page.close()
        return None

# Manually prompt user for dividend frequency
def prompt_for_frequency(symbol):
    frequency_input = input(f"Frequency for {symbol} (enter 'm' for monthly or 'q' for quarterly): ").strip().lower()
    if frequency_input == 'm':
        return 'monthly'
    elif frequency_input == 'q':
        return 'quarterly'
    else:
        print(f"Invalid input for {symbol}. Skipping...")
        return None

# Verify if a security pays monthly dividends
def verify_dividend_frequency(security, browser=None):
    symbol = security['symbol']
    frequency = get_dividend_frequency(symbol)

    if frequency is None:
        if AUTO_FETCH_FREQUENCY and browser is not None:
            print(f"Fetching distribution frequency for {symbol}...")
            dist = fetch_distribution_from_tmx(symbol, browser)

            if dist is None:
                print(f"Unable to fetch distribution frequency for {symbol}.")
                # Fall back to manual entry
                dist = prompt_for_frequency(symbol)
                if dist is None:
                    return None

            if dist in ['monthly', 'quarterly', 'semi-annually', 'annually']:
                add_or_update_dividend_frequency(symbol, dist)
                frequency = dist
            else:
                print(f"Unrecognized frequency '{dist}' for {symbol}. Skipping...")
                return None
        else:
            # Manual entry mode
            frequency = prompt_for_frequency(symbol)
            if frequency is None:
                return None
            add_or_update_dividend_frequency(symbol, frequency)

    return frequency == 'monthly'

# Main function to find the top N monthly dividend payers to consider for purchase
def find_top_dividend_payers():
    active_accounts = get_active_accounts()
    display_accounts(active_accounts)
    chosen_index = get_chosen_account_index(active_accounts)

    if chosen_index is None:
        return

    chosen_account = active_accounts[chosen_index]
    account_number = chosen_account['number']
    print(f"\nYou chose: {chosen_account['type']} account with number {account_number}")

    # Get number of securities to display
    num_securities = get_number_of_securities()

    current_holdings = get_current_holdings(account_number)
    top_securities = get_top_yielding_securities()

    verified_monthly_securities = []
    
    # Initialize Playwright browser if AUTO_FETCH is enabled
    browser = None
    playwright = None
    
    try:
        if AUTO_FETCH_FREQUENCY:
            playwright = sync_playwright().start()
            browser = playwright.chromium.launch(headless=True)
            print("Browser initialized for automatic fetching...")

        for security in top_securities:
            if security['symbolId'] in current_holdings:
                continue

            if verify_dividend_frequency(security, browser):
                verified_monthly_securities.append(security)

            if len(verified_monthly_securities) >= num_securities:
                break

    finally:
        # Clean up Playwright resources
        if browser:
            browser.close()
        if playwright:
            playwright.stop()

    if verified_monthly_securities:
        print(f"\nTop {num_securities} Highest Yielding Monthly Dividend Payers:")
        for idx, security in enumerate(verified_monthly_securities[:num_securities], start=1):
            print(f"{idx}: {security['symbol']} - Yield: {security['yield']}% - Expected Monthly Dividend: ${security['dividend']:.2f}")
    else:
        print("\nNo suitable monthly dividend payers found.")

# Main menu loop
def main():
    while True:
        print("\n" + "="*60)
        print("What would you like to do?")
        print("="*60)
        print("Press Enter - Run dividend picker")
        print("d - Display/Edit stored dividend frequencies")
        print("e or x - Exit")
        print("="*60)
        
        choice = input("Your choice: ").strip().lower()
        
        if choice == "":
            # Run the dividend picker
            find_top_dividend_payers()
        elif choice == "d":
            # Display and optionally edit frequencies
            display_all_frequencies()
        elif choice in ["e", "x"]:
            print("\nExiting... Goodbye!")
            break
        else:
            print("\nInvalid choice. Please try again.")

if __name__ == "__main__":
    main()