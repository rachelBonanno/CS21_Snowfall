import pygame
import socket
import time
import argparse
import sys

# --- Configuration via command-line arguments ---
parser = argparse.ArgumentParser(description="Client-Client latency tester using pygame")
parser.add_argument("--local-port", type=int, required=True, help="Port to bind locally")
parser.add_argument("--peer-ip", type=str, required=True, help="IP address of the peer")
parser.add_argument("--peer-port", type=int, required=True, help="Port on which the peer is listening")
args = parser.parse_args()

# --- Initialize UDP socket ---
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('', args.local_port))
sock.setblocking(False)  # Non-blocking mode

# --- Pygame setup ---
pygame.init()
width, height = 600, 400
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("Latency Tester")
font = pygame.font.SysFont("Arial", 24)
clock = pygame.time.Clock()

# --- Variables for latency measurement ---
last_latency = None  # Last measured round-trip time in ms
ping_sent_times = {}  # Dictionary to map ping timestamps to their send time

def draw_screen():
    screen.fill((30, 30, 30))
    instructions = [
        "Press SPACE to send a ping.",
        "Waiting for ping replies...",
    ]
    for i, text in enumerate(instructions):
        rendered = font.render(text, True, (255, 255, 255))
        screen.blit(rendered, (20, 20 + i * 30))
    if last_latency is not None:
        latency_text = f"Last Latency: {last_latency:.2f} ms"
        rendered = font.render(latency_text, True, (0, 255, 0))
        screen.blit(rendered, (20, 100))
    pygame.display.flip()

running = True
while running:
    # Check for pygame events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        # Press space to send a ping
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            timestamp = time.time()
            message = f"PING:{timestamp}"
            try:
                sock.sendto(message.encode(), (args.peer_ip, args.peer_port))
                # Record the send time
                ping_sent_times[str(timestamp)] = timestamp
            except Exception as e:
                print("Error sending ping:", e)

    # Check for incoming UDP messages
    try:
        while True:
            data, addr = sock.recvfrom(1024)
            message = data.decode().strip()
            # Process incoming message
            if message.startswith("PING:"):
                # When a ping is received, reply immediately with a pong containing the same timestamp
                _, ping_timestamp = message.split(":", 1)
                pong_message = f"PONG:{ping_timestamp}"
                sock.sendto(pong_message.encode(), addr)
            elif message.startswith("PONG:"):
                _, ping_timestamp = message.split(":", 1)
                # Calculate round-trip time if we have a record of this ping
                if ping_timestamp in ping_sent_times:
                    send_time = ping_sent_times.pop(ping_timestamp)
                    rtt = (time.time() - send_time) * 1000  # convert to milliseconds
                    last_latency = rtt
                    print(f"Round-trip latency: {rtt:.2f} ms")
    except BlockingIOError:
        # No more data available from socket
        pass

    draw_screen()
    clock.tick(100000)  # Limit the loop to 60 FPS

pygame.quit()
sys.exit()
