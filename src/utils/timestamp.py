from datetime import datetime
from random import random
import os

def get_timestamp(flag=False):
      now = datetime.now()
      date = now.strftime("_%m%d%Y")
      if flag: 
        date = now.strftime("_%m%d%Y_%S")
      #print(f"Formatted date: {date}")
      return date

def get_rand():
        rand = str(random.randint(1, 1000))
        return rand

def isPathExist(file_path):
    if os.path.exists(file_path):
      return True 
    return False
  
def avoid_dup_file_name(table, timestamp):
  file_name = f"{table}{timestamp}.csv"
  return file_name 

def upd_file_path(output_path, file_name):
    file_path = os.path.join(output_path, file_name)
    return file_path
