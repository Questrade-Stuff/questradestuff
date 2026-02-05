#!/usr/bin/env python3
#token_keepalive.py
"""
Daily token refresh to keep Questrade API tokens alive for all users
"""
import sys
sys.path.append('/home/scott/coding/Questrade')

from questrade_api import QuestradeAPI

def refresh_tokens():
    """Refresh tokens for all configured users"""
    # User IDs from your qt_users table (1 = Binx, 2 = Jinx)
    user_ids = [1, 2]
    
    for user_id in user_ids:
        try:
            print(f"Refreshing token for user_id {user_id}...")
            
            # Initialize API with specific user_id (skips prompt)
            qt = QuestradeAPI(user_id=user_id)
            
            # Make any simple API call to trigger token refresh
            time_response = qt.time()
            
            if time_response:
                print(f"✓ User {user_id} token refreshed successfully at {time_response.get('time', 'unknown')}")
            else:
                print(f"✗ User {user_id} token refresh failed")
                
        except Exception as e:
            print(f"✗ Error refreshing user {user_id} token: {e}")

if __name__ == "__main__":
    refresh_tokens()