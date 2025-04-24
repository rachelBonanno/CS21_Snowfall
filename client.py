import pygame
import time
import json
import pathlib
from time import perf_counter

JUDGE_Y = 615
SPEED = 1

JUDGMENT_IMAGES = {
                "Excellent": pygame.image.load('./assets/EXCELLENT.png'),
                "Very Good": pygame.image.load('./assets/VERYGOOD.png'),
                "Good": pygame.image.load('./assets/GOOD.png'),
                "Fair": pygame.image.load('./assets/FAIR.png'),
                "Poor": pygame.image.load('./assets/POOR.png'),
                "No Credit": pygame.image.load('./assets/NOCREDIT.png')
            }

KEY_IMAGES = {
    1: pygame.image.load('./assets/q_press.png'),
    2: pygame.image.load('./assets/w_press.png'),
    3: pygame.image.load('./assets/e_press.png'),
    4: pygame.image.load('./assets/r_press.png'),
    5: pygame.image.load('./assets/o_press.png'),
    6: pygame.image.load('./assets/p_press.png'),
    7: pygame.image.load('./assets/[_press.png'),
    8: pygame.image.load('./assets/]_press.png')  
}

KEY_LIMIT_IMAGES = {
    1: pygame.image.load('./assets/q_limit.png'),
    2: pygame.image.load('./assets/w_limit.png'),
    3: pygame.image.load('./assets/e_limit.png'),
    4: pygame.image.load('./assets/r_limit.png'),
    5: pygame.image.load('./assets/o_limit.png'),
    6: pygame.image.load('./assets/p_limit.png'),
    7: pygame.image.load('./assets/[_limit.png'),
    8: pygame.image.load('./assets/]_limit.png')  
}

LANE_KEY = {                
    pygame.K_q:1, pygame.K_w:2, pygame.K_e:3, pygame.K_r:4,
    pygame.K_o:5, pygame.K_p:6,
    pygame.K_LEFTBRACKET:7, pygame.K_RIGHTBRACKET:8,
}
LANE_POS = {                
    1:(166,650), 2:(264,650), 3:(362,650), 4:(460,650),
    5:(558,650), 6:(656,650), 7:(754,650), 8:(852,650),
}


        
body_image = pygame.image.load('./assets/long_p1.png')
body_width, body_height = body_image.get_size()

head_image = pygame.image.load('./assets/note_p1.png')
head_image = pygame.transform.scale(head_image, (64, 62)) 


note_image = pygame.image.load('./assets/note_p1.png')
note_image = pygame.transform.scale(note_image, (64, 62))  # Adjust size as needed
background_image = pygame.image.load('./assets/main_screen.png')

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
        self.visible_index = 0
        self.last_announced_id = -1
        self.pressed_keys = set()
    def active_lanes(self):
        """Return the right-most (max index) two lanes currently held."""
        return set(sorted(self.pressed_keys)[-2:])

    def announce(self, note_id, judgment):
        """Show a new judgment only if this note hasn’t been announced."""
        if note_id != self.last_announced_id:
            self.gamestate.recent_judgment = judgment
            self.last_announced_id         = note_id

    def receive_hit_confirmation(self, note_id, judgment): 
        """ This is where we actually record that a note was hit, so it stops
        being drawn on the screen. This is called from snowfall_client when it
        receives a message from the server indicating that a note was hit. """
        # print(f"Received hit confirmation: {note_id}, {judgment}")
        self.gamestate.notes['notes'][note_id]['judgment'] = judgment # set the judgment of the note to the one we received
        self.announce(note_id, judgment)


    def set_socket(self, server_socket):
        self.server_socket = server_socket

    def client_init(self):
        
        self.gamestate.notes = parse_chart('./charts/imprinting.chart')

        audio_path = pathlib.Path('./charts') / self.gamestate.notes['audio']
        print("Audio file:",audio_path.resolve())

        if not audio_path.exists():
            raise FileNotFoundError(audio_path)
        song_offset = self.gamestate.notes.get("offset", 0) / 1000 # to seconds
        
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.init()
        # flags = pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.SCALED
        self.screen = pygame.display.set_mode((1080, 720)) # pygame.display.set_mode((1080, 720), flags)
        pygame.display.set_caption(f"Game: {self.name}")
        for note in self.gamestate.notes['notes']:

            # flags used only at runtime
            note['holding']   = False      # latch state for holds
            note['completed'] = False 
        # print(self.gamestate.notes)
        while time.time() < self.starttime:
            time.sleep(0.01)
        
        print(self.starttime - time.time() + song_offset)
        play_delay = max(0, self.starttime - time.time() + song_offset)
        print(play_delay)
        pygame.time.set_timer(pygame.USEREVENT + 1, int(play_delay*1000), loops=1)
        pygame.mixer.music.load(audio_path)
        pygame.mixer.music.set_volume(0.05) # this mf is LOUD
        print(f"starting client loop at {time.time()}")

        return self.client_loop()


    def client_loop(self):
        clock = pygame.time.Clock()
        frame = 0
        while True:
            t0 = perf_counter()
            note_queue = {1: [], 2: [], 3: [], 4: [], 5: [], 6: [], 7: [], 8: []}
            elapsed_time = 1000 * (time.time() - self.starttime)
            visible = self.visible_index          # attribute you initialise to 0

            while visible < len(self.gamestate.notes['notes']) and self.gamestate.notes['notes'][visible]['time'] < elapsed_time - 2000:
                visible += 1                      # note is two seconds behind -> skip forever
            self.visible_index = visible

            for i in range(visible, len(self.gamestate.notes['notes'])):
                note = self.gamestate.notes['notes'][i]
                if note['time'] > elapsed_time + 2000:
                    break                         # two seconds ahead -> stop scanning
                if note['judgment'] != "":
                    # print(f"should stop drawing {note['id']} bc it has judgment {note['judgment']}")
                    continue
                y_position = 0
                note_time = note['time']
                if elapsed_time >= note_time or (note['id'] == self.gamestate.recent_id and elapsed_time >= self.gamestate.recent_position):
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
                            remaining_tail_px = total_tail_px 

                        # --- BODY RECTANGLE ---------------------------------------------------
                        # The rectangle starts at the top of the still-visible tail
                        top_y = head_y - remaining_tail_px
                        rect_h = remaining_tail_px        # height of the visible body

                        # --- BODY IMAGE ---------------------------------------------------
                        if rect_h > 0:
                            # Load the body image

                            # Calculate how many times the body image needs to be repeated
                            num_repeats = int(rect_h / body_height) + 1

                            # Draw the body image repeatedly to fill the height
                            for rep in range(num_repeats):
                                segment_y = int(top_y) + rep * body_height
                                if segment_y + body_height > top_y + rect_h:
                                    # Clip the last segment if it exceeds the visible height
                                    clipped_body = pygame.Surface((body_width, int(top_y + rect_h - segment_y)), pygame.SRCALPHA)
                                    clipped_body.blit(body_image, (0, 0), (0, 0, body_width, int(top_y + rect_h - segment_y)))
                                    self.screen.blit(clipped_body, (x_position - 28, segment_y))
                                else:
                                    self.screen.blit(body_image, (x_position - 28, segment_y))

                        # --- HEAD IMAGE ---------------------------------------------------
                        if draw_head:
                            self.screen.blit(head_image, (x_position - 32, int(head_y) - 31))
                    else: # not held note
                        # render note
                        self.screen.blit(note_image, (x_position - 32, int(y_position) - 31)) 
                if y_position > 700 and note['duration'] == 0 and note['holding'] == False:
                    # print('miss')
                    self.gamestate.recent_id = note['id']
                    self.gamestate.recent_position = y_position
                    self.gamestate.recent_judgment = "No Credit"
                if note['duration'] > 0 and not note['completed']:
                    tail_time = note['time'] + note['duration'] + JUDGE_Y  # same JUDGE_Y ms leniency
                    if elapsed_time > tail_time:
                        note['judgment'] = "No Credit"
                        note['completed'] = True
                        self.gamestate.recent_id       = note['id']
                        self.gamestate.recent_judgment = "No Credit"
                        self.gamestate.recent_position = y_position
                        self.active_holds.pop(note['lane'], None)      # if we were still holding
            t1 = perf_counter()
            for event in pygame.event.get():
                if event.type == pygame.USEREVENT + 1:
                    print("playing")
                    pygame.mixer.music.play()
                if event.type == pygame.KEYDOWN and event.key in LANE_KEY:
                    lane = LANE_KEY[event.key]
                    self.pressed_keys.add(lane)

                    # ---- HIT-DETECTION (exactly what you already had) ----
                    if lane in self.active_lanes():
                        curnotes = [n for n in note_queue[lane] if n['judgment'] == ""]
                        if curnotes:
                            note = curnotes[0]
                            acc  = accuracy(note, elapsed_time, lane)
                            if note['duration'] == 0:
                                self.gamestate.recent_judgment = norman(acc)
                                self.gamestate.recent_id       = note['id']
                            elif acc > 0:
                                note['holding'] = True
                                self.active_holds[lane] = note
                            # print(current_note)
                elif event.type == pygame.KEYUP and event.key in LANE_KEY:
                    lane = LANE_KEY[event.key]
                    self.pressed_keys.discard(lane)

                    note = self.active_holds.pop(lane, None)
                    if note and not note['completed']:
                        tail_time = note['time'] + note['duration']
                        late_by   = elapsed_time - tail_time
                        j = norman(1 - late_by/1000) if late_by <= self.release_window*1000 else "No Credit"
                        note['completed']           = True
                        self.gamestate.recent_id    = note['id']
                        self.gamestate.recent_judgment = j

                    # Display the key image at the specified position
                    # self.screen.blit(key_image, key_position)

                if event.type == pygame.QUIT or elapsed_time >= self.gamestate.notes['end']:
                    pygame.quit()
                    return True
            t2 = perf_counter()
            font = pygame.font.Font(None, 36)
            
            # judgement logic here 
            

            # Render the judgment image in the top center of the screen
            if self.gamestate.recent_judgment in JUDGMENT_IMAGES:
                # print(f"got judgment {self.gamestate.recent_judgment}")
                judgment_image = JUDGMENT_IMAGES[self.gamestate.recent_judgment]
                image_rect = judgment_image.get_rect(center=(self.screen.get_width() // 2, 50))
                self.screen.blit(judgment_image, image_rect)

            # text = font.render(self.gamestate.recent_judgment, True, (255, 255, 255))
            # self.screen.blit(text, (50, 50))
            active = self.active_lanes()

            for lane in self.pressed_keys:
                pos = LANE_POS[lane]
                if lane in active:
                    self.screen.blit(KEY_IMAGES[lane], pos)
                else:
                    self.screen.blit(KEY_LIMIT_IMAGES[lane], pos)
            
            pygame.display.flip()
            t3 = perf_counter()
            if frame % 120 == 0:
                print(f"update = {(t1-t0)*1000:5.1f} ms   "
                    f"event = {(t2-t1)*1000:5.1f} ms   "
                    f"flip = {(t3-t2)*1000:5.1f} ms")
            frame += 1

            
            self.screen.fill((0, 0, 0))  # Clear the screen
            
            self.screen.blit(background_image, (0, 0))
            # print("wahoo")
            
            pygame.draw.line(self.screen, (255, 255, 255), (0, JUDGE_Y), (1080, JUDGE_Y), 5)
            # time.sleep(0.016) # Limit frame rate