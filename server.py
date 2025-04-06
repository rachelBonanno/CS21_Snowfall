import json
import threading

def better(judgment1, judgment2):
    judgments = ['No Credit', 'Poor', 'Fair', 'Good', 'Very Good', 'Excellent']
    return judgments.index(judgment1) > judgments.index(judgment2)

class Server:
    def __init__(self, stats, gamestate):
        self.stats = stats # only display at end of song
        self.gamestate = gamestate
        self.gamestatelock = threading.Lock() # lock for gamestate

    def parse_chart(self, chartpath):
        with open(chartpath, 'r') as file:
            data = json.load(file)
        self.gamestate.notes = data # doesn't need to be locked as this is only done once

    def receive_score(self, note):
        score = score(note['judgment'])
        with self.gamestatelock:
            our_note = self.gamestate.notes[note['id']] # get the note from the gamestate

            if note['judgment'] == 'No Credit' and our_note['judgment'] == 'No Credit':
                # then we actually have a miss
                self.gamestate.combo = 0 # reset combo
                
            # after we get the note from the second player
            if better(note['judgement'], our_note['id']['judgement']): # scoring when there's already a score
                # if our new judgment is better than the previous one, update it
                our_note['id']['judgement'] = note['judgement']
                # account for judgements from both players, takes the higher onee nd adds to score
                self.gamestate.update_score(score - score(our_note['id']['judgement'])) # update score with the new judgment
                self.gamestate.combo += 1 # increment combo
            else:
                # if our new judgment is worse, we don't need to update it
                return
                
            # when we get a first time note from first player - scoring when there's no score yet
            our_note['id']['judgement'] = note['judgment']
            self.gamestate.update_score(score)
            self.gamestate.combo += 1
            self.stats.update_max_combo(pState.combo)




# each tick (we expect that ticks are fast enough that scoring accuracy is doable):
# merge these into server Gamestate – this should only affect lane states
# check if there’s a note near enough to the judgment line to score it, if lane state for that note is pressed:
# score accuracy if there is one
# Logs stats (accuracy of note, new best combo)
# Update game state (new score, new accuracy as most recent judgment, new current combo)
# Get new timestamp and send gamestate object to each connected client 
# 		After gameplay, send Stats object to connected clients, and await inputs for a new game
