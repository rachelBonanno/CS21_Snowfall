class Stats:
    def __init__(self, notes, max_combo, score):
        self.notes = notes
        self.max_combo = max_combo
        self.score = score
    
    @staticmethod
    def empty_stats():
        return Stats(0, 0, 0)

    def update_max_combo(self, new_combo):
        if new_combo > self.max_combo:
            self.max_combo = new_combo

    

    