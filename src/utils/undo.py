class Undo():
  def __init__(self, stack, league):
    """Undo helper that reverts the last action recorded in the provided stack."""
    self.stack = stack
    self.league = league
  
  def undo_exp(self):
    """Pop and revert the last stack action by restoring previous values/structures."""
    if self.stack.is_empty():
      return 
  
    last_action = self.stack.get_last()
    obj, team, stat, prev, func, flag, player = last_action
    
    if stat == 'lineup':
      key = prev[0]
      value = prev[1]
      obj.lineup[key] = value 
      #print('undo:', obj.lineup)
    
    elif stat == 'positions':
      key = prev[0]
      value = prev[1]
      obj.positions[key] = value 
      #print('undo:', obj.positions)
    
    else:
      #print('setattr - undo:', obj, stat, prev)
      if type(stat) == list:
        pa = ab = statType = None

        if len(stat) == 3:
          pa, val, statType = stat  
          #print("len 2: ", pa, statType, prev)
          currPA = getattr(obj, pa)
          print("curr pa: ", currPA, prev, currPA-prev)
          paUpdate = currPA - val

          setattr(obj, pa, paUpdate)
          setattr(obj, statType, prev)

        elif len(stat) == 4:
          pa, ab, val, statType = stat
          print("len 3: ", pa, ab, val, statType)
          currAB = getattr(obj, ab)
          currPA = getattr(obj, pa)
          paUpdate = currPA - val
          abUpdate = currAB - val

          setattr(obj, pa, paUpdate)
          setattr(obj, ab, abUpdate)
          setattr(obj, statType, prev)

      else:

        setattr(obj, stat, prev)


        #print(team, stat, prev, func, flag, player)

    self.stack.remove_last()
    

  