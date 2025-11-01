import math
from src.core.node import NodeStack


class Stack():
  """Simple LIFO stack of stat-change nodes for undo operations."""
  def __init__(self):
    self.name = "Undo Stat Stack"
    self.lst = []
    
  def __str__(self):
    ret = ''
    if self.is_empty():
      ret = 'Stack Empty'
      return ret
    for indx, node in enumerate(self.lst):
      ret += f"{indx+1}:  Obj: {node.name} - Stat: {node.stat} - L: {node.prev}\n\n" 
    return ret
  
  def is_empty(self):
    """Return True when the stack has no nodes."""
    return len(self.lst) == 0
    #return self.head is None
  
  def get_size(self):
    """Return current number of nodes in the stack."""
    return len(self.lst)
  
  def get_first(self):
    """Return earliest pushed node or None if empty."""
    if self.is_empty():
      return None
    return self.lst[0]
  
  def get_last(self):
    """Return most recently pushed node or None if empty."""
    if self.is_empty():
      return None
    last = self.lst[-1]
    return last
  
  def get_second_last(self):
    """Return node before the top if present; else None."""
    if self.is_empty():
      return None 
    if len(self.lst) >= 2:
      return self.lst[-2]
    
  def add_node(self, obj, team, stat, prev, func, flag, player=None):
    """Push a new NodeStack with context needed to undo a stat change."""
    new_node = NodeStack(obj, team, stat, prev, func, flag, player=None)
    self.lst.append(new_node)
  
  def remove_last(self):
    """Pop the top node if stack is non-empty."""
    if self.is_empty():
      return 
    self.lst.pop()
  

class InstanceStack():
    """Queue of DB rows grouped by table, building typed instances for GUI loads."""
    def __init__(self):
        self.name = "Instance Stack"
        self.instances = []
        self.rows = []
        self.values = []
        self.tables = []
        self.table_check = ["leagueID", "teamID", "playerID", "pitcherID"]
        
  
    def add(self, table_name, row, values):
      """Queue a row definition and aligned values for later instance building."""
      self.tables.append(table_name)
      self.rows.append(row)
      self.values.append(values) 

    def popRow(self):
        """Remove last queued row schema."""
        self.rows.pop()
    
    def popValue(self):
        """Remove last queued row values."""
        self.values.pop()
  
    def popTable(self):
      """Remove last queued table name."""
      self.tables.pop()

    def peek(self):
        """Return first constructed instance without removing it."""
        return self.instances[0]
    
    def get_length(self):
        """Return number of constructed instances."""
        return len(self.instances)
    
    def isEmpty(self):
        """Return True if no constructed instances are present."""
        return len(self.instances) == 0 
    
    def topRow(self):
        """Return last queued row schema dict."""
        top = self.rows[-1]
        return top 
    
    def topValue(self):
        """Return last queued values list aligned with schema."""
        top = self.values[-1]
        return top
    
    def getTable(self):
      """Return last queued table name or None if empty."""
      if len(self.tables) == 0:
          return None
      return self.tables[-1]
    
    def getType(self):
      """Classify the queued row by table and store zipped pairs in order."""
      table_name = self.getTable()
      value_hint = self.topValue()
      # zip keys in insertion order with aligned values list
      zipped = list(zip(self.topRow().keys(), value_hint))
      temp = {}
      if table_name == "league":
          temp['league'] = zipped
          self.instances.insert(0, temp)
      elif table_name == "team":
          temp['team'] = zipped
          self.instances.insert(1, temp)
      elif table_name == "player":
          temp['player'] = zipped
          self.instances.append(temp)
      elif table_name == "pitcher":
          temp['pitcher'] = zipped
          self.instances.append(temp)
      self.popRow()
      self.popValue()
      self.popTable()

    def getLeague(self):
        pass 
    
    def getTeam(self):
        pass 
    
    def getPlayer(self):
        pass 
    
    def getPitcher(self):
        pass
    
    def getInstances(self):
        """Process all queued rows into typed instance dicts and return the list."""
        # process all queued rows into instances, stop if indeterminate
        guard = 0
        while len(self.rows) > 0 and len(self.values) > 0 and guard < 10000:
            hint = self.getTable()
            if hint is None:
                break
            self.getType()
            guard += 1
        return self.instances
        
        
            
        

    
        
    
      

    def load_all_to_gui(self, attrs, vals):
        lst_attr = [x for x in attrs]
        lst_vals = [x for x in vals]
        print("instance type: ", lst_attr[0])
        print("attrs for gui: ", lst_attr)
        print("vals for gui: ", lst_vals)


  