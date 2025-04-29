# gamestate.py
# CS21 Concurrent Programming
# Final Project -- Snowfall
# Team Snowfall -- Stephanie Wilson, Rachel Bonanno, Justin Millette
# 4/28/25
#
# This file defines a gamestate object that holds various information during 
# runtime of the game. The gamestate object owned by the server is a single-
# point-of-truth for this information, but instances of this are owned by 
# clients as well for ease of access.

import queue

class Gamestate:
    def __init__(self, notes, lanes_pressed, score, recent_id, 
                 recent_judgment, combo):
        self.notes = notes
        self.lanes_pressed = lanes_pressed
        self.score = score
        self.recent_id = recent_id
        self.outbox = queue.Queue()
        self.recent_judgment = recent_judgment
        self.combo = combo

    @staticmethod
    def empty_gamestate():
        """ Make a new gamestate object with empty values. """
        return Gamestate(notes=[], lanes_pressed=[], score=0, recent_id=None, 
                         recent_judgment=None, combo=0)

    def update_score(self, new_score): 
        """ Increases score by new_score. Always called under a lock. """
        self.score += new_score