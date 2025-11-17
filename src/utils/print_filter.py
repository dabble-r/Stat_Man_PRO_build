# Silence all print statements unless STATMANG_DEBUG=1 is set
import os
import sys

# --------------------------------------------------
def mute_print():
  try:
      if os.environ.get("STATMANG_DEBUG", "0") != "1":
          import builtins
          builtins.print = lambda *args, **kwargs: None
  except Exception:
      pass
