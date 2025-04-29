# snowfall_server.py
# CS21 Concurrent Programming
# Final Project -- Snowfall
# Team Snowfall -- Stephanie Wilson, Rachel Bonanno, Justin Millette
# 4/28/25
#
# This file defines the server-side, server-concurrency-related processing 
# during the runtime of Snowfall. It first creates a server with the given
# host and port information, and waits for clients to connect. It determines
# name & ping information (technically packet round-trip-time), determines a
# time to start gameplay, and then tells connected clients to start gameplay
# at that time. It then starts a gameplay process that listens for note-hit 
# messages, and then sends messages to connected clients if they need to stop
# drawing a note. It owns a "gameplay server" object that does this checking.
#
# For information on running this code, see the README.

import socket
import argparse
import sys
import threading
import struct
from server import Server 
from gamestate import Gamestate
from stats import Stats
import time
import select

def main():
    # arg parsing for server
    parser = argparse.ArgumentParser(description="Start the Snowfall server.")
    parser.add_argument('--host', type=str, default='127.0.0.1', 
                        help='Host to bind the server to.')
    parser.add_argument('--port', type=int, default=65432, 
                        help='Port to bind the server to.')
    parser.add_argument('--chart', type=str, default='./charts/basic.chart', 
                        help='Path to the chart file.')
    args = parser.parse_args()

    host = args.host
    port = args.port

    # initializing server socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(5)
    print(f"Server started on {host}:{port}")

    # creating server object
    server = Server(stats=Stats.empty_stats(), 
                    gamestate=Gamestate.empty_gamestate()) 
    server.parse_chart(args.chart)
    
    # connecting clients
    clients_lock = threading.Lock()
    clients = {}
    client_names = {}
    client_threads = []

    while len(clients) < 2: 
        client_socket, client_address = server_socket.accept()
        print(f"Accepted connection from {client_address}")
        with clients_lock:
            clients[client_socket] =  ("", "")
    
    # tell clients we accepted them, then wait for them to send their names
    # send a time 2 seconds into the future so that we can start syncing then
    future_time = time.time() + 3  # Current time + 2 seconds

    # start client connecting threads
    for client_socket in list(clients.keys()):  
        thread = threading.Thread(target=connect_client, 
                                  args=[clients, client_socket, 
                                        clients_lock, future_time, 
                                        client_names])
        client_threads.append(thread)
        thread.start()
    
    for thread in client_threads:
        thread.join()
    
    # run gameplay processing on main thread
    gameplay(clients, server)
    
    # print stats to terminal after gameplay
    notes = server.gamestate.notes["notes"]

    labels = [
        "Excellent", "Very Good", "Good", "Fair", "Poor", "No Credit"
    ]

    counts = {
        lab: sum(n["judgment"] == lab for n in notes)
        for lab in labels
    }

    print(f"Final score: {server.gamestate.score}")
    print(f"Max combo  : {server.stats.max_combo}")

    for lab in labels:
        print(f"{lab:<11}: {counts[lab]}")
    
    # close the server socket
    server_socket.close()

def connect_client(clients, client, clients_lock, future_time, name_array):
    """
    Handles the connection process for a client in the server-client 
    architecture. This function performs the following steps:
    1. Requests and retrieves the client's name.
    2. Updates the shared `clients` and `name_array` dictionaries with the 
        client's information.
    3. Sends a connection acknowledgment to the client and waits for the client
        to acknowledge.
    4. Measures the round-trip time (ping) between the server and the client.
    5. Sends a future time value to the client, adjusted by the measured ping, 
        and waits for acknowledgment.
    
    - If the client disconnects or fails to respond at any step, the client is 
        removed from the `clients` dictionary.
    - The function ensures proper synchronization when modifying shared
        resources using the `clients_lock`.
    - The function expects the client to follow a specific protocol for 
        communication, including sending acknowledgments.
    """
    client.send(b"Retrieving client name...")
    # receive the length of the name (4 byte int)
    name_length_bytes = recv_data(client, 4)
    if not name_length_bytes:
        print("Client disconnected before sending name length.", 
              file=sys.stderr)
        with clients_lock:
            del clients[client]
        return
    name_length = struct.unpack("!I", name_length_bytes)[0]
    # receive the name based on the length
    client_name_bytes = recv_data(client, name_length)
    if not client_name_bytes:
        print("Client disconnected before sending name.", file=sys.stderr)
        with clients_lock:
            del clients[client]
        return
    client_name = client_name_bytes.decode('utf-8').strip()
    # update client information
    with clients_lock:
        clients[client] = (client_name, "")
        name_array[client] = client_name
        print(f"This player has joined:", client_name)
    
    # confirm connection
    client.send(b"Connection Established")
    # Wait for the client to acknowledge the connection
    ack_bytes = recv_data(client, 3)
    if not ack_bytes:
        print(f"{client_name} disconnected before acknowledging connection.", 
              file=sys.stderr)
        with clients_lock:
            del clients[client]
        return
    ack = ack_bytes.decode('utf-8').strip()
    if ack != "ACK":
        print(f"{client_name} did not acknowledge connection!", file=sys.stderr)
        return

    # get round-trip time by pinging
    ping = time.time()
    client.sendall("ping!".encode('utf-8'))
    ack_pong = recv_data(client, 5)
    pong = time.time() - ping
    if not ack_pong:
        print(f"{client_name} disconnected before ponging server ping.", 
              file=sys.stderr)
        with clients_lock:
            del clients[client]
        return
    ack = ack_pong.decode('utf-8').strip()
    if ack != "pong!":
        print(f"{client_name} did not acknowledge ping!", file=sys.stderr)
    # update client information with new RTT
    with clients_lock:
        client_name, _ = clients[client]
        clients[client] = (client_name, pong)
        print(f"{client_name} has ping {pong}")

    # pack the time as a double
    future_time_bytes = struct.pack("!d", future_time + pong) 

    # send the future time to the client
    client.sendall(future_time_bytes)  

    # wait for the client to acknowledge the future time
    ack_bytes = recv_data(client, 3)
    if not ack_bytes:
        print(f"{client_name} disconnected before acknowledging future time.", 
              file=sys.stderr)
        with clients_lock:
            del clients[client]
        return
    ack = ack_bytes.decode('utf-8').strip()
    if ack != "ACK":
        print(f"{client_name} did not acknowledge future time!", 
              file=sys.stderr)

def gameplay(clients, server):
    """ Gameplay logic. Listens for client note hits and then informs clients 
    when to not draw notes anymore."""
    client_sockets = list(clients.keys())
    # ensure two players are connected
    if len(client_sockets) != 2:
        print("Error: Not enough clients to start gameplay.", file=sys.stderr)
        return

    while True:
        # wait until a socket has a message to parse
        readable, _, _ = select.select(client_sockets, [], [], 0.01)  
        for sock in readable:
            try:
                # get data length
                len_data_bytes = recv_data(sock, 4)
                if not len_data_bytes: # client DC
                    print(f"Client {clients[sock]} disconnected.", 
                          file=sys.stderr)
                    # this pattern is to ensure that we never send anything to 
                    # this client ever again after it disconnects
                    del clients[sock] 
                    client_sockets.remove(sock)
                    if not client_sockets:
                        print("All clients disconnected. Ending gameplay.")
                        return
                    continue
                length = struct.unpack("!I", len_data_bytes)[0]

                # get "length" much data
                data_bytes = recv_data(sock, length)
                if not data_bytes: # client DC
                    print(f"Client {clients[sock]} disconnected during \
                          message.", file=sys.stderr)
                    del clients[sock]
                    client_sockets.remove(sock)
                    if not client_sockets:
                        print("All clients disconnected. Ending gameplay.")
                        return
                message = data_bytes.decode('utf-8').strip()
                
                # Parse the received message
                try:
                    # first is client ID and we don't care
                    _, note_id, note_judgment = message.split(", ") 
                    note_id = int(note_id.strip())
                    note_judgment = note_judgment.strip()
                except ValueError as e:
                    print(f"Error parsing message from {clients[sock]}: {e}", 
                          file=sys.stderr)
                    continue
                # Update server gamestate with received data
                notify = server.receive_score(note_id, note_judgment)  
                if notify:
                    message = message.encode('utf-8')
                    # tell all clients that a note was hit
                    for soc in client_sockets: 
                        soc.sendall(struct.pack("!I", len(message)))
                        soc.sendall(message)
            # if we got some error, treat it as client DC (which it is)
            except Exception as e:
                # this handles the error that shows up when a client 
                # disconnects on Windows. This is untested on any other OS; 
                # the side effects are just an unimportant error message 
                # printed to standard error.
                if "forcibly closed by the remote" not in str(e): 
                    print(f"Error handling client {clients[sock]}: {e}", 
                          file=sys.stderr)
                # again make sure we never send anything to this client ever 
                del clients[sock] 
                client_sockets.remove(sock)
                if not client_sockets: 
                    print("All clients disconnected. Ending gameplay.")
                    return

def recv_data(client, length):
    """ Receives data over sockets of given length. This was originally 
    implemented because we were planning to send a lot more data (charts and 
    mp3 files) over the sockets, but we scrapped this. This function still 
    works for smaller data lengths, but normal recv would work just fine too."""
    data = b""
    while len(data) < length:
        packet = client.recv(length - len(data))
        if not packet:
            break
        data += packet
    return data

if __name__ == "__main__":
    main()