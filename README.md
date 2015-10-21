reates match threads and updates the sidebar and a wiki for /r/cricket

Features
-----
* Lists the next five fixtures for all test playing nations on the sidebar and the time left.
* Lists all cricket matches that are going to take place in the next 48 hours and the time left on /wiki/bot_schedule
* Creates match threads automatically for all matches involving the test playing nations one hour prior to the start
* Users with 100+ karma can request match threads for any game by going to the wiki page mentioned above and requesting a thread. The thread will be created automatically one hour prior to the start.
* Keeps all match threads up to date with the latest score.

Running this on your own subreddit
-----

1. Get the source code
2. Install python
2. Install the following modules: [PRAW] [1], [OAuth2Util] [2]
3. OAuth2Util comes with its own setup so make sure you do that.
3. Get an API key from: https://market.mashape.com/dev132/cricket-live-scores. This is our source of truth. You don't have to pay, the free tier allows us 2500 API hits which should be more than enough for regular use cases. We hit the API once every 15 minutes for the schedules (96 hits a day) and once per minute for any match thread. Assuming it's an 8 hour game, that's 480 API hits. So 2500 has us covered for any day with four or less match threads.
4. Create a sqlite3 database in the source folder with the name 'rcricketbot.db'
4. Create the three tables using the scripts present in tables.sql.
5. Edit config.ini to suit your needs.
6. run the bot - `python bot.py`



 [1]: https://praw.readthedocs.org/en/latest/ "PRAW"
 [2]: https://github.com/SmBe19/praw-OAuth2Util "OAuth2Util"
