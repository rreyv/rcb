import datetime
import emails
import HTMLParser
import logging
import OAuth2Util
import praw
import requests
import sqlite3 as sql
import time
from ConfigParser import SafeConfigParser

class schedule(object):

  def __init__(self):
    self.sched = dict()

  def __iter__(self):
    return iter(self.sched.itervalues())

  def add_match_day (self,match_day):
    if match_day.start_dt in self.sched:
      self.sched[match_day.start_dt].append(match_day)
    else:
      self.sched[match_day.start_dt]=[match_day]
  
  def sorted_keys(self):
    return sorted(self.sched)

  def get(self,key):
    return self.sched.get(key) 

class match_day(object):
  
  def __init__(self, match_id, day, start_date_time,match_name,match_abr,important, series_id):
    self.day = day
    self.match_id = match_id
    self.start_dt = start_date_time
    self.match_name = match_name
    self.match_abr = match_abr
    self.important = important
    self.series_id = series_id

def get_date_time (time):
  return datetime.datetime.strptime(time,'%Y-%m-%dT%H:%M:%SZ')

def get_team_name (team_name):
  if team_name.endswith(' Men'):
    team_name = team_name[:-4]
  return team_name

def add_match_to_schedule (match,upcoming_schedule):
  teams_we_care_about = ['Australia', 'Bangladesh', 'England', 'India', 'New Zealand', 'Pakistan', 'South Africa', 'Sri Lanka', 'West Indies', 'Zimbabwe']
  start_date_time = get_date_time(match['startDateTime'])
  end_date_time = get_date_time(match['endDateTime'])
  current_date_time = start_date_time
  day = 1
  match_name = get_team_name(match['homeTeam']['name']) + " vs " + get_team_name(match['awayTeam']['name']) + " at " + match['venue']['name']
  match_abr = match.get('homeTeam').get('shortName','???') + " vs " + match.get('awayTeam').get('shortName','???')
  series_id = match.get('series').get('id')
  important = (get_team_name(match['homeTeam']['name']) in teams_we_care_about) or (get_team_name(match['awayTeam']['name']) in teams_we_care_about) 
  #important = True
  if match['isMultiDay'] == False:
    matchDay = match_day (match['id'],1,start_date_time,match_name,match_abr, important, series_id)
    upcoming_schedule.add_match_day(matchDay)
    return
  while end_date_time > current_date_time:
    matchDay = match_day (match['id'],day,current_date_time,match_name + ", Day " + str(day),match_abr + ", D" + str(day), important, series_id)
    upcoming_schedule.add_match_day(matchDay)
    current_date_time = current_date_time + datetime.timedelta(days=1)
    day = day + 1

def create_wiki_schedule():
  matches_response = requests.get("https://dev132-cricket-live-scores-v1.p.mashape.com/matches.php",
      headers={
          "X-Mashape-Key": parser.get('r_cricket_bot','api_key'),
              "Accept": "application/json"
                })
  match_status = ['UPCOMING','INPROGRESS','LIVE']
  upcoming_schedule = schedule()
  match_data = matches_response.json()
  match_list = match_data['matchList']['matches']
  for match in match_list:
    if match['status'] in match_status:
      add_match_to_schedule (match,upcoming_schedule)
  return upcoming_schedule

def get_time_left(time1, time2):
  #returns time2 - time1 in #D #H #M
  timeleft = time2 - time1
  if time2 < time1:
    return 'In Progress', timeleft
  return str(timeleft.days).zfill(2) + "D " + str(timeleft.seconds//3600).zfill(2) + "H " + str((timeleft.seconds//60)%60).zfill(2) + "M", timeleft
  #return timeleft.days + "D " + timeleft.hours + "H " + timeleft.minutes + "M" 

def user_action(matchday):
  con = None
  con = sql.connect('rcricketbot.db',detect_types=sql.PARSE_DECLTYPES)
  cur = con.cursor()
  cur.execute("SELECT url from created where match_id = ? and series_id = ? and day = ?",(matchday.match_id, matchday.series_id, matchday.day))
  data = cur.fetchone()
  con.commit()
  con.close()
  if data:
    return "[Created](" + data[0] + ")"

  if matchday.important == True:
    return 'Scheduled'
  con = None
  con = sql.connect('rcricketbot.db',detect_types=sql.PARSE_DECLTYPES)
  cur = con.cursor()
  cur.execute("SELECT count(*) from requested where match_id = ? and series_id = ? and day = ?",(matchday.match_id, matchday.series_id, matchday.day))
  data = cur.fetchone()
  con.commit()
  con.close()
  if data[0] > 0:
    return "Scheduled"
  return '[Request Thread](https://www.reddit.com/message/compose/?to=rCricketBot&subject=create^'+str(matchday.match_id) + "^" + str(matchday.series_id) +"^" + str(matchday.day) + "&message=Don't change anything and just hit send.)"
  
def print_wiki_schedule(schedule,debug_mode,r):
  schedule_table = "This wiki lists all cricket fixtures scheduled to begin in the next 48 hours. \
      Matches involving test playing nations are pre-scheduled. To request a thread for any other match, \
      click on request thread and then hit send immediately without changing anything in the message. \
      You will get a confirmation shortly that a thread has been scheduled and will be created an hour before \
      the start time. \n\n"
  schedule_table += "Match | Time Left | Match Thread \n:--|:--|:--\n"
  current_date_time = datetime.datetime.utcnow()
  for match_date_time in upcoming_schedule.sorted_keys():
    for matchday in upcoming_schedule.get(match_date_time):
      time_left, time_left_dt = get_time_left(current_date_time,match_date_time)
      if (time_left_dt.total_seconds()//60 < - 480) and time_left == 'In Progress':
        continue
      elif (time_left_dt.total_seconds()//60 > 2880):
        continue
      else:
        name = '**' + str(matchday.match_name) + '**' if matchday.important else str(matchday.match_name)
        schedule_table = schedule_table + str(name) + "|" + time_left + "|" + user_action(matchday) + "\n"
        if (time_left_dt.total_seconds()//60 < 65) and matchday.important == True:
          add_to_requested_table(matchday,'rCricketBot',matchday.match_name)
  if debug_mode==True:
    print schedule_table
  else:
    try:
      wiki_page = r.get_wiki_page(subreddit,'bot_schedule')
      wiki_page.edit(schedule_table)
      logging.info('Successfully updated wiki.')
    except:
      logging.warning("Couldn't update wiki. Trying again in 50 seconds.")
      emails.sendEmail('Wiki Error!', 'Could not update wiki. Trying again in 50 seconds')

def print_sidebar_schedule(schedule,debug_mode,r):
  i = 0 
  schedule_table = ">Match|Time Left\n:--|:--\n"
  current_date_time = datetime.datetime.utcnow()
  for match_date_time in upcoming_schedule.sorted_keys():
    for matchday in upcoming_schedule.get(match_date_time):
      time_left, time_left_dt = get_time_left(current_date_time,match_date_time)
      if (not matchday.important) or time_left == 'In Progress':
        continue
      else:
        schedule_table = schedule_table + str(matchday.match_abr) + "|" + time_left + "\n"
        i+=1
        if i==5:
          break
    if i==5:
      break

  if debug_mode == True:
    logging.info(schedule_table)
    logging.info('Printing sidebar schedule.')
  else:
    end_of_table=">[More International Fixtures](http://www.espncricinfo.com/ci/engine/series/index.html?view=month)." #Signature to look for that marks the end of table
    beg_of_table=">**Upcoming International Fixtures:**" #Signature to look for that marks beginning of table
    
    schedule_table = beg_of_table + "\n\n" + schedule_table + "\n" + end_of_table

    try:
      settings = r.get_settings(subreddit)
      description_html = settings['description']
      html_parser = HTMLParser.HTMLParser()
      description = html_parser.unescape(description_html)
      if ((description.find(beg_of_table) == -1) or (description.find(end_of_table)==-1)):
        emails.sendEmail('Sidebar Error!', 'Could not find sidebar marker.')
        logging.error('Could not find the sidebar markers. Trying again in 50 seconds.')
        return
      description_begin = description.find(beg_of_table)
      description_end = description.find(end_of_table) + len(end_of_table)
      description = description[:description_begin] + schedule_table + description[description_end:]
      settings = r.get_subreddit(subreddit).update_settings(description=description)
      logging.info('Successfully updated sidebar.')
    except:
      logging.warning('Could not update sidebar. Trying again in 50 seconds.')
      emails.sendEmail('Sidebar Error!', 'Could not update sidebar. Trying again in 50 seconds.')

def create_thread_wrapper(r,debug_mode):
  con = None
  con = sql.connect('rcricketbot.db',detect_types=sql.PARSE_COLNAMES)
  cur = con.cursor()
  cur.execute("select match_id, series_id, day, thread_name, requestor, attempts,Pkey,start_date_time as '[timestamp]' from requested")
  data=cur.fetchall()
  con.commit()
  con.close()
  current_gmt = datetime.datetime.utcnow()
  if not data:
    return
  for fixture in data:
    if (fixture[7]-current_gmt).total_seconds()<3601:
      create_thread(fixture[0],fixture[1],fixture[2],fixture[3],fixture[5],r,fixture[4],fixture[6],debug_mode)
  return

def create_thread(match_id, series_id, day, thread_title, i, r, requestor,Pkey,debug_mode):

  try:
    score_response = requests.get("https://dev132-cricket-live-scores-v1.p.mashape.com/matchdetail.php?matchid=" + str(match_id) + "&seriesid=" + str(series_id),
    headers={
      "X-Mashape-Key":  parser.get('r_cricket_bot','api_key'),
      "Accept": "application/json"
      }
    )
    # score_response = requests.get("kasjdlas")
    score_data = score_response.json()
  except:
    if i == 5:
      logging.info("Failed to get scores from the API. I've tried 5 times and failed and won't try again.")
      emails.sendEmail('Create Thread Error', "Failed to get scores from the API for " + thread_title + " [ID: ]" + str(Pkey) + ". I've tried 5 times and failed and won't try again. Please create a match thread manually.")
      remove_from_requested_table(match_id, series_id, day)
      # delete_from_requested(Pkey)
    else:
      increment_attempts(Pkey)
      logging.info("Failed to get scores from the API. This was attempt #" + str(i) + " for "+ thread_title + " [ID: ]" + str(Pkey) + ".") 
    return

  try:
    #create thread with threadtitle from the schedule 
    if debug_mode == True:
      logging_info('Thread Title: ' + thread_title) 
    else:
      submission = r.submit(subreddit, "Match Thread: " + thread_title,text=thread_title)
      logging.info('Created thread. Title: ' + thread_title + ".")
  except:
    if i == 5:
      print "Failed to create thread. I've tried 5 times and failed and won't try again."
      #email - "Failed to create thread. I've tried 5 times and failed and won't try again. Please create a match thread manually."
      logging.info("Failed to create reddit thread. Reddit error. I've tried 5 times and failed and won't try again.")
      emails.sendEmail('Create Thread Error (reddit)', "Failed to create thread for " + thread_title + " [ID: ]" + str(Pkey) + ". I've tried 5 times and failed and won't try again. Please create a match thread manually.")
      remove_from_requested_table(match_id, series_id, day)
    else:
      increment_attempts(Pkey)
      logging.info("Failed to create thread. Reddit down? I've tried " + str(i) + " times and failed and won't try again.")
    return
  
  remove_from_requested_table(match_id, series_id, day)
  add_to_created_table(match_id, series_id, day, thread_title, requestor, submission.url, submission.id)

  #everything worked. Insert data in created_threads
  
def update_thread_wrapper(r, debug_mode):
  con = None
  con = sql.connect('rcricketbot.db',detect_types=sql.PARSE_COLNAMES)
  cur = con.cursor()
  cur.execute("select match_id, series_id, day, url, requestor, created_time as '[timestamp]', Pkey, sub_id from created where day_over < 6")
  data=cur.fetchall()
  con.commit()
  con.close()
  if not data:
    return
  for fixture in data:
    update_thread(fixture[0],fixture[1],fixture[2], r, fixture[3],fixture[4],debug_mode, fixture[5], fixture[6], fixture[7])
  return

def set_day_over(Pkey):
  con = None
  con = sql.connect('rcricketbot.db',detect_types=sql.PARSE_DECLTYPES)
  cur = con.cursor()
  cur.execute("update created set day_over = day_over + 1 where Pkey = ?",(Pkey,))
  con.commit()
  con.close()

def get_cricinfo_link(match_id, series_id, sub_id):
  con = None
  con = sql.connect('rcricketbot.db',detect_types=sql.PARSE_DECLTYPES)
  cur = con.cursor()
  cur.execute("SELECT cricinfo_url from match_info where match_id = ? and series_id = ?",(match_id, series_id))
  data = cur.fetchone()
  con.commit()
  con.close()
  if data:
    return "[Cricinfo Link](" + data[0] + ") "
  else:
    return "[Add Cricinfo Link](https://www.reddit.com/message/compose/?to=rCricketBot&subject=cricinfo^" + sub_id + ") "

def update_thread(match_id, series_id, day, r, url, requestor, debug_mode, creation_time, Pkey, sub_id):
  unsafe_statuses = ['UPCOMING']
  thread_text = ""

  try:
    score_response = requests.get("https://dev132-cricket-live-scores-v1.p.mashape.com/matchdetail.php?matchid=" + str(match_id) + "&seriesid=" + str(series_id),
    headers={
      "X-Mashape-Key":  parser.get('r_cricket_bot','api_key'),
      "Accept": "application/json"
      }
    )
  
  except:
    print "Failed to get scores from the API. Trying again in the next loop."
    return False
      
  score_data = score_response.json()

  current_gmt = datetime.datetime.utcnow()

  # update day_over flag if true
  if score_data.get('matchDetail').get('matchSummary').get('currentMatchState') in ['COMPLETED', 'STUMPS'] and (current_gmt - creation_time).total_seconds > 14400:
    set_day_over(Pkey) 
  
  #get match name and multiday
  match_name = score_data.get("meta").get("series").get("name") + ", " + score_data.get("meta").get("matchName")
  multi_day = True if score_data.get('matchDetail').get('matchSummary').get('isMultiDay')==True else False
  match_name = match_name + " - Day " + str(day) if multi_day else match_name
  thread_text += "###" + match_name + "\n\n"
  
  #need to add cricinfo link, stream links, reddit stream link
  reddit_stream=url.replace("reddit.com","reddit-stream.com")
  thread_text += get_cricinfo_link(match_id, series_id, sub_id)
  thread_text += "| [Live Streams](https://www.reddit.com/r/Cricket/wiki/livestreams) | "
  thread_text += "[Reddit-Stream](" + reddit_stream + ")\n\n"

  # add scorecard
  thread_text += "Innings|Score\n:--|:--\n"
  if score_data.get('matchDetail').get('matchSummary').get('status') not in unsafe_statuses:
    for inning in score_data.get('matchDetail').get("innings"):
      inning_name = inning.get('name')
      inning_name = inning_name[inning_name.rfind('Inn') + len('Inn '):] if multi_day==False else inning_name
      thread_text += inning_name + "|" + inning.get('score') + " (Ov " + inning.get('overs') + ")\n"

  #print batsman table
  thread_text += "\n\nBatsman | Runs | Balls | SR\n:--|:--|:--|:--\n"
  if score_data.get('matchDetail').get('matchSummary').get('status') not in unsafe_statuses:
    i = 0
    if score_data.get('matchDetail').get('currentBatters'):
      for batsman in score_data.get('matchDetail').get('currentBatters'):
        #The API shows every batsman twice for some reason. I'm hoping this i business is only temporary
        if i==2:
          break
        else:
          i+=1
        thread_text += batsman.get('name') + "|" + batsman.get('runs') + "|" + batsman.get('ballsFaced') + "|" + batsman.get('strikeRate') + "\n"

  #print bowler table
  thread_text += "\n\nBowler | Overs | Runs | Wickets \n:--|:--|:--|:--\n"
  if score_data.get('matchDetail').get('matchSummary').get('status') not in unsafe_statuses:
    bowler = score_data.get('matchDetail').get('bowler')
    if bowler:
      thread_text +=bowler.get('name') + "|" + bowler.get('bowlerOver') + "|" + bowler.get('runsAgainst') + "|" + bowler.get('wickets')

  thread_text += "\n\n" + score_data.get('matchDetail').get('matchSummary').get('matchSummaryText')

  if requestor == 'rCricketBot':
    thread_text+= "\n\nThis thread was created by a bot. Have feedback? [Send me a message.](https://www.reddit.com/message/compose/?to=rreyv)"
  else:
    thread_text+= "\n\nThis thread was requested by /u/" + requestor + " and created by a bot. Have feedback? [Send me a message.](https://www.reddit.com/message/compose/?to=rreyv)"

  if debug_mode == True:
    logging.info(thread_text)
  else:
    try:
      submission = r.get_submission(url=url)
      submission.edit(thread_text)
      logging.info('Updated match thread for ' + url)
    except:
      logging.info("Couldn't update match thread for " + url)

def add_to_created_table(match_id, series_id, day, thread_title, requestor, url, sub_id):
  con = None
  con = sql.connect('rcricketbot.db',detect_types=sql.PARSE_DECLTYPES)
  cur = con.cursor()
  current_gmt=datetime.datetime.utcnow()
  cur.execute("insert into created('match_id','series_id','day','thread_title','requestor','created_time', 'url', 'day_over','sub_id') values (?,?,?,?,?,?,?,?,?)",(match_id, series_id, day, thread_title, requestor,current_gmt,str(url), 0,str(sub_id)))
  con.commit()
  con.close()

def add_to_requested_table(matchday,requestor,name):
  con = None
  con = sql.connect('rcricketbot.db',detect_types=sql.PARSE_DECLTYPES)
  cur = con.cursor()
  cur.execute("SELECT count(*) from created where match_id = ? and series_id = ? and day = ?",(matchday.match_id, matchday.series_id, matchday.day))
  data = cur.fetchone()
  con.commit()
  con.close()
  if data[0] > 0:
    return

  con = None
  con = sql.connect('rcricketbot.db',detect_types=sql.PARSE_DECLTYPES)
  cur = con.cursor()
  cur.execute("SELECT count(*) from requested where match_id = ? and series_id = ? and day = ?",(matchday.match_id, matchday.series_id, matchday.day))
  data = cur.fetchone()
  con.commit()
  con.close()
  if data[0] > 0:
    return

  con = None
  con = sql.connect('rcricketbot.db',detect_types=sql.PARSE_DECLTYPES)
  cur = con.cursor()
  cur.execute("insert into requested('match_id','series_id','day','requestor','attempts','thread_name','start_date_time') values (?,?,?,?,?,?,?)",(matchday.match_id, matchday.series_id, matchday.day, requestor, 0, name, matchday.start_dt))
  con.commit()
  con.close()

def remove_from_requested_table(match_id, series_id, day):
  con = None
  con = sql.connect('rcricketbot.db',detect_types=sql.PARSE_DECLTYPES)
  cur = con.cursor()
  cur.execute("DELETE from requested where match_id = ? and series_id = ? and day = ?",(match_id, series_id, day))
  data = cur.fetchone()
  con.commit()
  con.close()

def increment_attempts(Pkey):
  con = None
  con = sql.connect('rcricketbot.db',detect_types=sql.PARSE_DECLTYPES)
  cur = con.cursor()
  cur.execute("update requested set attempts = attempts + 1 where Pkey = ?",(Pkey,))
  con.commit()
  con.close()

def find_match_day(upcoming_schedule, match_id, series_id, day):
  for match_date_time in upcoming_schedule.sorted_keys():
    for matchday in upcoming_schedule.get(match_date_time):
      if matchday.match_id == match_id and matchday.series_id == series_id and matchday.day == day:
        return matchday
  return None

def inbox(upcoming_schedule, r):
  already_done=[]
  try:
    messages = r.get_unread(limit=None)
  except:
    logging.info("Couldn't get unread messages. Quitting")
    return

  if not messages:
    return "No unread messages."

  try:
    for message in messages:
      subject = str(message.subject)
      author = str(message.author)
      split_subject = subject.split("^")
      try:
        message.mark_as_read()
      except:
        pass
      if ((message.was_comment==False) and (message.id not in already_done)):
        if message.author.comment_karma<100:
          reply_text = 'Your comment karma is too low to control this bot.'
          logging.info('/u/' + author + ' tried to control the bot with < 100 karma. Subject: ' + subject + '. Body: ' + str(message.body) + '.')
        elif split_subject[0].strip()=='create':
          match_id = int(split_subject[1].strip())
          series_id = int(split_subject[2].strip())
          day = int(split_subject[3].strip())
          match_day = find_match_day(upcoming_schedule, match_id, series_id, day)
          if match_day:
            add_to_requested_table(match_day, author, match_day.match_name)
            reply_text = 'Match thread for ' + match_day.match_name + ' has been scheduled.'
            logging.info('Match thread for ' + match_day.match_name + ' successfully requested by ' + author + '.')
          else:
            reply_text = 'Could not find match info. Did you change the subject of the message? If yes, please do not do that and resend the message. If not, just create a thread manually instead.'
        elif split_subject[0].strip()=='cricinfo':
          cricinfo_url = str(message.body)
          reddit_id = split_subject[1].strip()
          result = add_to_match_info_table(r, reddit_id, cricinfo_url, author)
          if result:
            reply_text = 'Thanks, the information has been saved and the match thread will be updated shortly.'
          else:
            reply_text = 'Error occurred. Someone might have sent in a link right before you. If the match thread does not show a link in a few minutes, try again.'
        else:
          reply_text = "I don't know what you're trying to say."
        try:
          message.reply(reply_text)
          already_done.append(message.id)
        except:
          logging.info ('Error occured when responding to the user but actions probably happened.')
  except:
    logging.info('Inbox troubles!')

def add_to_match_info_table(r, reddit_id, cricinfo_url, author):
  #if reddit_url.find('reddit.com')==-1 and reddit_url.find('redd.it')==-1:
  try:
    subm = r.get_submission(submission_id=reddit_id)
  except:
    return False
  #  return False
  if cricinfo_url.find('espncricinfo.com')==-1:
    return False
  
  con = None
  con = sql.connect('rcricketbot.db',detect_types=sql.PARSE_DECLTYPES)
  cur = con.cursor()
  current_gmt=datetime.datetime.utcnow()
  cur.execute("select match_id, series_id from created where sub_id = ?",(reddit_id,))
  data = cur.fetchone()
  con.commit()
  con.close()

  if not data:
    return False
  
  match_id = data[0]
  series_id = data[1]

  con = None
  con = sql.connect('rcricketbot.db',detect_types=sql.PARSE_DECLTYPES)
  cur = con.cursor()
  current_gmt=datetime.datetime.utcnow()
  cur.execute("select count(cricinfo_url) from match_info where match_id = ? and series_id = ?",(match_id, series_id))
  data = cur.fetchone()
  con.commit()
  con.close()

  if data[0] > 0:
    return False

  con = None
  con = sql.connect('rcricketbot.db',detect_types=sql.PARSE_DECLTYPES)
  cur = con.cursor()
  current_gmt=datetime.datetime.utcnow()
  cur.execute("insert into match_info('match_id','series_id', 'cricinfo_url','cricinfo_user') values (?,?,?,?)",(match_id, series_id, cricinfo_url, author))
  con.commit()
  con.close()
  return True


if __name__=="__main__":

  #config stuff
  parser = SafeConfigParser()
  parser.read('config.ini')
  debug_mode = parser.getboolean('r_cricket_bot','debug_mode')
  subreddit = parser.get('r_cricket_bot','subreddit')
  
  #init variables
  i = 0
  r = None

  if debug_mode == False:
    r = praw.Reddit('/r/cricket sidebar updating, wiki updating and match thread creating bot by /u/rreyv v2.0. Please let me know if it is causing issues. Should only call into the API 4-5 times every 50 seconds.')
    o = OAuth2Util.OAuth2Util(r)
    o.refresh(force=True)
    logging.basicConfig(filename='logfile.log',format='%(asctime)s %(message)s',level=logging.INFO)
  else:
    logging.basicConfig(format='%(asctime)s %(message)s',level=logging.INFO)

  while True:
    #things to do every 15 minutes
    logging.info("Getting data from API.")
    upcoming_schedule = create_wiki_schedule()
    while True:
      #things to do every 50 seconds
      logging.info("Attempting to update schedules.")
      inbox(upcoming_schedule, r)
      print_wiki_schedule (upcoming_schedule,debug_mode,r)
      print_sidebar_schedule (upcoming_schedule, debug_mode, r)
      create_thread_wrapper(r, debug_mode)
      update_thread_wrapper(r, debug_mode)
      i += 1
      if i%5 == 0:
        break
      time.sleep(50)
    i = 0
