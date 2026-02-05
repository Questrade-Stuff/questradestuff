run AlphaSweep.py first - it populates the db with all the securities from questrade.  I dont know why qt doesnt just give a list, but whatever.  also since I only buy CAD stocks, its only grabbing securities traded in CAD. I cron it to run evfery morning at like 4am
when you run it the first time it will see your oAuth rows are empty and will ask for the key from QY, just put it there and it will do the rest 
AlphaEnrich.py run second - it goes through all the securities and fills out stuff like 52w high low, etc - I cron this at like 8pm daily
AlphaCandle.py stores 500 days of 1min candles for each security (QT only gives a few months worth) and having a db of candle data is easier to backtest other scripts against - I cron this at 9:30 daily
token_keepalive.py does what you expect - I cron it to run every 12 hrs
questrade_api.py is the qt api, but I added some things that other scripts used.  its not efficient, Im not an amazing program and this was all done before chatgpt
dividend_calculator.py will go through your securities and will show you your expected dividends.  I only purchase ones that pay monthly, so I cant remember if it will even list quarterly payers.
highest_yeild.py uses the data from AlphaEnrich.py to sort the best dividend payers that you dont already own.  if it is the first time choosing that security it will scrape tmx.com with playright to see if it pays monthly or quarterly, and it only displays monthly payers
opening_rebound_score2.py runs before daily_ema_scoreboard2.py  - its just an idea im working on.  ignore it, or run the script through claude or chatgpt and ask what it does - Im sure it could explain it better than I can here.
schema.sql is what you'll need to setup a mysql db
and put in your mySQL credentials in the credentials.py file - all oauth stuff is in the database 
youll see the oauth is setup for multiple users - thats beacuse I run this against mine, and my wifes account
hopefully you know your way around python to get the requirements setup, im sure your local friendly llm can help
no guarentees, no promises - somebody just asked me to share.
