import pygame
import time
import json

JUDGE_Y = 615
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
                    x_position = (lane - 1) * 98 + 198

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

                        # --- BODY IMAGE ---------------------------------------------------
                        if rect_h > 0:
                            # Load the body image
                            body_image = pygame.image.load('./assets/long_p1.png')
                            body_width, body_height = body_image.get_size()

                            # Calculate how many times the body image needs to be repeated
                            num_repeats = int(rect_h / body_height) + 1

                            # Draw the body image repeatedly to fill the height
                            for i in range(num_repeats):
                                segment_y = int(top_y) + i * body_height
                                if segment_y + body_height > top_y + rect_h:
                                    # Clip the last segment if it exceeds the visible height
                                    clipped_body = pygame.Surface((body_width, int(top_y + rect_h - segment_y)), pygame.SRCALPHA)
                                    clipped_body.blit(body_image, (0, 0), (0, 0, body_width, int(top_y + rect_h - segment_y)))
                                    self.screen.blit(clipped_body, (x_position - 28, segment_y))
                                else:
                                    self.screen.blit(body_image, (x_position - 28, segment_y))

                        # --- HEAD IMAGE ---------------------------------------------------
                        if draw_head:
                            head_image = pygame.image.load('./assets/note_p1.png')
                            head_image = pygame.transform.scale(head_image, (64, 62)) 
                            self.screen.blit(head_image, (x_position - 32, int(head_y) - 31))
                    else: # not held note
                        # render note
                        note_image = pygame.image.load('./assets/note_p1.png')
                        note_image = pygame.transform.scale(note_image, (64, 62))  # Adjust size as needed
                        self.screen.blit(note_image, (x_position - 32, int(y_position) - 31)) 
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
                        key_image = pygame.image.load('./assets/q_press.png') 
                        key_position = (198 - 32, 650)  
                    elif event.key == pygame.K_w:
                        key = 2
                        key_image = pygame.image.load('./assets/w_press.png')  
                        key_position = (296 - 32, 650)  
                    elif event.key == pygame.K_e:
                        key = 3
                        key_image = pygame.image.load('./assets/e_press.png')  
                        key_position = (394 - 32, 650) 
                    elif event.key == pygame.K_r:
                        key = 4
                        key_image = pygame.image.load('./assets/r_press.png')  
                        key_position = (492 - 32, 650) 
                    elif event.key == pygame.K_o:
                        key = 5
                        key_image = pygame.image.load('./assets/o_press.png')  
                        key_position = (590 - 32, 650)  
                    elif event.key == pygame.K_p:
                        key = 6
                        key_image = pygame.image.load('./assets/p_press.png')  
                        key_position = (688 - 32, 650) 
                    elif event.key == pygame.K_LEFTBRACKET:
                        key = 7
                        key_image = pygame.image.load('./assets/[_press.png')  
                        key_position = (786 - 32, 650)  
                    elif event.key == pygame.K_RIGHTBRACKET:
                        key = 8
                        key_image = pygame.image.load('./assets/]_press.png')  
                        key_position = (884 - 32, 650)  

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

                    # Display the key image at the specified position
                    self.screen.blit(key_image, key_position)

                if event.type == pygame.QUIT or elapsed_time >= self.gamestate.notes['end']:
                    pygame.quit()
                    return True
            
            font = pygame.font.Font(None, 36)
            
            # judgement logic here 
            judgment_images = {
                "Excellent": pygame.image.load('./assets/EXCELLENT.png'),
                "Very Good": pygame.image.load('./assets/VERYGOOD.png'),
                "Good": pygame.image.load('./assets/GOOD.png'),
                "Fair": pygame.image.load('./assets/FAIR.png'),
                "Poor": pygame.image.load('./assets/POOR.png'),
                "No Credit": pygame.image.load('./assets/NOCREDIT.png')
            }

            # Render the judgment image in the top center of the screen
            if self.gamestate.recent_judgment in judgment_images:
                judgment_image = judgment_images[self.gamestate.recent_judgment]
                image_rect = judgment_image.get_rect(center=(self.screen.get_width() // 2, 50))
                self.screen.blit(judgment_image, image_rect)

            # text = font.render(self.gamestate.recent_judgment, True, (255, 255, 255))
            # self.screen.blit(text, (50, 50))
            pygame.display.flip()

            
            self.screen.fill((0, 0, 0))  # Clear the screen
            background_image = pygame.image.load('./assets/main_screen.png')
            self.screen.blit(background_image, (0, 0))
            # print("wahoo")
            
            pygame.draw.line(self.screen, (255, 255, 255), (0, JUDGE_Y), (1080, JUDGE_Y), 5)
            time.sleep(0.016) # Limit frame rate