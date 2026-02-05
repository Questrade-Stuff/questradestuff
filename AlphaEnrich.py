# This script will cycle through each security in the qt_securities table
# The script will remember where it left off using the resume_info table
# There are 2 API calls that together provide the full datapackage for each security

from questrade_api import QuestradeAPI
from credentials import MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE
import pymysql.cursors

# Initialize Questrade API
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

        # Fetch where the script left off
        last_processed_security = qt.resume_progress('update_qt_securities', 'load')
        if last_processed_security:
            print(f"Resuming from security ID: {last_processed_security['last_processed_security_id']}")
        else:
            print("Starting from the beginning.")

        # Fetch all securities from the qt_securities table
        query = "SELECT * FROM qt_securities"
        if last_processed_security:
            query += f" WHERE symbolId > {last_processed_security['last_processed_security_id']}"
        query += " ORDER BY symbolId"

        cursor.execute(query)
        securities = cursor.fetchall()

        for security in securities:
            symbol_id = security['symbolId']
            symbol = security['symbol']

            print(f"Processing security ID: {symbol_id}, Symbol: {symbol}")

            try:
                # Get detailed symbol information
                symbol_info = qt.get_symbol_info(symbol_id)

                # Get quote information for additional details
                quote_info = qt.get_security_data(symbol_id)

                # Combine symbol_info and quote_info data
                combined_data = {**symbol_info, **quote_info}

                # Replace any 'NULL' strings or missing values with None
                combined_data = {key: (None if value == 'NULL' or value is None else value)
                                 for key, value in combined_data.items()}

                # Filter keys to match the columns in the qt_securities table
                cursor.execute("DESCRIBE qt_securities")
                table_columns = [row["Field"] for row in cursor.fetchall()]
                update_keys = [key for key in combined_data.keys() if key in table_columns]
                update_values = [combined_data[key] for key in update_keys]

                # Add the symbolId to the values for the WHERE clause
                update_values.append(symbol_id)

                # Dynamically construct the SQL update query
                update_query = f"""
                    UPDATE qt_securities
                    SET {', '.join([f"{key} = %s" for key in update_keys])}
                    WHERE symbolId = %s
                """

                # Execute the update query
                cursor.execute(update_query, update_values)
                db_connection.commit()

                # Save progress after successfully processing a security
                qt.resume_progress('update_qt_securities', 'save', security_id=symbol_id)

            except Exception as e:
                print(f"Error processing security ID {symbol_id}: {e}")
                # Save progress even if an error occurs so we can resume here next time
                qt.resume_progress('update_qt_securities', 'save', security_id=symbol_id)
                continue

        # After processing all securities, clear the progress marker.
        # This ensures that the next run will start from the beginning.
        qt.resume_progress('update_qt_securities', 'delete')
        
    db_connection.close()
    print("Successfully processed all securities.")

except Exception as e:
    print(f'Error: {e}')
