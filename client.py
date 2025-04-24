import pygame
import time
import json

JUDGE_Y = 600
SPEED = 1

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
        return 1 - (currenttime - (note['time'] + JUDGE_Y)) / 1000 # + JUDGE_Y for judgment window
    # figure out delay

class Client:
    def __init__(self, name, gamestate, stats, starttime):
        self.name = name
        self.gamestate = gamestate
        self.stats = stats
        self.starttime = starttime
        self.server_socket = None # Will be set from the main client script
        self.active_holds = {}
        self.release_window = 0.15 # should probably be a global but I CBA

    def receive_hit_confirmation(self, note_id, judgment): 
        """ This is where we actually record that a note was hit, so it stops
        being drawn on the screen. This is called from snowfall_client when it
        receives a message from the server indicating that a note was hit. """
        print(f"Received hit confirmation: {note_id}, {judgment}")
        self.gamestate.notes['notes'][note_id]['judgment'] = judgment # set the judgment of the note to the one we received


    def set_socket(self, server_socket):
        self.server_socket = server_socket

    def client_init(self):
        while time.time() < self.starttime:
            time.sleep(0.01)
        pygame.init()
        self.screen = pygame.display.set_mode((1080, 720))
        pygame.display.set_caption(f"Game: {self.name}")
        self.gamestate.notes = parse_chart('./charts/basic.chart')
        for note in self.gamestate.notes['notes']:

            # flags used only at runtime
            note['holding']   = False      # latch state for holds
            note['completed'] = False 
        print(self.gamestate.notes)
        return self.client_loop()


    def client_loop(self):
        while True:
            note_queue = {1: [], 2: [], 3: [], 4: [], 5: [], 6: [], 7: [], 8: []}
            elapsed_time = 1000 * (time.time() - self.starttime)
            for note in self.gamestate.notes['notes']:
                if note['judgment'] != "":
                    # print(f"should stop drawing {note['id']} bc it has judgment {note['judgment']}")
                    continue
                y_position = 0
                note_time = note['time']
                if elapsed_time >= note_time:
                    lane = note['lane']
                    x_position = lane * 100 + 100
                    y_position = (elapsed_time - note_time) * SPEED  
                    if y_position > 400 and y_position < 800:
                        note_queue[note['lane']].append(note) # okay, the note is hittable now
                    
                    if note['duration'] > 0:                                # HOLD NOTE
                        # total length in pixels
                        total_tail_px = note['duration'] * SPEED

                        # how far the head has travelled so far
                        travelled_px  = (elapsed_time - note['time']) * SPEED

                        # --- HEAD POSITION ----------------------------------------------------
                        if note['holding'] and not note['completed']:
                            head_y = JUDGE_Y              # freeze on the judgment line
                            draw_head = False             # hide the head while holding
                            # While the player is holding, the body should shrink, so the
                            # amount of tail that is still visible is:
                            remaining_tail_px = max(0, total_tail_px - (travelled_px - JUDGE_Y))
                        else:
                            head_y = travelled_px         # still falling
                            draw_head = True
                            remaining_tail_px = max(0, total_tail_px - travelled_px)

                        # --- BODY RECTANGLE ---------------------------------------------------
                        # The rectangle starts at the top of the still-visible tail
                        top_y = head_y - remaining_tail_px
                        rect_h = remaining_tail_px        # height of the visible body

                        if rect_h > 0:
                            pygame.draw.rect(
                                self.screen,
                                (150, 150, 255),          # light blue body
                                pygame.Rect(x_position - 7, int(top_y), 14, int(rect_h))
                            )

                        # --- OPTIONAL HEAD ----------------------------------------------------
                        if draw_head:
                            pygame.draw.circle(
                                self.screen,
                                (255, 255, 255),
                                (x_position, int(head_y)),
                                10
                            )
                    else: # not held note
                        pygame.draw.circle(self.screen, (255, 255, 255), (x_position, int(y_position)), 10)
                if y_position > 700 and note['duration'] == 0 and note['holding'] == False:
                    # print('miss')
                    self.gamestate.recent_id = note['id']
                    self.gamestate.recent_judgment = "No Credit"
                if note['duration'] > 0 and not note['completed']:
                    tail_time = note['time'] + note['duration'] + JUDGE_Y  # same JUDGE_Y ms leniency
                    if elapsed_time > tail_time:
                        note['judgment'] = "No Credit"
                        note['completed'] = True
                        self.gamestate.recent_id       = note['id']
                        self.gamestate.recent_judgment = "No Credit"
                        self.active_holds.pop(note['lane'], None)      # if we were still holding
            
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
                        curnotes = [n for n in note_queue[key] if n['judgment'] == ""] # list(note_queue[key])
                        print(curnotes)
                        if not curnotes:
                            continue # ignore stray hits
                        current_note = curnotes[0]
                        acc = accuracy(current_note, elapsed_time, key)
                        judgment = norman(acc)
                        if current_note['duration'] == 0:
                            self.gamestate.recent_judgment = judgment
                            self.gamestate.recent_id = current_note['id']
                        else:
                            if acc > 0:
                                current_note['holding'] = True
                                self.active_holds[key] = current_note
                        print(current_note)
                elif event.type == pygame.KEYUP:
                    lane = {
                        pygame.K_q:1, pygame.K_w:2, pygame.K_e:3, pygame.K_r:4,
                        pygame.K_o:5, pygame.K_p:6, pygame.K_LEFTBRACKET:7, pygame.K_RIGHTBRACKET:8
                    }.get(event.key, 0)

                    note = self.active_holds.pop(lane, None)
                    if note and not note['completed']:
                        tail_time = note['time'] + note['duration']
                        late_by = elapsed_time - tail_time
                        if late_by <= self.release_window * 1000:
                            j = norman(1 - late_by/1000)
                        else:
                            j = "No Credit"

                        note['completed'] = True
                        self.gamestate.recent_id = note['id']
                        self.gamestate.recent_judgment = j

                if event.type == pygame.QUIT or elapsed_time >= self.gamestate.notes['end']:
                    pygame.quit()
                    return True
                
            # Example: Send a message periodically from the Pygame loop (optional now)
            # if self.server_socket and int(round(time.time() * 1000)) % 1000 == 0:
            #     message = "Hello from Pygame".encode('utf-8')
            #     try:
            #         self.server_socket.sendall(struct.pack("!I", len(message)))
            #         self.server_socket.sendall(message)
            #     except socket.error as e:
            #         print(f"{self.name}: Error sending from Pygame: {e}")
            
            font = pygame.font.Font(None, 36)
            
            # judgement logic here 
            text = font.render(self.gamestate.recent_judgment, True, (255, 255, 255))
            self.screen.blit(text, (50, 50))
            pygame.display.flip()
            self.screen.fill((0, 0, 0))  # Clear the screen
            # print("wahoo")
            
            pygame.draw.line(self.screen, (255, 255, 255), (0, JUDGE_Y), (1080, JUDGE_Y), 5)
            time.sleep(0.016) # Limit frame rate