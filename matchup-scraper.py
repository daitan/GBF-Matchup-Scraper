# import libraries
from time import time as time_now
from time import sleep, strftime
from selenium import webdriver
from os import makedirs, path
from bs4 import BeautifulSoup
import argparse
from sys import argv
import threading
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from pytz import timezone    
from random import randint

from config import config

CHECK_FREQUENCY = 60.0 # in seconds

GW_DAY = '4'
GW_NUM = '035'
GW_URL = 'http://game.granbluefantasy.jp/#event/teamraid{}'.format(GW_NUM)

CHROME_ARGUMENTS = '--disable-infobars'

LOG_FILE = '[{}]granblue-scraper.log'.format(strftime('%m-%d_%H%M'))

def log(message):
  '''Prints to console and outputs to log file'''

  try:
    with open('.\\logs\\' + LOG_FILE, 'a',
        encoding='utf-8', newline='') as fout:
      message = '[%s] %s' % (strftime('%a %H:%M:%S'), message)
      print(message)
      print(message, file=fout)
  except FileNotFoundError:
    makedirs('.\\logs')
    log('Created log folder')
    log(message)

def main():
  global GBF
  timestart = time_now()
  profile = path.abspath(".\\" + CFG.profile)

  parser = argparse.ArgumentParser(prog='matchup-scraper.py',
    description='A simple script for scraping various parts of Granblue Fantasy',
    usage='matchup-scraper.py [profile] [gw] [finals day] [options]\nexample: python gbf-scraper.py profile2 035 5 -l',
    formatter_class=argparse.MetavarTypeHelpFormatter)

  parser.add_argument('profile', nargs='?',
    help='overwrites the default profile path', type=str)
  parser.add_argument('gw', nargs=2,
    help='scrapes matchup scores based on gw and finals day', type=str)
  parser.add_argument('--login', '-l',
    help='pauses the script upon starting up to allow logging in', action='store_true')
  args = parser.parse_args()

  if len(argv) == 1:
    parser.print_help()
    quit()

  if args.profile is not None:
    log('Changing profile path to {}'.format(args.profile))
    profile = path.abspath('.\\' + args.profile)

  if args.gw is not None and len(args.gw) == 2:
    log('Parsing scores for GW {} day {}'.format(args.gw[0], args.gw[1]))
    GW_NUM = args.gw[0]
    GW_DAY = args.gw[1]
    GW_URL = 'http://game.granbluefantasy.jp/#event/teamraid{}'.format(GW_NUM)
  else:
    parser.print_help()
    quit()

  options = webdriver.ChromeOptions()
  log('Using profile at: {}'.format(profile))
  options.add_argument('user-data-dir=%s' % profile)
  for cargs in CHROME_ARGUMENTS.split():
    options.add_argument(cargs)
  GBF = webdriver.Chrome(chrome_options=options)
  GBF.get('http://game.granbluefantasy.jp/#mypage')

  if args.login:
    log('Pausing to login')
    input('Press enter to continue...')

  jp_tz = timezone('Asia/Tokyo')

  while True:
    # use creds to create a client to interact with the Google Drive API
    scope = ['https://spreadsheets.google.com/feeds']
    creds = ServiceAccountCredentials.from_json_keyfile_name('client_secret.json', scope)
    client = gspread.authorize(creds)
 
    # Find a workbook by name and open the first sheet
    # Make sure you use the right name here.
    spreadsheet = client.open('GW Points')
    try:
      worksheet = spreadsheet.worksheet('GW {} - Day {}'.format(GW_NUM, GW_DAY))
    except:
      spreadsheet.add_worksheet('GW {} - Day {}'.format(GW_NUM, GW_DAY), 2, 21)
      worksheet = spreadsheet.worksheet('GW {} - Day {}'.format(GW_NUM, GW_DAY))
      worksheet.update_cell(1, 1, "Time")
      worksheet.update_cell(1, 2, "Guild")
      worksheet.update_cell(1, 3, "Guild+")
      worksheet.update_cell(1, 4, "Opponent")
      worksheet.update_cell(1, 5, "Opponent+")
      worksheet.update_cell(1, 6, "Difference")
      worksheet.update_cell(2, 1, "7:00:00")
      worksheet.update_cell(2, 2, "0")
      worksheet.update_cell(2, 3, "0")
      worksheet.update_cell(2, 4, "0")
      worksheet.update_cell(2, 5, "0")
      worksheet.update_cell(2, 6, "0")
    GBF.get(GW_URL);
    sleep(5)
    data = BeautifulSoup(GBF.page_source, 'html.parser')
    guild = 0
    rival = 0

    scores = data.find('div', attrs={'class': 'prt-battle-point'})
    if scores is not None:
      guild = int(scores.find('div', attrs={'class': 'txt-guild-point'}).text.strip().replace(',', ''))
      rival = int(scores.find('div', attrs={'class': 'txt-rival-point'}).text.strip().replace(',', ''))
      if worksheet.row_count == 1:
        guildplus = guild
        rivalplus = rival
      else:
        guildplus = guild - int(worksheet.cell(worksheet.row_count, 2).value.strip().replace(',', ''))
        rivalplus = rival - int(worksheet.cell(worksheet.row_count, 4).value.strip().replace(',', ''))
      difference = guild - rival
      worksheet.append_row([datetime.now(jp_tz).strftime('%H:%M:%S'), guild, guildplus, rival, rivalplus, difference])
    sleep(CHECK_FREQUENCY - ((time_now() - timestart) % CHECK_FREQUENCY))

if __name__ == '__main__':
  CFG = config()

  try:
    main()
  except Exception:
    GBF.close()
    raise
