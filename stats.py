# stats.py
# CS21 Concurrent Programming
# Final Project -- Snowfall
# Team Snowfall -- Stephanie Wilson, Rachel Bonanno, Justin Millette
# 4/28/2025
#
# This file defines a stats object to be used as part of the single point of 
# truth on the server-side during and after gameplay.

class Stats:
    def __init__(self, notes, max_combo, score):
        self.notes = notes
        self.max_combo = max_combo
        self.score = score
    
    @staticmethod
    def empty_stats():
        """ Creates a new stats object and initializes it to have zero everything. """
        return Stats(0, 0, 0)

    def update_max_combo(self, new_combo):
        """ Updates max combo if new combo is greater than current max. """
        if new_combo > self.max_combo:
            self.max_combo = new_combo

    

    