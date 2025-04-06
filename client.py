class Client:
    def __init__(self, name, gamestate, stats, server):
        self.name = name
        self.gamestate = gamestate
        self.stats = stats
        self.server = server

    def client_loop():
        # each tick, receive new gamestate from server
        # then display information to the screen
        # then check if there's input from the player