# exact copy of Player 
# to refacto as Game instance 
# 
class Game():
  """Lightweight game container for lineups, positions, and basic game metadata."""
  def __init__(self, team='Team', parent=None):
    self.team = team
    self.opponent = 'Opponent'
    self.season = None
    self.date = None 
    self.score = 0 
    self.winner = None
    self.loser = None
    self.lineups = [
      {
        f'{self.team}': 
        {
        '1': None,
        "2": None, 
        "3": None, 
        "4": None, 
        "5": None, 
        "6": None, 
        "7": None, 
        "8": None, 
        "9": None
        }  
      },
      {
        f'{self.opponent}': 
        {
        '1': None,
        "2": None, 
        "3": None, 
        "4": None, 
        "5": None, 
        "6": None, 
        "7": None, 
        "8": None, 
        "9": None
        }  
      }
    ]
    self.positions = [
      { 
        f'{self.team}':
        {
        'pitcher': None,
        'catcher': None,
        'first base': None,
        'second base': None,
        'third base': None,
        'shortstop': None,
        'left field': None,
        'center field': None,
        'right field': None
        }
      },
      {
        f'{self.opponent}':
        {
        'pitcher': None,
        'catcher': None,
        'first base': None,
        'second base': None,
        'third base': None,
        'shortstop': None,
        'left field': None,
        'center field': None,
        'right field': None
        }
      }
    ] 
  
    # message box self 
    self.parent = parent

  def __str__(self):
    """Return a short printable summary of the current game context."""
    ret = '' 
    ret += f"Game: {self.team} vs. {self.opponent}\nScore: {self.score}\nSeason: {self.season}\nDate: {self.date}\n\n"
    return ret
  
  '''def format_player(self, raw_lst):
    team = raw_lst[0]
    name = raw_lst[1]
    number = raw_lst[2]
    #avg = self.AVG
    positions = raw_lst[3:]
    ##print(raw_lst)
    ##print('team', team)
    ##print('name', name)
    ##print('number', number)
    new_player = Game(name, number, team, positions)
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
      QMessageBox.warning(self.parent, "Stat Input Error", message)

  def _get_attrs(self):
      directory = dir(self)
      ret = []
      for el in directory:
        temp = getattr(self, el)
        if isinstance(temp, (int)):
            ##print(temp, el)
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
    curr = getattr(self, stat)
    ##print('curr:', curr)
    total = self._get_max(update)
    ##print('new:', new)
    new_total = total + val
    if new_total > curr:
        ##print('invalid stat update')
        self._warn(f"{update.capitalize()} update total cannot exceed {stat.capitalize()} {curr}.")
    else:
        #print('valid stat update')
        setattr(self, update, new_total)
    
    # ------------------------------------------------------------------------ #
    # getters 

  def get_at_bat(self):                 return self.at_bat 
  
  def get_BABIP(self):                  return self.BABIP
  
  def get_SLG(self):                    return self.SLG
  
  def get_AVG(self):                    return self.AVG

  def get_ISO(self):                    return self.ISO 

    # ------------------------------------------------------------------------ #
    # setters 

  def set_at_bat(self, val):
    self.at_bat += val
    #self._add_stat('at_bat', val)
    #if self.at_bat + val < 0:
      self.at_bat = 0
    else:
      #print('type val - at bat', type(val))
      self.at_bat += val
        
  def set_hit(self, val):
    self._validate_update('at_bat', 'hit', val)

    #self._add_stat('hit', val, maximum=self.at_bat)

    #if self.at_bat == 0:
      self.hit = 0
    elif self.hit > self.at_bat:
      #print('excess hits')
    else:
      self.hit += val
      #print('hits proper limit
  
  def set_bb(self, val):
    self._validate_update('hit', 'bb', val)
    #self._add_stat('bb', val, maximum=self.at_bat)
    #if self.less_zero(self.bb, val):
      self.bb = 0
    else:
      self.bb += val
  
  def set_so(self, val):
    if self.less_zero(self.so, val):
      self.so = 0
    else:
      self.so += val
  
  def set_hr(self, val):
    self._validate_update('hit', 'hr', val)
    #self._add_stat('hr', val, maximum=self.at_bat)
    #if self.less_zero(self.hr, val):
      self.hr = 0
    else:
      self.hr += val

  def set_rbi(self, val):
    #self._validate_update('at_bat', 'hit', val)
    #self._add_stat('rbi', val, maximum=self.at_bat)
    if self.less_zero(self.rbi, val):
      self.rbi = 0
    elif self.at_bat > 0:
       self.rbi += val
    #if self.less_zero(self.rbi, val):
      self.rbi = 0
    else:
      self.rbi += val
  
  def set_runs(self, val):
    #self._validate_update('hit', 'runs', val)
    #self._add_stat('runs', val)
    if self.less_zero(self.runs, val):
      self.runs = 0
    elif self.at_bat > 0:
       self.runs += val

  def set_sac_fly(self, val):
    self._validate_update('hit', 'sac_fly', val)
    #self._add_stat('sac_fly', val, maximum=self.at_bat)
    #if self.less_zero(self.sac_fly, val):
      #self.sac_fly = 0
    #else:
      #self.sac_fly += val

  def set_singles(self, val):
    self._validate_update('hit', 'singles', val)
    #self._add_stat('singles', val, maximum=self.hit)
    #if self.less_zero(self.singles, val):
      #self.singles = 0
    #else:
      #self.singles += val
  
  def set_doubles(self, val):
    self._validate_update('hit', 'doubles', val)
    #self._add_stat('doubles', val, maximum=self.hit)
    #if self.less_zero(self.doubles, val):
      #self.doubles = 0
    #else:
      #self.doubles += val
  
  def set_triples(self, val):
    self._validate_update('hit', 'triples', val)
    #self._add_stat('triples', val, maximum=self.hit)
    #if self.less_zero(self.triples, val):
      self.triples = 0
    else:
      self.triples += val#
  
  def set_AVG(self):              self.AVG = self.calc_AVG()
  
  def set_BABIP(self):            self.BABIP = self.calc_BABIP()

  def set_SLG(self):              self.SLG = self.calc_SLG()
  
  def set_ISO(self):              self.ISO = self.calc_ISO()

    # ---------------------------------------------------------------------------------- #
    # calc functions
  
  def calc_BABIP(self):
    #(H - HR)/(AB - K - HR + SF)
    ret = 0
    if self.at_bat == 0:
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
    elif self.at_bat > 0 and self.hit <= self.at_bat:
      if (self.hit / self.at_bat) < 0:
        return self.format_decimal(ret)
      ##print(self.at_bat, self.hit)
      ret = self.hit / self.at_bat 
      return self.format_decimal(ret)
      
  def calc_ISO(self):
    #(1x2B + 2x3B + 3xHR) / At-bats OR Slugging percentage - Batting average
    ret = 0
    ##print('slg:', self.SLG)
    ##print('avg:', self.AVG)
    if self.at_bat == 0:
      return self.format_decimal(ret)
    if float(self.SLG) - float(self.AVG) > 0:
      ret = ( (1 * self.doubles) + (2 * self.triples) + (3 * self.hr ) ) / float(self.SLG) - float(self.AVG)
    return self.format_decimal(ret)
'''