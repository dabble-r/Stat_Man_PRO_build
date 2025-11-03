from PySide6.QtWidgets import QMessageBox

from PySide6.QtWidgets import QMessageBox


class SamplePlayer():
  def __init__(self, name, number, team, league, positions=[], message=None, parent=None):
    self.name = name 
    self.number = number 
    self.team = team
    self.league = league
    self.positions = positions
    self.pa = 0
    self.at_bat = 0 
    self.fielder_choice = 0
    self.hit = 0 
    self.bb = 0
    self.hbp = 0
    self.put_out = 0
    self.so = 0
    self.hr = 0
    self.rbi = 0
    self.runs = 0
    self.singles = 0
    self.doubles = 0
    self.triples = 0
    self.sac_fly = 0
    self.OBP = 0
    self.BABIP = 0
    self.SLG = 0
    self.AVG = 0
    self.ISO = 0
    self.max = 0
    self.image = None

    #message box
    self.message = message
    ##print('player initialized - msg inst', self.message)

    # message box self 
    self.parent = parent

  def __str__(self):
    ret = f'Name: {self.name}\nNumber: {self.number}\nPrimary Position: {self.positions[0]}\n  Secondary Positions: {self.positions[1:]}\n'
    ret += f'PA: {self.pa}\nAt Bats: {self.at_bat}\nHits: {self.hit}\nWalks: {self.bb}\nHBP: {self.hbp}\nSO: {self.so}\nHR: {self.hr}\n'
    ret += f'Runs: {self.runs}\nRBI: {self.rbi}\nOBP: {self.OBP}\nBABIP: {self.BABIP}\nSLG: {self.SLG}\nAVG: {self.AVG}\nISO: {self.ISO}' 
    return ret
  
  def set_min(self):
      #self.message.show_message('Sample chart. Player has no updated stats!')
      print('sample player set min called!')
      self.at_bat = 60 
      self.pa = 75
      self.bb = 10 
      self.hbp = 5
      self.hit = 20
      self.sac_fly = 10
      self.put_out = 5
      self.so = 20 
      self.fielder_choice = 5
      self.hr = 3  
      self.singles = 10 
      self.doubles = 5 
      self.triples = 2
  
  def _get_attrs(self):
      directory = dir(self)
      ret = []
      for el in directory:
        temp = getattr(self, el)
        if isinstance(temp, (int)):
            ###print(temp, el)
            ret.append((el, temp))
      return ret
  
  
class Player():
  def __init__(self, name, number, team, league, positions=[], message=None, parent=None):
    self.name = name 
    self.playerID = self.get_hash()
    self.number = number 
    self.team = team
    self.teamID = team.teamID 
    self.league = league
    self.leagueID = self.league.leagueID
    self.positions = positions
    self.pa = 0
    self.at_bat = 0 
    self.fielder_choice = 0
    self.hit = 0 
    self.bb = 0
    self.hbp = 0
    self.put_out = 0
    self.so = 0
    self.hr = 0
    self.rbi = 0
    self.runs = 0
    self.singles = 0
    self.doubles = 0
    self.triples = 0
    self.sac_fly = 0
    self.OBP = 0
    self.BABIP = 0
    self.SLG = 0
    self.AVG = 0
    self.ISO = 0
    self.max = 0
    self.image = None

    #message box
    self.message = message
    ##print('player initialized - msg inst', self.message)

    # message box self 
    self.parent = parent

  def __str__(self):
    ret = f'Name: {self.name}\nNumber: {self.number}\nPrimary Position: {self.positions[0]}\n  Secondary Positions: {self.positions[1:]}\n'
    ret += f'PA: {self.pa}\nAt Bats: {self.at_bat}\nHits: {self.hit}\nWalks: {self.bb}\nHBP: {self.hbp}\nSO: {self.so}\nPut Out: {self.put_out}\nHR: {self.hr}\n'
    ret += f'Runs: {self.runs}\nRBI: {self.rbi}\nOBP: {self.OBP}\nBABIP: {self.BABIP}\nSLG: {self.SLG}\nAVG: {self.AVG}\nISO: {self.ISO}' 
    return ret
  
  def get_hash(self):
    def indx(a, b):
        index = a.index(b)
        if index == 0:
            return 2 
        return index
    ord_lst = [sum(ord(x)*indx(self.name, x) for x in self.name)]
    return ord_lst.pop()

  def check_graph_min(self):
    stats = ['hit', 'bb', 'so'] 
    for stat in stats:
      val = getattr(self, stat)
      if val == 0:
        #print('Sample chart, must update at bats, hits, walks, SOs !')
        return False 
    return True
  
  def set_min(self):
      #self.message.show_message('Sample chart. Player has no updated stats!')
      self.at_bat = 70 
      self.pa = 85
      self.bb = 10 
      self.hbp = 5
      self.hit = 20
      self.sac_fly = 10
      self.put_out = 15
      self.so = 20 
      self.fielder_choice = 5
      self.hr = 3  
      self.singles = 10 
      self.doubles = 5 
      self.triples = 2

  def graph_view_format_player(self):
        self.sample_player = None
        flag = True
        '''data_test_player = [
          {
            'Stat': 'On Base',
            'Amount': [{"Hit": 177}, {"BB": 111},{"HBP": 6}, {"Error": 3}],
          },
          {
            'Stat': 'Outs',
            'Amount': [{"SO": 175}, {"Sac Fly": 5}, {"GIDP": 14}],
          }
        ]'''
        check = self.check_graph_min()
        if check == False:
          
          self.sample_player = SamplePlayer('Sample Player', 1, 'Sample Team', 'Sample League', ['first', 'second', 'third'], message=self.message)
          self.sample_player.set_min()
          #print(self.sample_player)
          flag = False

        ret = [
            {
            'Stat_1': None, 
            'Amount_1': [] 
            },
            {
            'Stat_2': None, 
            'Amount_2': [] 
            }
        ]
        on_base = ['bb', 'hbp', 'fielder_choice', 'singles', 'doubles', 'triples', 'hr']
        outs = ['so', 'sac_fly', 'put_out']
        attrs = self._get_attrs()
        if self.sample_player:
          attrs = self.sample_player._get_attrs()
        ##print(attrs)
        for el in attrs:
            ##print(el)
            stat = el[0]
            val = el[1]
            ##print(stat, val)
            stat_1 = ret[0]['Stat_1']
            stat_2 = ret[1]['Stat_2']
            if stat in on_base:
                ##print(stat)
                if not stat_1:
                    ret[0]['Stat_1'] = 'On Base' 
                    temp = {stat:val}
                    amt_lst_1 = ret[0]['Amount_1']
                    amt_lst_1.append(temp) 
                else:
                    temp = {stat:val}
                    amt_lst_1 = ret[0]['Amount_1']
                    amt_lst_1.append(temp) 
            elif stat in outs:
                ##print(stat)
                if not stat_2:
                    ret[1]['Stat_2'] = 'Outs'
                    temp = {stat:val}
                    amt_lst_1 = ret[1]['Amount_2']
                    amt_lst_1.append(temp) 
                else:
                    temp = {stat:val}
                    ##print(temp)
                    amt_lst_2 = ret[1]['Amount_2']
                    amt_lst_2.append(temp)
        return (ret, flag)

  def format_player(self, raw_lst):
    team = raw_lst[0]
    name = raw_lst[1]
    number = raw_lst[2]
    #avg = self.AVG
    positions = raw_lst[3:]
    ###print(raw_lst)
    ###print('team', team)
    ###print('name', name)
    ###print('number', number)
    new_player = Player(name, number, team, positions)
    return new_player

  # utilities 

  def format_decimal(self, num):        return "{:.3f}".format(num)
  
  def less_zero(self, stat, val):       return stat + val < 0

  def limit_at_bat(self, stat, val):    return (stat + val) > self.at_bat

  def _add_stat(self, attr, val, minimum=0, maximum=None, max_label=None):
      """Safely add val to stat, validate boundaries."""
      current = getattr(self, attr)
      new_total = current + val

      if new_total < minimum:
          self._warn(f"{attr.upper()} cannot be negative.")
          return

      if maximum is not None and new_total > maximum:
          label = max_label or maximum
          self._warn(f"{attr.upper()} cannot exceed {label}.")
          return

      setattr(self, attr, new_total)
  
  def _warn(self, message):
      #QMessageBox.warning(self.parent, "Stat Input Error", message)
      #print('warn error msg inst', self.message)
      self.message.show_message(message)
      
  def _get_attrs(self):
      directory = dir(self)
      ret = []
      for el in directory:
        temp = getattr(self, el)
        if isinstance(temp, (int)):
            ###print(temp, el)
            ret.append((el, temp))
      return ret
  
  def _get_max(self, stat):
      check_hits = ['hr', 'runs', 'singles', 'doubles', 'triples']
      check_bats = ['hit', 'bb', 'so', 'sac_fly']
      total = 0 
      if stat in check_hits:
          for el in check_hits:
              curr = getattr(self, el)
              total += curr 
      elif stat in check_bats:
          for el in check_bats:
            curr = getattr(self, el)
            total += curr 
      return total
  
  def _validate_update(self, stat, update, val):
    curr_stat = getattr(self, stat)
    total = self._get_max(update)
    new_total = total + val
    curr_update = getattr(self, update)
    new_val = curr_update + val
    if new_total > curr_stat:
        ###print('invalid stat update')
        self._warn(f"{update.capitalize()} update total cannot exceed {stat.capitalize()} {curr_stat}.")
    else:
        ##print('valid stat update')
        #print('curr val:', stat, curr_stat)
        #print('curr total:', total)
        #print('new total:', new_total)
        setattr(self, update, new_val)
    
    # ------------------------------------------------------------------------ #
    # getters 

  def get_at_bat(self):                 return self.at_bat 
  
  def get_BABIP(self):                  return self.BABIP
  
  def get_SLG(self):                    return self.SLG
  
  def get_AVG(self):                    return self.AVG

  def get_ISO(self):                    return self.ISO 

  def get_OBP(self):                    return self.OBP

    # ------------------------------------------------------------------------ #
    # setters 
  def set_pa(self, val):
    #self.pa += val
    self.pa += val

  def set_at_bat(self, val):
    self.at_bat += val
    #self._validate_update('pa', 'at_bat', val)
    #self._add_stat('at_bat', val)
    '''if self.at_bat + val < 0:
      self.at_bat = 0
    else:
      ##print('type val - at bat', type(val))
      self.at_bat += val'''
        
  def set_hit(self, val):
    self.hit += val 
    self.set_at_bat(val)
    self.set_pa(val)
    #self._validate_update('at_bat', 'hit', val)

    #self._add_stat('hit', val, maximum=self.at_bat)

    '''if self.at_bat == 0:
      self.hit = 0
    elif self.hit > self.at_bat:
      ##print('excess hits')
    else:
      self.hit += val
      ##print('hits proper limit')'''
  
  def set_bb(self, val):
    self.bb += val 
    self.set_pa(val)
    #self._validate_update('pa', 'bb', val)
    #self._add_stat('bb', val, maximum=self.at_bat)
    '''if self.less_zero(self.bb, val):
      self.bb = 0
    else:
      self.bb += val
    '''
  def set_hbp(self, val):
    self.hbp += val
    self.set_pa(val)
    #self._validate_update('pa', 'hbp', val)
  
  def set_so(self, val):
    self.so += val 
    self.set_pa(val)
    self.set_at_bat(val)
    #self._validate_update('at_bat', 'so', val)
  
  def set_put_out(self, val):
    self.put_out += val 
    self.set_pa(val)
    self.set_at_bat(val)
    #self._validate_update('at_bat', 'so', val)
  
  def set_hr(self, val):
    self._validate_update('hit', 'hr', val)
    #self._add_stat('hr', val, maximum=self.at_bat)
    '''if self.less_zero(self.hr, val):
      self.hr = 0
    else:
      self.hr += val'''

  def set_rbi(self, val):
    #self._validate_update('at_bat', 'hit', val)
    #self._add_stat('rbi', val, maximum=self.at_bat)
    if self.less_zero(self.rbi, val):
      self.rbi = 0
    elif self.at_bat > 0:
       self.rbi += val
    '''if self.less_zero(self.rbi, val):
      self.rbi = 0
    else:
      self.rbi += val'''
  
  def set_runs(self, val):
    #self._validate_update('hit', 'runs', val)
    #self._add_stat('runs', val)
    if self.less_zero(self.runs, val):
      self.runs = 0
    elif self.at_bat > 0:
       self.runs += val

  def set_sac_fly(self, val):
    self.sac_fly += val 
    self.set_pa(val)
    #self._validate_update('pa', 'sac_fly', val)
    #self._add_stat('sac_fly', val, maximum=self.at_bat)
    '''if self.less_zero(self.sac_fly, val):
      self.sac_fly = 0
    else:
      self.sac_fly += val'''
  
  def set_fielder_choice(self, val):
    self.fielder_choice += val 
    self.set_pa(val)

  def set_singles(self, val):
    self._validate_update('hit', 'singles', val)
    #self._add_stat('singles', val, maximum=self.hit)
    '''if self.less_zero(self.singles, val):
      self.singles = 0
    else:
      self.singles += val
    '''
  def set_doubles(self, val):
    self._validate_update('hit', 'doubles', val)
    #self._add_stat('doubles', val, maximum=self.hit)
    '''if self.less_zero(self.doubles, val):
      self.doubles = 0
    else:
      self.doubles += val '''
  
  def set_triples(self, val):
    self._validate_update('hit', 'triples', val)
    #self._add_stat('triples', val, maximum=self.hit)
    '''if self.less_zero(self.triples, val):
      self.triples = 0
    else:
      self.triples += val'''
  
  def set_AVG(self):              self.AVG = self.calc_AVG()
  
  def set_BABIP(self):            self.BABIP = self.calc_BABIP()

  def set_SLG(self):              self.SLG = self.calc_SLG()
  
  def set_ISO(self):              self.ISO = self.calc_ISO()

  def set_OBP(self):              self.OBP = self.calc_OBP()

    # ---------------------------------------------------------------------------------- #
    # calc functions
  
  def calc_OBP(self): 
    # (Hits + Walks + Hit By Pitch) / (At Bats + Walks + Hit By Pitch + Sacrifice Flies)
    ret = 0
    if self.pa == 0 or self.at_bat == 0:
      return self.format_decimal(ret)
    elif (self.at_bat + self.bb + self.hbp + self.sac_fly) == 0:
      return self.format_decimal(ret)
    ret = (self.hit + self.bb + self.hbp) / (self.at_bat + self.bb + self.hbp + self.sac_fly)
    return self.format_decimal(ret)
  
  def calc_BABIP(self):
    #(H - HR)/(AB - K - HR + SF)
    ret = 0
    if self.at_bat - self.so - self.hr + self.sac_fly <= 0:
      return self.format_decimal(ret)
    ret = (self.hit - self.hr)/(self.at_bat - self.so - self.hr + self.sac_fly)
    return self.format_decimal(ret)
    
  def calc_SLG(self):
    #(1B + 2Bx2 + 3Bx3 + HRx4)/AB
    ret = 0
    if self.at_bat == 0:
      return self.format_decimal(ret)
    ret = ( self.singles + (2 * self.doubles) + (3 * self.triples) + (4 * self.hr) ) / self.at_bat 
    return self.format_decimal(ret)
  
  def calc_AVG(self):
    ret = 0
    if self.hit == 0 or self.at_bat == 0:
      return self.format_decimal(ret)
    ret = self.hit / self.at_bat 
    return self.format_decimal(ret)
      
  def calc_ISO(self):
    #(1x2B + 2x3B + 3xHR) / At-bats OR Slugging percentage - Batting average
    ret = 0
    print('slg:', self.SLG)
    print('avg:', self.AVG)
    if self.at_bat == 0:
      return self.format_decimal(ret)
    if float(self.SLG) - float(self.AVG) > 0:
      ret = ( (1 * self.doubles) + (2 * self.triples) + (3 * self.hr ) ) / float(self.SLG) - float(self.AVG)
    return self.format_decimal(ret)

class Pitcher(Player):
  def __init__(self, name, number, team, league, positions=[], message=None):
    super().__init__(name, number, team, league, positions=[], message=None)
  
    # player pitcher gen attr
    self.name = name 
    self.number = number 
    self.team = team
    self.positions = positions
    self.message = message

    # pitching attr
    self.wins = 0 
    self.losses = 0 
    self.era = 0 
    self.games_played = 0 

    # to incorporate ...
    self.games_started = 0 
    self.games_completed = 0 
    self.shutouts = 0 
    self.saves = 0 
    self.save_ops = 0
    self.ip = 0 
    self.p_at_bats = 0
    self.p_hits = 0 
    self.p_runs = 0
    self.er = 0 
    self.p_hr = 0 
    self.p_hb = 0 
    self.p_bb = 0 
    self.p_so = 0 
    self.WHIP = 0 
    self.p_avg = 0 
    self.k_9 = 0 
    self.bb_9 = 0 
  
  def __str__(self):
    ret = f'Name: {self.name}\nNumber: {self.number}\nPrimary Position: {self.positions[0]}\nSecondary Positions: {self.positions[1:]}\n'
    ret += f'Offense: ----- -----\n Plate Appearance: {self.pa}\nAt Bats: {self.at_bat}\n Hits: {self.hit}\n Walks: {self.bb}\n SO: {self.so}\n Put Out: {self.put_out}\n HR: {self.hr}\n'
    ret += f' Runs: {self.runs}\n RBI: {self.rbi}\n OBP: {self.OBP}\nBABIP: {self.BABIP}\n SLG: {self.SLG}\n AVG: {self.AVG}\n ISO: {self.ISO}\n' 
    ret += f'Pitching: ----- -----\n Wins: {self.wins}\n Losses: {self.losses}\n G: {self.games_played}\n ERA: {self.era}\n'
    ret += f' IP: {self.ip}\n At Bats: {self.p_at_bats}\n SO: {self.p_so}\n BB: {self.p_bb}\n AVG: {self.p_avg}\n WHIP: {self.WHIP}\n K9: {self.k_9}\n BB9: {self.bb_9}'
    return ret

  # -------- Validation Utilities --------

  def _show_error(self, message):
      #QMessageBox.warning(self.parent, "Input Error", message)
      #print('show error - msg inst', self.message)
      self.message.show_message(message)

  
  
  def _validate_not_exceed(self, val, stat_name, limit):
    if getattr(self, stat_name) + val > limit:
        self._show_error(f"{stat_name.replace('_', ' ').capitalize()} cannot exceed {limit}.")
        return False
    return True

  def _validate_combined_limit(self, val, stat_names, limit, combined_label="Combined stats"):
    current_total = sum(getattr(self, stat) for stat in stat_names)
    if current_total + val > limit:
        self._show_error(f"{combined_label} cannot exceed {limit}.")
        return False
    return True
  
  def _update_stat(self, val, attr_name, custom_validator=None):
    if self.less_zero(getattr(self, attr_name), val):
        self._show_error(f"{attr_name.replace('_', ' ').capitalize()} cannot go below zero.")
        return

    if custom_validator and not custom_validator(val):
        return

    setattr(self, attr_name, getattr(self, attr_name) + val)

  # -------- Game Logic --------

  '''def set_games_played(self, val):
      if self.less_zero(self.games_played, val):  
          return     
      self.games_played += val

  def set_wins(self, val):
      if self.less_zero(self.wins, val):  
          return 
      if self._validate_game_total(new_wins=val):
          self.wins += val

  def set_losses(self, val):
      if self.less_zero(self.losses, val):  
          return 
      if self._validate_game_total(new_losses=val):
          self.losses += val

  def set_games_started(self, val):
      if self.less_zero(self.games_started, val):  
          return 
      if self._validate_game_component(val, "games_started"):
          self.games_started += val

  def set_games_completed(self, val):
      if self.less_zero(self.games_completed, val):  
          return 
      if self._validate_game_component(val, "games_completed"):
          self.games_completed += val

  def set_shutouts(self, val):       self.shutouts += val
  def set_saves(self, val):          self.saves += val
  def set_save_ops(self, val):       self.save_ops += val
  def set_er(self, val):             self.er += val
  def set_ip(self, val):             self.ip += val
  def set_p_hits(self, val):         self.p_hits += val
  def set_p_bb(self, val):           self.p_bb += val
  def set_p_so(self, val):           self.p_so += val
  def set_p_at_bats(self, val):      self.p_at_bats += val
  def set_p_runs(self, val):         self.p_runs += val
  def set_p_hr(self, val):           self.p_hr += val
  def set_p_hb(self, val):           self.p_hb += val'''

  def set_wins(self, val):
      if self.games_played > 0 and (self.wins + self.losses) == self.games_played:
          #QMessageBox.warning(self.parent, "Input Error", "Update games played before wins and losses.")
          self.message.show_message("Update games played before wins and losses.")
          return 
      if (self.wins + val + self.losses) > self.games_played:
          #QMessageBox.warning(self.parent, "Input Error", "Wins - Losses do not match total games played.")
          self.message.show_message("Wins - Losses do not match total games played.")
          return 
      self.wins += val

  def set_losses(self, val):
      if self.games_played > 0 and (self.wins + self.losses) == self.games_played:
          #QMessageBox.warning(self.parent, "Input Error", "Update games played before wins and losses.")
          self.message.show_message("Update games played before wins and losses.")
          return
      if (self.wins + val + self.losses) > self.games_played:
          #QMessageBox.warning(self.parent, "Input Error", "Wins - Losses do not match total games played.")
          self.message.show_message("Wins - Losses do not match total games played.")
          return 
      self.losses += val

  def set_er(self, val):
      self._update_stat(val, 'er', lambda v: self._validate_not_exceed(v, 'er', self.p_at_bats))

  def set_ip(self, val):
      self._update_stat(val, 'ip', lambda v: self._validate_not_exceed(v, 'ip', 9 * self.games_played))

  def set_saves(self, val):
      self._update_stat(val, 'saves', lambda v: self._validate_not_exceed(v, 'saves', self.games_played))

  def set_save_ops(self, val):
      self._update_stat(val, 'save_ops', lambda v: self._validate_not_exceed(v, 'save_ops', self.games_played))
  
  def set_shutouts(self, val):
      self._update_stat(val, 'shutouts', lambda v: self._validate_not_exceed(v, 'shutouts', self.games_completed))
  
  def set_p_at_bats(self, val):
      if self.less_zero(self.p_at_bats, val):
         return 
      self.p_at_bats += val

  def set_p_runs(self, val):
      self._update_stat(val, 'p_runs', lambda v: self._validate_not_exceed(v, 'p_runs', self.p_at_bats))

  def set_p_hr(self, val):
      self._update_stat(val, 'p_hr', lambda v: self._validate_combined_limit(v, ['p_hits', 'p_bb', 'p_so', 'p_hr', 'p_hb'], self.p_at_bats))

  def set_p_bb(self, val):
      self._update_stat(val, 'p_bb', lambda v: self._validate_combined_limit(v, ['p_hits', 'p_bb', 'p_so', 'p_hr', 'p_hb'], self.p_at_bats))

  def set_p_hits(self, val):
      self._update_stat(val, 'p_hits', lambda v: self._validate_combined_limit(v, ['p_hits', 'p_bb', 'p_so', 'p_hr', 'p_hb'], self.p_at_bats))

  def set_p_so(self, val):
      self._update_stat(val, 'p_so', lambda v: self._validate_combined_limit(v, ['p_hits', 'p_bb', 'p_so', 'p_hr', 'p_hb'], self.p_at_bats))

  def set_p_hb(self, val):
      self._update_stat(val, 'p_hb', lambda v: self._validate_combined_limit(v, ['p_hits', 'p_bb', 'p_so', 'p_hr', 'p_hb'], self.p_at_bats))
  
  def set_games_played(self, val):
      if self.less_zero(self.games_played, val):
         return 
      self.games_played += val

  def set_games_started(self, val):
      self._update_stat(val, 'games_started', lambda v: self._validate_not_exceed(v, 'games_started', self.games_played))

  def set_games_completed(self, val):
    self._update_stat(val, 'games_completed', lambda v: self._validate_not_exceed(v, 'games_completed', self.games_played))  

  def set_p_avg(self):               self.p_avg = self.calc_p_avg()
  def set_k_9(self):                 self.k_9 = self.calc_k_9()
  def set_bb_9(self):                self.bb_9 = self.calc_bb_9()
  def set_WHIP(self):                self.WHIP = self.calc_WHIP()
  def set_era(self):                 self.era = self.calc_era()

  # -------- Calculations --------

  def calc_era(self):
      return self.format_decimal((self.er / self.ip) * 9) if self.ip else 0.000

  def calc_WHIP(self):
      return self.format_decimal((self.p_bb + self.p_hits) / self.ip) if self.ip else 0.000

  def calc_p_avg(self):
      return self.format_decimal(self.p_hits / self.p_at_bats) if self.p_at_bats else 0.000

  def calc_k_9(self):
      return self.format_decimal((self.p_so / self.ip) * 9) if self.ip else 0.000

  def calc_bb_9(self):
      return self.format_decimal((self.bb / self.ip) * 9) if self.ip else 0.000

  # -------- Getters --------

  def get_wins(self):         return self.wins
  def get_losses(self):       return self.losses
  def get_games_played(self): return self.games_played
  def get_era(self):          return self.era
  def get_p_at_bats(self):    return self.p_at_bats

  