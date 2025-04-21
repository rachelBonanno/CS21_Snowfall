class Gamestate:
    def __init__(self, notes, lanes_pressed, score, recent_id, recent_judgment, combo):
        self.notes = notes

        self.lanes_pressed = lanes_pressed
        self.score = score
        self.recent_id = recent_id
        self.recent_judgment = recent_judgment
        self.combo = combo

    @staticmethod
    def empty_gamestate():
        return Gamestate(notes=[], lanes_pressed=[], score=0, recent_id=None, recent_judgment=None, combo=0)

    def get_note_with_id(self, id):
        for note in self.notes:
            if note.id == id:
                return note
        return None

    def update_score(self, new_score):
        self.score = new_score