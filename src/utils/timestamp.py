from datetime import datetime
from random import random
import os 
from pathlib import Path

class Timestamp():
    def __init__(self):
      pass

    @staticmethod
    def get_timestamp(flag=False):
          now = datetime.now()
          date = now.strftime("_%m%d%Y")
          if flag: 
            date = now.strftime("_%m%d%Y_%S")
          #print(f"Formatted date: {date}")
          return date

    @staticmethod
    def get_rand():
          rand = str(random.randint(1, 1000))
          return rand

    @staticmethod
    def get_next_int(val: str, ts: str) -> int:
        return ts + val
    
    @staticmethod
    def strip_ts_val(ts: str) -> str:
      try: 
        indx = ts.index("(")
        return ts[:indx]
      except:
        return ts

    @staticmethod
    def get_new_ts(ts: str,csv_path: Path, chosen_name: str) -> str:
        ts = Timestamp.get_timestamp()
        i = 0
        while Timestamp.isPathExist(csv_path / f"_{chosen_name}{ts}"):
          temp = f"({i})"
          ts = Timestamp.get_next_int(temp, Timestamp.strip_ts_val(ts))
          i += 1
        return ts

    @staticmethod
    def isPathExist(file_path):
        if os.path.exists(file_path):
          return True 
        return False

    @staticmethod  
    def avoid_dup_file_name(table, timestamp):
      file_name = f"{table}{timestamp}.csv"
      return file_name 
      
    @staticmethod
    def upd_file_path(output_path, file_name):
        file_path = os.path.join(output_path, file_name)
        return file_path



