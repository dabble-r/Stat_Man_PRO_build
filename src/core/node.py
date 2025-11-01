
class Node():
  def __init__(self, team, next=None):
    self.team = team
    self.next = next

class NodeStack():
  def __init__(self, obj, name, stat, prev, func, flag, player=None):
    self.obj = obj
    self.name = name 
    self.stat = stat 
    self.prev = prev 
    self.func = func
    self.flag = flag
    self.player = player
  
  def __iter__(self):
    yield self.obj
    yield self.name 
    yield self.stat 
    yield self.prev
    yield self.func
    yield self.flag
    yield self.player