import pygame
import time
import json
# rhythm game

def main():
    pygame.init()
    screen = pygame.display.set_mode((1080, 720))
    pygame.display.set_caption("Game")
    pygame.draw.rect(screen, (255, 0, 0), (100, 100, 100, 100))
    start_time = time.time() 
    def parse_chart(filepath):
        with open(filepath, 'r') as file:
            data = json.load(file)
        return data

    chart_data = parse_chart('./charts/basic.chart')
    print(chart_data)
    last_judgment = ""

    while True:
        elapsed_time = 1000 * (time.time() - start_time)
        for event in pygame.event.get():
            key = 0
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    key = 1
                elif event.key == pygame.K_w:
                    key = 2
                elif event.key == pygame.K_LEFTBRACKET:
                    key = 3
                elif event.key == pygame.K_RIGHTBRACKET:
                    key = 4
                if 1 <= key <= 4:
                    acc = accuracy(chart_data[0], elapsed_time, key)
                    last_judgment = norman(acc)
                    if acc > 0:
                        chart_data.pop(0)

            if event.type == pygame.QUIT:
                pygame.quit()
                return
        font = pygame.font.Font(None, 36)
        text = font.render(last_judgment, True, (255, 255, 255))
        screen.blit(text, (50, 50))
        pygame.display.flip()
        screen.fill((0, 0, 0))  # Clear the screen
        # print("wahoo")
        for note in chart_data:
            y_position = 0
            note_time = note['time']
            if elapsed_time >= note_time:
                lane = note['lane']
                if lane == 1:
                    x_position = 200
                elif lane == 2:
                    x_position = 400
                elif lane == 3:
                    x_position = 600
                elif lane == 4:
                    x_position = 800
                y_position = (elapsed_time - note_time) * 1  # Adjust speed as needed
                pygame.draw.circle(screen, (255, 255, 255), (x_position, int(y_position)), 10)
            if y_position > 700:
                print('miss')
                chart_data.remove(note)
        pygame.draw.line(screen, (255, 255, 255), (0, 600), (1080, 600), 5)
    # pygame.quit()

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
if __name__ == "__main__":
    main()