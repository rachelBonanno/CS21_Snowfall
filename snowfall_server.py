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
import select

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
    client_names = {}
    client_threads = []

    while len(clients) < 2: 
        client_socket, client_address = server_socket.accept()
        print(f"Accepted connection from {client_address}")
        clients[client_socket] =  ""
    
    # tell clients we accepted them, then wait for them to send their names
    # send a time 2 seconds into the future so that we can start syncing then
    future_time = time.time() + 2  # Current time + 2 seconds
    future_time_bytes = struct.pack("!d", future_time) # pack the time as a double

    client_names = {}

    threads = [threading.Thread(target=connect_client, args=[clients, client, clients_lock, future_time_bytes, client_names]) for client in clients]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    

    print("client names:", client_names)

    # after syncing we can do gameplay stuff:
    # message receiving loop
    server = Server(stats=Stats.empty_stats(), gamestate=Gamestate.empty_gamestate())

    gameplay(clients, server)
    
    # close the server socket
    server_socket.close()
    

    

def connect_client(clients, client, clients_lock, future_time, name_array):
    # receive name from client
    print("Asking for client name")
    client.send(b"Retrieving client name...")

    # Receive the length of the name (4 bytes)
    name_length_bytes = recv_data(client, 4)
    if not name_length_bytes:
        print("Client disconnected before sending name length.", file=sys.stderr)
        return
    name_length = struct.unpack("!I", name_length_bytes)[0]

    # Receive the name based on the length
    client_name = recv_data(client, name_length).decode('utf-8').strip()
    with clients_lock:
        clients[client] = client_name
        print("This player has joined!:", client_name)
    client.send(b"Connection Established")

    # Wait for the client to acknowledge the connection
    ack_bytes = recv_data(client, 3)
    if not ack_bytes:
        print(f"{client_name} disconnected before acknowledging connection.", file=sys.stderr)
        return
    ack = ack_bytes.decode('utf-8').strip()
    if ack != "ACK":
        print(f"{client_name} did not acknowledge connection!", file=sys.stderr)
        return

    # Send the future time to the client
    client.sendall(future_time)  # Ensure all bytes are sent

    # Wait for the client to acknowledge the future time
    ack_bytes = recv_data(client, 3)
    if not ack_bytes:
        print(f"{client_name} disconnected before acknowledging future time.", file=sys.stderr)
        return
    ack = ack_bytes.decode('utf-8').strip()
    if ack != "ACK":
        print(f"{client_name} did not acknowledge future time!", file=sys.stderr)

    name_array[client] = client_name

    # onwards to gameplay






def gameplay(clients, server):
    print("Starting gameplay with select...")
    client_sockets = list(clients.keys())
    if len(client_sockets) != 2:
        print("Error: Not enough clients to start gameplay.", file=sys.stderr)
        return

    while True:
        print("Inside the server gameplay loop (select)")
        readable, _, _ = select.select(client_sockets, [], [])  # Wait for sockets to be ready for reading

        for sock in readable:
            try:
                len_data_bytes = recv_data(sock, 4)
                if not len_data_bytes:
                    print(f"Client {clients[sock]} disconnected.", file=sys.stderr)
                    del clients[sock]
                    client_sockets.remove(sock)
                    if not client_sockets:
                        print("All clients disconnected. Ending gameplay.")
                        return
                    continue

                length = struct.unpack("!I", len_data_bytes)[0]
                data = recv_data(sock, length).decode('utf-8')
                print(f"Received from {clients[sock]}: {data}")

                # Echo back to the same client
                response = f"Server received from {clients[sock]}: {data}".encode('utf-8')
                sock.sendall(struct.pack("!I", len(response)))
                sock.sendall(response)

            except Exception as e:
                print(f"Error with client {clients[sock]}: {e}", file=sys.stderr)
                del clients[sock]
                client_sockets.remove(sock)
                if not client_sockets:
                    print("All clients disconnected. Ending gameplay.")
                    return

    









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