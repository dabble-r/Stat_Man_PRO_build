class Undo:
    def __init__(self, stack, league):
        """Undo helper that reverts the last action recorded in the provided stack."""
        self.stack = stack
        self.league = league

    def undo_exp(self, message=None):
        """Pop and revert the last stack action by restoring previous values/structures."""
        if self.stack.is_empty():
            return

        last_action = self.stack.get_last()
        obj, team, stat, prev, func, flag, player = last_action

        if stat == 'lineup':
            key = prev[0]
            value = prev[1]
            obj.lineup[key] = value
            # print('undo:', obj.lineup)

        elif stat == 'positions':
            key = prev[0]
            value = prev[1]
            obj.positions[key] = value
            # print('undo:', obj.positions)

        else:
            # print('setattr - undo:', obj, stat, prev)
            if isinstance(stat, list):
                pa = ab = statType = None

                if len(stat) == 3:
                    pa, val, statType = stat
                    # print("len 3: ", pa, statType, prev)
                    currPA = getattr(obj, pa)

                    # Validation: prevent undo if PA is 0 (would make it negative)
                    if currPA == 0:
                        if message is not None:
                            message.show_message("Player at bat and pa are 0", btns_flag=False, timeout_ms=2000)
                        return

                    print("curr pa: ", currPA, prev, currPA - prev)
                    paUpdate = currPA - val

                    setattr(obj, pa, paUpdate)
                    setattr(obj, statType, prev)

                elif len(stat) == 4:
                    pa, ab, val, statType = stat
                    # print("len 4: ", pa, ab, val, statType)
                    currAB = getattr(obj, ab)
                    currPA = getattr(obj, pa)

                    # Validation: prevent undo if PA or AB is 0 (would make it negative)
                    if currPA == 0 or currAB == 0:
                        if message is not None:
                            message.show_message("Player at bat and pa are 0", btns_flag=False, timeout_ms=2000)
                        return

                    paUpdate = currPA - val
                    abUpdate = currAB - val

                    setattr(obj, pa, paUpdate)
                    setattr(obj, ab, abUpdate)
                    setattr(obj, statType, prev)

            else:
                setattr(obj, stat, prev)
                # print(team, stat, prev, func, flag, player)

        self.stack.remove_last()