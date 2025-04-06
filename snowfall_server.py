# i am a server

# server,py is just a way to hold information
# snowfall_server actually receives message things
# snowfall_client actually sends message things
# client.py is just a way to hold information

import socket
import argparse
import sys
import threading
import struct
from server import Server 
from gamestate import Gamestate
from stats import Stats
import json
import time

def main():
    # arg parsing for server
    parser = argparse.ArgumentParser(description="Start the Snowfall server.")
    parser.add_argument('--host', type=str, default='127.0.0.1', help='Host to bind the server to.')
    parser.add_argument('--port', type=int, default=65432, help='Port to bind the server to.')
    parser.add_argument('--chart', type=str, default='charts/basic.chart', help='Path to the chart file.')
    args = parser.parse_args()

    host = args.host
    port = args.port

    # initializing server socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(5)
    print(f"Server started on {host}:{port}")

    # creating server object
    server = Server(stats=Stats.empty_stats(), gamestate=Gamestate.empty_gamestate()) 
    server.parse_chart(args.chart)

    clients_lock = threading.Lock()

    # connecting clients
    clients = {}
    while len(clients) < 2:
        client_socket, client_address = server_socket.accept()
        print(f"Accepted connection from {client_address}")
        clients[client_socket] =  ""
    
    # tell clients we accepted them, then wait for them to send their names
    # send a time 2 seconds into the future so that we can start syncing then
    future_time = time.time() + 2  # Current time + 2 seconds
    future_time_bytes = struct.pack("!d", future_time) # pack the time as a double

    threads = [threading.Thread(target=connect_client, args=[clients, client, clients_lock, future_time_bytes]) for client in clients]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    
    # after syncing we can do gameplay stuff:
    # message receiving loop
    threads = [threading.Thread(target=gameplay, args=[client, server]) for client in clients]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    
    # close the server socket
    server_socket.close()
    

    

def connect_client(clients, client, clients_lock, future_time):
    # receive name from client
    # store this better
    client_name = recv_data(client, 32).decode('utf-8').strip()
    with clients_lock:
        clients[client] = client_name
    
    client.send(b"Connection Established")

    # Send the future time to the client
    client.sendall(future_time)  # Ensure all bytes are sent

    # this was crashing bc the clients were dc'd before we sent this



def gameplay(client, server):
    while True:
        try:
            # receive data from one of the clients
            length = struct.unpack("!I", recv_data(client, 4))[0]
            data = recv_data(client, length)

            note = data.decode('utf-8')
            # {time, lane, id, judgment}
            server.receive_note(note)


            client.send(data) 

        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            break




def recv_data(client, length):
    # receive data from the client
    data = b""
    while len(data) < length:
        packet = client.recv(length - len(data))
        if not packet:
            break
        data += packet
    return data


if __name__ == "__main__":
    main()