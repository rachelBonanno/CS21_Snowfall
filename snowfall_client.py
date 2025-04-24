import socket
import argparse
import sys
import struct
import time
from gamestate import Gamestate
from stats import Stats
from client import Client
import threading
import pickle

# i am a client

def main():
    # create a socket object
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # parse command-line arguments
    parser = argparse.ArgumentParser(description="Client for connecting to a server.")
    parser.add_argument('--host', type=str, required=True, help='Server hostname or IP address')
    parser.add_argument('--port', type=int, required=True, help='Server port number')
    parser.add_argument('--name', type=str, required=True, help='Client name')
    args = parser.parse_args()

    # Assign host and port from arguments
    host = args.host
    port = args.port
    name = args.name

    stop_event = threading.Event()

    # Connect to the server
    try:
        server_socket.connect((host, port))
        print(f"Connected to server at {host}:{port}")
    except socket.error as e:
        print(f"Error connecting to server at {host}:{port}: {e}", file=sys.stderr)

    # Receive connection response from server
    data = server_socket.recv(1024) 
    # if data:
    #     print(f"Received: {data.decode()}")

    # Send name length and name to the server
    name_bytes = name.encode()
    server_socket.send(struct.pack("!I", len(name_bytes)))  
    server_socket.send(name_bytes)  

    # Receive acknowledgment for connection
    data = server_socket.recv(1024)  
    # if data:
    #     print(f"Received: {data.decode()}")
    server_socket.send(b"ACK")

    data = server_socket.recv(5)  
    if data:
        # we got a "ping!"
        # print(f"Received future time: {future_time}")
        server_socket.send(b"pong!")

    # Receive the future time from the server
    data = server_socket.recv(8)  
    if data:
        future_time = struct.unpack("!d", data)[0]
        print(f"Received future time: {future_time}")
    server_socket.send(b"ACK")

    

    client_game = Client(name=name, gamestate=Gamestate.empty_gamestate(), stats=Stats.empty_stats(), starttime=future_time)
    client_game.set_socket(server_socket)  

    # gameplay time
    
    # Start threads for sending and receiving messages
    receive_thread = threading.Thread(target=receive_messages, args=[server_socket, name, client_game, stop_event])
    send_thread = threading.Thread(target=send_messages, args=[server_socket, name, client_game, stop_event])
    receive_thread.daemon = True
    send_thread.daemon = True

    receive_thread.start()
    send_thread.start()

    client_game.client_init()

    stop_event.set()

    # # Keep the main thread alive until the other threads finish (which will likely be never in this example)
    # try:
    #     while True:
    #         time.sleep(1)
    # except KeyboardInterrupt:
    #     print(f"{name}: Exiting.")
    # finally:
    server_socket.close()
    receive_thread.join()
    send_thread.join()



def receive_messages(server_socket, client_name, client_instance, stop_event):
    while not stop_event.is_set():
        try:
            len_data_bytes = server_socket.recv(4)
            if not len_data_bytes:
                print(f"{client_name}: Connection to server closed (receiving).")
                break
            message_length = struct.unpack("!I", len_data_bytes)[0]
            message_bytes = server_socket.recv(message_length)
            if not message_bytes:
                print(f"{client_name}: Connection to server closed (receiving).")
                break
            message = message_bytes.decode('utf-8')
            try:
                client_id, note_id, note_judgment = message.split(", ")
                note_id = int(note_id.strip())
                note_judgment = note_judgment.strip()
                # print(f"Parsed message - Client ID: {client_id}, Note ID: {note_id}, Note Judgment: {note_judgment}")
            except ValueError as e:
                print(f"Error parsing message: {e}", file=sys.stderr)
                continue
            # print(f"{client_name} received: {message}")
            client_instance.receive_hit_confirmation(note_id, note_judgment)
            # use to update the gamestate 
        except Exception as e:
            print(f"{client_name}: Error receiving message: {e}")
            break

def send_messages(server_socket, client_name, client, stop_event):
    # while True:
        # if int(round(time.time()*1000)) % 16 == 0:
        #     message = "Hello Server".encode('utf-8')
        #     try:
        #         server_socket.sendall(struct.pack("!I", len(message)))
        #         server_socket.sendall(message)
        #         time.sleep(0.016) # Roughly 60 ticks per second
        #     except socket.error as e:
        #         print(f"{client_name}: Error sending message: {e}")
        #         break
    sent_ids = set()  # Keep track of sent IDs to ensure each is sent only once
    while not stop_event.is_set():
        # Check if the recent_id has changed and hasn't been sent before
        recent_id = client.gamestate.recent_id
        if recent_id not in sent_ids:
            # Add the recent_id to the set of sent IDs
            sent_ids.add(recent_id)

            # Get the recent_judgment
            recent_judgment = client.gamestate.recent_judgment

            # Prepare the data to send
            data_to_send = f"{client_name}, {recent_id}, {recent_judgment}".encode()
            # print(f"sending: {data_to_send}")

            # Send the length of the data followed by the data itself
            server_socket.sendall(struct.pack("!I", len(data_to_send)))
            server_socket.sendall(data_to_send)
        else:
            time.sleep(0.01)  # Avoid busy-waiting





if __name__ == "__main__":
    main()