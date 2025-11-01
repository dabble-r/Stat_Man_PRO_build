from src.core.node import Node
from PySide6.QtWidgets import QMessageBox, QDialog
import random
#from team import beef, rougarou

class LinkedList():
  COUNT = 0

  @classmethod
  def get_count(cls):
    return cls.COUNT 
  
  @classmethod
  def set_count(cls):
    cls.COUNT += 1
  
  def __init__(self, message=None, name=None, head=None):
    self.admin = {
      "Name": 'League',
      "Commissioner": None,
      "Treasurer": None,
      "Communications": None,
      "Historian": None,
      "Recruitment": None,
      "Start": None,
      "Stop": None
    }
    self.date = None
    self.season = None
    self.location = None
    self.head = head 
    self.name = 'League' 
    self.message = message 
    self.leagueID = self.get_hash()

    # --------------------------------------------------------------- # 

  def get_hash(self):
    def indx(a, b):
        index = a.index(b)
        if index == 0:
            return 2 
        return index
    ord_lst = [sum(ord(x)*indx(self.admin['Name'], x) for x in self.admin['Name'])]
    
    return ord_lst.pop() 
  
  def get_rand_hash(self):
    def indx(a, b):
        index = a.index(b)
        if index == 0:
            return 2 
        return index
    ord_lst = [sum(ord(x)*indx(self.admin['Name'], x) for x in self.admin['Name'])]
    rand = random.randint(0,1000)
    return ord_lst.pop() + rand
  
  def get_incr_hash(self, val):
    return val + 1
  
  def format_decimal(self, num):
    return "{:.3f}".format(num)

  def __str__(self):
    ret = ''
    if LinkedList.COUNT == 0:
      ##print('No teams in league')
      return ret
    else:
      ret = "League\n"
      traverser = self.head
      while traverser is not None:
        tmp = f'Team: {traverser.team.name}\n'
        ret += tmp
        tmp = ''
        if traverser.next is not None:
          traverser = traverser.next
        else:
          return ret
      #ret += f'Team: {traverser.team.name}\n'
      return ret
  
  def get_team_objs_barset(self):
    '''
    example temp: ('team1', 'Beef Sliders', [1,2,3,4,5])
    '''

    if self.COUNT == 0:
      return False
    
    traverser = self.head
    ret = []
    c_ret = [] 
    t_ret = []
    stat_ret = []

    while traverser is not None:
      indx = 1
      count = "team" + str(indx)
      team = traverser.team.name 
      hits = int(traverser.team.get_team_hits())
      so = int(traverser.team.get_team_so())
      runs = int(traverser.team.get_team_runs())
      era = float(traverser.team.get_team_era())
      k = int(traverser.team.get_team_k())
      avg = round(float(traverser.team.get_bat_avg()), 3)
      #avg = "{:.3f}".format(float(traverser.team.get_bat_avg()))
      stats = [hits, so, runs, era, k, avg]

      if hits == 0:
        #print('hits:', hits)
        return False

      c_ret.append(count)
      t_ret.append(team)
      stat_ret.append(stats)

      indx += 1

      if traverser.next is not None:
        traverser = traverser.next
      else:
        ret.append(t_ret)
        ret.append(stat_ret)
        return ret
      
    ret.append(t_ret) 
    ret.append(stat_ret)
    return ret
  
  def get_team_objs_barset_spec(self, lst):
    traverser = self.head
    ret = []
    c_ret = [] 
    t_ret = []
    stat_ret = []
    check_team = lst

    while traverser is not None:
      indx = 1
      count = "team" + str(indx)
      team = traverser.team.name 

      if team in check_team:
        hits = int(traverser.team.get_team_hits())
        so = int(traverser.team.get_team_so())
        runs = int(traverser.team.get_team_runs())
        era = float(traverser.team.get_team_era())
        k = int(traverser.team.get_team_k())
        avg = round(float(traverser.team.get_bat_avg()), 3)
        stats = [hits, so, runs, era, k, avg]

        if hits == 0:
          ##print('hits:', hits)
          return False

        c_ret.append(count)
        t_ret.append(team)
        stat_ret.append(stats)
        indx += 1

        if traverser.next is not None:
          traverser = traverser.next

        else:
          ret.append(t_ret)
          ret.append(stat_ret)
          return ret
        
      else:
        if traverser.next is not None:
          traverser = traverser.next
          
        else:
          ret.append(t_ret)
          ret.append(stat_ret)
          return ret

    ret.append(t_ret) 
    ret.append(stat_ret)
    return ret
  

  # deprecated
  def get_team_objs_lineseries(self):
    '''example temp: 
      ('team1', 'Beef Sliders', 0.432)
    '''
    if self.COUNT == 0:
      return None
    traverser = self.head
    ret = [(),(),()]
    while traverser is not None:
      indx = 1
      count = "team" + str(indx)
      team = traverser.team.name 
      avg = traverser.team.get_bat_avg()
      #temp = (count, team, avg)
      ret[0].append(count)
      ret[1].append(team)
      ret[2].append(avg)
      indx += 1
      if traverser.next is not None:
        traverser = traverser.next
      else:
        return ret
    #ret += f'Team: {traverser.team.name}\n'
    return ret
    
  def get_admin(self):
    ret = 'League Admin\n'
    ret += f" League Name: {self.admin['League Name']}\n"
    ret += f" Commissioner: {self.admin['Commissioner']}\n"
    ret += f" Historian: {self.admin['Historian']}\n"
    ret += f" Treasurer: {self.admin['Treasurer']}\n"
    ret += f" Recruitment: {self.admin['Recruitment']}\n"
    ret += f" Communications: {self.admin['Communications']}\n"
    ret += f" Season Start: {self.admin['Season Start']}\n"
    ret += f" Season End: {self.admin['Season End']}"
    return ret
  
  def return_dict(self, dict):
        ret = "" 
        ###print('return dict:', dict)
        for el in dict:
            ##print('return dict:', el)
            ret += f"{el}:{dict[el]}\n"
        return ret
          
  # team lineup 
  # list of tuples
  def format_dict(self, dict):
        ret = []
        ret_dict = self.return_dict(dict).split("\n")
        ###print(ret_dict)
        for el in ret_dict:
            # not necessary
            indx = el.find(":")
            el = el.replace(":", " ")
            val = el[:indx].strip()
            name = el[indx::].strip()
            ret.append((val, name))
            #temp = None
        ret.pop()
        return ret
        
  # team stats 
  # list of all team stats plus lineup as tuples
  def return_admin(self):
        admin = self.format_dict(self.admin)
        #admin.pop()
        ##print('return stats:', admin)
        return admin

  def ques_replace(self, attr, stat, parent):
    ##print("admin:\n", attr, stat)
    existing_val = getattr(self, attr)[stat]
    if existing_val:
      reply = QMessageBox.question(parent, "Input Error", f"Would you like to replace {existing_val} at {stat}?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
      return reply 
    return None
    
    # --------------------------------------------------------------- # 
  

    # --------------------------------------------------------------- #
  
  def add_team(self, val):
    """Append a Team node to the end of the league list and increment COUNT."""
    new_node = Node(val)
    if self.head == None:
      self.head = new_node 
      self.head.next = None
      LinkedList.set_count()
      return
    curr = self.head
    while curr.next != None:
      curr = curr.next
    curr.next = new_node
    new_node.next = None
    LinkedList.set_count()
    return
  
  def remove_team(self, target): 
      """Remove first Team node whose name matches target; update COUNT accordingly."""
      if self.head.team.name == target and LinkedList.COUNT == 1:
        self.head = None
        LinkedList.COUNT -= 1
        ###print(f'Removing {target}')
        return
      
      elif self.head.team.name != target and LinkedList.COUNT == 1:
        return
      
      if self.head.team.name == target and LinkedList.COUNT > 1:
        curr = self.head
        self.head = curr.next
        curr = None
        LinkedList.COUNT -= 1
        ###print(f'Removing {target}')
        return
      traverser = self.head
      prev = None
      while traverser is not None:
        if traverser.team.name == target:
            if prev is not None:
                prev.next = traverser.next
            else:
                self.head = traverser.next
                traverser = None
            LinkedList.COUNT -= 1
            return
        prev = traverser
        traverser = traverser.next
      return
      ###print('end of list')
  
  def find_team(self, target):
    """Return Team by case-insensitive name match, or None if not present."""
    def _norm(s):
      try:
        return str(s).strip().lower()
      except Exception:
        return s
    traverser = self.head
    if traverser == None:
      return None
    target_n = _norm(target)
    # check head
    if _norm(traverser.team.name) == target_n:
      return traverser.team
    # traverse rest
    while traverser.next != None:
      if _norm(traverser.next.team.name) == target_n:
        return traverser.next.team
      traverser = traverser.next 
    return None
  
  def find_teamID(self, target):
    """Return Team by exact teamID match (int), or None if not present."""
    traverser = self.head
    if traverser == None:
      ###print('No teams in league\n')
      return None
    if traverser.team.teamID == target:
      return traverser.team
    else:
      while traverser.next != None:
        if traverser.next.team.teamID == target:
          return traverser.next.team
        traverser = traverser.next 
    ###print('Team not found')
    return None
  
  def find_player(self, target):
    traverser = self.head 
    if traverser == None:
      return 
    if len(traverser.team.players) == 0:
      return 
    while traverser.next != None:
      for el in traverser.team.players:
        if el.name == target:
          return el 
        traverser = traverser.next
    return

  def view_all(self):
    """Return string summary of teams and first-position players across league."""
    if LinkedList.COUNT == 0:
      ##print('No teams in league')
      return ''
    else:
      ret = ''
      traverser = self.head 
      while traverser != None:
        ret += f'\nTeam: {traverser.team.name}\nPlayers: {[{x.name: x.positions[0]} for x in traverser.team.players]}'
        traverser = traverser.next
      return ret
    
    # --------------------------------------------------------------------- #

  def set_admin(self, attr, stat, val, parent):
    ##print('attr:', attr)
    ##print('stat:', stat)
    ##print('val:', val)
    if 'Season' in stat:
      self.admin[stat] = val
      return
    
    reply = self.ques_replace(attr, stat, parent)
    if reply == QMessageBox.StandardButton.No: 
      return
    
    self.admin[stat] = val

    #print("admin:\n", stat, val)

    # --------------------------------------------------------------------- #
  def isDefaultName(self):
    return self.admin['Name'] == 'League'  
  
  def get_all_players_num(self):
    ret = []
    if LinkedList.COUNT == 0:
      ##print('No teams in league')
      return ret
    else:
      traverser = self.head 
      while traverser != None:
        players = traverser.team.players
        for el in players:
          team_val = el.team.name if hasattr(el.team, 'name') else el.team
          temp = (el.name, team_val, str(el.number))
          ret.append(temp)
          temp = None
        traverser = traverser.next
      return ret
  
  def get_all_players_avg(self):
    ret = []
    if LinkedList.COUNT == 0:
      ##print('No teams in league')
      return ret
    else:
      traverser = self.head 
      while traverser != None:
        players = traverser.team.players
        for el in players:
          temp = (el.name, el.team, el.AVG)
          ret.append(temp)
          temp = None
        traverser = traverser.next
      return ret
  
  def get_all_avg(self):
    ret = []
    if LinkedList.COUNT == 0:
      ##print("no team sin league")
      return ret 
    traverser = self.head 
    while traverser != None:
      name = traverser.team.name 
      roster = traverser.team.max_roster
      avg = self.format_decimal(float(traverser.team.get_bat_avg()))
      ret.append((name, roster, avg))
      traverser = traverser.next 
    return ret

  def get_all_wl(self):
    ret = []
    if LinkedList.COUNT == 0:
      ##print("no team sin league")
      return ret 
    traverser = self.head 
    while traverser != None:
      name = traverser.team.name 
      roster = traverser.team.max_roster
      avg = self.format_decimal(float(traverser.team.get_wl_avg()))
      ret.append((name, roster, avg))
      traverser = traverser.next 
    return ret
  
  def get_all_team_names(self):
    ret = []
    if LinkedList.COUNT == 0:
      ##print("no team sin league")
      return None
    traverser = self.head
    while traverser != None:
      name = traverser.team.name 
      ret.append(name)
      traverser = traverser.next 
    return ret
  
  def get_team_era(self):
    '''
    team = all players
    players = [a,b,c,d,e,f,g]
    a.positions = [a,b,c,d,pitcher,e,f,g]
    if 'pitcher' in a.positions:
      temp = a.era
      total += temp 
      temp = 0
    '''
    ret = []
    total = 0 
    if LinkedList.COUNT == 0:
      ##print('No teams in league')
      return self.format_decimal(ret)
    else:
      traverser = self.head 
      while traverser != None:
        players = traverser.team.players
        for el in players:
          pos = el.positions
          if 'pitcher' in pos:
            temp = float(el.era) 
            total += temp
            temp = 0
        ret.append((traverser.team.name, str(total)))
        total = 0
        traverser = traverser.next
      return ret
    
  def get_all_objs(self):
    ret = []
    if self.COUNT == 0:
      return ret
    traverser = self.head
    while traverser is not None:
      objTeam = traverser.team 
      ret.append(objTeam)
      traverser = traverser.next 
    return ret


  

# create league
#PBL = LinkedList('People\'s Baseball League')

#add team to league
#PBL.add_team(beef)
#PBL.add_team(rougarou)

# view all players
#all_players_league = PBL.view_all()
###print(all_players_league)

#find existing team in league
#team_search = PBL.find_team('Rougarou')
###print(team_search)

# curr state of league, view all teams
###print(PBL)



  

  

