import logging
import smtplib
from email.mime.text import MIMEText
from ConfigParser import SafeConfigParser

def sendEmail(subject, text):
  parser = SafeConfigParser()
  parser.read('config.ini')

  from_user = parser.get('r_cricket_bot','email_id')
  from_pass = parser.get('r_cricket_bot','email_pass')
  to_user = [parser.get('r_cricket_bot','to_email_id')]
  message = """\From: %s\nTo: %s\nSubject: %s\n\n\n%s""" % (from_user, ",".join(to_user), subject, text)
  try:
    s = smtplib.SMTP('smtp.gmail.com', 587)
    s.ehlo()
    s.starttls()
    s.ehlo()
    s.login(from_user, from_pass)
    s.sendmail(from_user,to_user,message)
    s.quit()
  except:
    logging.warning('Cannot send email.')
