import pygame
import time
import json

def parse_chart(filepath):
        with open(filepath, 'r') as file:
            data = json.load(file)
        return data

def norman(acc):
    realacc = abs(acc - 1)
    if realacc <= 0.05:
        return "Excellent"
    elif realacc <= 0.15:
        return "Very Good"
    elif realacc <= 0.25:
        return "Good"
    elif realacc <= 0.35:
        return "Fair"
    elif realacc <= 0.45:
        return "Poor"
    else:
        return "No Credit"

def accuracy(note, currenttime, key):
    if note['lane'] != key:
        return 0
    if currenttime - note['time'] < 0:
        return 0
    else:
        return 1 - (currenttime - (note['time'] + 600)) / 1000 # + 600 for judgment window
    # figure out delay

class Client:
    def __init__(self, name, gamestate, stats, starttime):
        self.name = name
        self.gamestate = gamestate
        self.stats = stats
        self.starttime = starttime

    def client_init(self):
        while time.time() < self.starttime:
            time.sleep(0.01)
        pygame.init()
        self.screen = pygame.display.set_mode((1080, 720))
        pygame.display.set_caption(f"Game: {self.name}")
        self.notes = parse_chart('./charts/basic.chart')
        print(self.notes)
        self.client_loop()


    def client_loop(self):
        while True:
            note_queue = {1: [], 2: [], 3: [], 4: [], 5: [], 6: [], 7: [], 8: []}
            elapsed_time = 1000 * (time.time() - self.starttime)
            for note in self.notes['notes']:
                if note['judgment'] != "":
                    continue
                y_position = 0
                note_time = note['time']
                if elapsed_time >= note_time:
                    lane = note['lane']
                    x_position = lane * 100 + 100
                    y_position = (elapsed_time - note_time) * 1  # Adjust speed as needed
                    if y_position > 500 and y_position < 800:
                        note_queue[note['lane']].append(note) # okay, the note is hittable now
                    pygame.draw.circle(self.screen, (255, 255, 255), (x_position, int(y_position)), 10)
                if y_position > 700:
                    print('miss')
                    self.gamestate.recent_id = note['id']
                    self.gamestate.recent_judgment = "No Credit"
                    note['judgment'] = self.gamestate.recent_judgment
            
            for event in pygame.event.get():
                key = 0
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_q:
                        key = 1
                    elif event.key == pygame.K_w:
                        key = 2
                    elif event.key == pygame.K_e:
                        key = 3
                    elif event.key == pygame.K_r:
                        key = 4
                    elif event.key == pygame.K_o:
                        key = 5
                    elif event.key == pygame.K_p:
                        key = 6
                    elif event.key == pygame.K_LEFTBRACKET:
                        key = 7
                    elif event.key == pygame.K_RIGHTBRACKET:
                        key = 8
                    if 1 <= key <= 8:
                        curnotes = list(note_queue[key])
                        print(curnotes)
                        try:
                            current_note = curnotes[0]
                        except IndexError:
                            continue # player hit wrong key, nws tho
                        acc = accuracy(current_note, elapsed_time, key)
                        self.gamestate.recent_judgment = norman(acc)
                        self.gamestate.recent_id = current_note['id']
                        if acc > 0:
                            current_note['judgment'] = self.gamestate.recent_judgment
                        print(current_note)

                if event.type == pygame.QUIT:
                    pygame.quit()
                    return
            font = pygame.font.Font(None, 36)
            text = font.render(self.gamestate.recent_judgment, True, (255, 255, 255))
            self.screen.blit(text, (50, 50))
            pygame.display.flip()
            self.screen.fill((0, 0, 0))  # Clear the screen
            # print("wahoo")
            
            pygame.draw.line(self.screen, (255, 255, 255), (0, 600), (1080, 600), 5)