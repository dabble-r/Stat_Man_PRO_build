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
  
 