import json
import threading

def better(judgment1, judgment2):
    judgments = ['No Credit', 'Poor', 'Fair', 'Good', 'Very Good', 'Excellent']
    return judgments.index(judgment1) > judgments.index(judgment2)

def calcscore(judgment):
    # scoring system
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
        print("parsing chart")
        with open(chartpath, 'r') as file:
            data = json.load(file)
        print(data)
        self.gamestate.notes = data # doesn't need to be locked as this is only done once

    def receive_score(self, note_id, judgment):
        print(f"Received score: {note_id}, {judgment}")
        score = calcscore(judgment)
        tellOtherPlayer = False
        with self.gamestatelock:
            # print(self.gamestate.notes)
            our_note = self.gamestate.notes['notes'][note_id]  # get the note from the gamestate
            print(f"our note: {our_note}, judgment: {judgment}, our judgment: {our_note['judgment']}")
            if judgment == 'No Credit' and our_note['judgment'] == 'No Credit': # case where both players miss
                print("!!!!!!!!!!!! in missed note case")
                # then we actually have a miss
                self.gamestate.combo = 0 # reset combo
                tellOtherPlayer = True    
            elif our_note['judgment'] == "" or our_note['judgment'] == 'No Credit': # case where we have a first time note from first player
                # when we get a first time note from first player - scoring when there's no score yet
                our_note['judgment'] = judgment
                self.gamestate.update_score(score)
                self.gamestate.combo += 1
                self.stats.update_max_combo(self.gamestate.combo)
                tellOtherPlayer = True
            # else we don't do anything and we don't need to inform anyone
        print(f"new score: {self.gamestate.score}, new combo: {self.gamestate.combo}")
        return tellOtherPlayer




# each tick (we expect that ticks are fast enough that scoring accuracy is doable):
# merge these into server Gamestate – this should only affect lane states
# check if there’s a note near enough to the judgment line to score it, if lane state for that note is pressed:
# score accuracy if there is one
# Logs stats (accuracy of note, new best combo)
# Update game state (new score, new accuracy as most recent judgment, new current combo)
# Get new timestamp and send gamestate object to each connected client 
# 		After gameplay, send Stats object to connected clients, and await inputs for a new game
