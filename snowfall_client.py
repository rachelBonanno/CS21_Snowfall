import socket
import argparse
import sys
import struct
import time
from gamestate import Gamestate
from stats import Stats
from client import Client


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

    # Connect to the server
    try:
        server_socket.connect((host, port))
        print(f"Connected to server at {host}:{port}")
    except socket.error as e:
        print(f"Error connecting to server at {host}:{port}: {e}", file=sys.stderr)

    # Receive connection response from server
    data = server_socket.recv(1024) 
    if data:
        print(f"Received: {data.decode()}")

    # Send name length and name to the server
    name_bytes = name.encode()
    server_socket.send(struct.pack("!I", len(name_bytes)))  
    server_socket.send(name_bytes)  

    # Receive acknowledgment for connection
    data = server_socket.recv(1024)  
    if data:
        print(f"Received: {data.decode()}")
    server_socket.send(b"ACK")

    # Receive the future time from the server
    data = server_socket.recv(8)  
    if data:
        future_time = struct.unpack("!d", data)[0]
        print(f"Received future time: {future_time}")
    server_socket.send(b"ACK")

    client = Client(name=name, gamestate=Gamestate.empty_gamestate(), stats=Stats.empty_stats(), starttime=future_time)
    client.client_init()
    # gameplay time
    # while True:
    #     if int(round(time.time()*1000)) % 16 == 0:
    #         print(round(time.time()*1000))
    #         bytes = 15
    #         server_socket.send(struct.pack("!I", bytes))
    #         server_socket.send(f"{name}Hello, server!".encode()) 
    #         # wait for a hundredth of a second
    #         time.sleep(0.01)

    # Close the connection
    server_socket.close()


if __name__ == "__main__":
    main()