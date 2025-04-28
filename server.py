# server.py
# CS21 Concurrent Programming
# Final Project -- Snowfall
# Team Snowfall -- Stephanie Wilson, Rachel Bonanno, Justin Millette
# 4/28/25
#
# This file defines the server-side, gameplay-related logic during the runtime 
# of Snowfall. The main purpose of this is to handle note-hit messages, and 
# determine if that message needs to be passed back to the clients. This also
# handles chart file parsing on the server side.

import json
import threading

def better(judgment1, judgment2):
    """ Returns true if judgment1 is better than judgment2. E > VG > G > F > P > NC. """ 
    judgments = ['No Credit', 'Poor', 'Fair', 'Good', 'Very Good', 'Excellent']
    return judgments.index(judgment1) > judgments.index(judgment2)

def calcscore(judgment):
    """ Returns a number score to increment given a judgment string. """
    if judgment == 'No Credit':
        return 0
    elif judgment == 'Poor':
        return 100
    elif judgment == 'Fair':
        return 200
    elif judgment == 'Good':
        return 300
    elif judgment == 'Very Good':
        return 400
    elif judgment == 'Excellent':
        return 500
    else:
        raise ValueError("Invalid judgment value")

class Server:
    def __init__(self, stats, gamestate):
        self.stats = stats # only display at end of song
        self.gamestate = gamestate
        self.gamestatelock = threading.Lock() # lock for gamestate

    def parse_chart(self, chartpath):
        """ Turn chart at filepath into json object. """
        with open(chartpath, 'r', encoding="utf-8") as file: # encoding UTF-8 to handle weird outputs from chart conversion script
            data = json.load(file)
        print(f"Chart at {chartpath} loaded successfully!")
        with self.gamestatelock:
            self.gamestate.notes = data 

    def receive_score(self, note_id, judgment):
        """ Handle received score: update single point of truth gamestate, stats object. 
        Indicate if this information should be passed on to both clients. 
        We should do this if both clients scored NC on this note, or when the first client
        doesn't score NC. If we already have a non-NC judgment saved for a note, and we receive an
        NC judgment, we don't care."""
        score = calcscore(judgment) # assign points to the note for all of our very competitive players
        tellOtherPlayer = False # update if we should send 
        with self.gamestatelock: # both client listening threads could be here at the same time
            our_note = self.gamestate.notes['notes'][note_id]  # get the note from the gamestate
            if judgment == 'No Credit' and our_note['judgment'] == 'No Credit': # case where both players miss
                # then we actually have a miss
                self.gamestate.combo = 0 # reset combo
                tellOtherPlayer = True    
            elif our_note['judgment'] == "" or our_note['judgment'] == 'No Credit': # case where we have a first non-NC score
                # when we get a first time note from first player - scoring when there's no score yet
                our_note['judgment'] = judgment
                self.gamestate.update_score(score)
                if judgment != 'No Credit':
                    self.gamestate.combo += 1 # increment combo if the note was hit
                    self.stats.update_max_combo(self.gamestate.combo) # update max combo
                tellOtherPlayer = True
            # else we don't do anything and we don't need to inform anyone
        return tellOtherPlayer
