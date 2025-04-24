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
import pickle

def main():
    # arg parsing for server
    parser = argparse.ArgumentParser(description="Start the Snowfall server.")
    parser.add_argument('--host', type=str, default='127.0.0.1', help='Host to bind the server to.')
    parser.add_argument('--port', type=int, default=65432, help='Port to bind the server to.')
    parser.add_argument('--chart', type=str, default='./charts/basic.chart', help='Path to the chart file.')
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
    print(server.gamestate.notes)
    clients_lock = threading.Lock()

    # connecting clients
    clients = {}
    client_names = {}
    client_threads = []

    while len(clients) < 2: 
        client_socket, client_address = server_socket.accept()
        print(f"Accepted connection from {client_address}")
        with clients_lock:
            clients[client_socket] =  ""
    
    # tell clients we accepted them, then wait for them to send their names
    # send a time 2 seconds into the future so that we can start syncing then
    future_time = time.time() + 2  # Current time + 2 seconds
    future_time_bytes = struct.pack("!d", future_time) # pack the time as a double


    for client_socket in list(clients.keys()):  # Iterate over a copy to allow removal
        thread = threading.Thread(target=connect_client, args=[clients, client_socket, clients_lock, future_time_bytes, client_names])
        client_threads.append(thread)
        thread.start()
    
    for thread in client_threads:
        thread.join()
    

    print("client names:", client_names)

    # after syncing we can do gameplay stuff:
    # message receiving loop
    # server = Server(stats=Stats.empty_stats(), gamestate=Gamestate.empty_gamestate())
    # server.parse_chart(args.chart)

    gameplay(clients, server)
    
    # close the server socket
    server_socket.close()
    

    

def connect_client(clients, client, clients_lock, future_time, name_array):
    try:
        print("Asking for client name")
        client.send(b"Retrieving client name...")

        # Receive the length of the name (4 bytes)
        name_length_bytes = recv_data(client, 4)
        if not name_length_bytes:
            print("Client disconnected before sending name length.", file=sys.stderr)
            with clients_lock:
                del clients[client]
            return
        name_length = struct.unpack("!I", name_length_bytes)[0]

        # Receive the name based on the length
        client_name_bytes = recv_data(client, name_length)
        if not client_name_bytes:
            print("Client disconnected before sending name.", file=sys.stderr)
            with clients_lock:
                del clients[client]
            return
        client_name = client_name_bytes.decode('utf-8').strip()

        with clients_lock:
            clients[client] = client_name
            name_array[client] = client_name
            print(f"This player has joined!:", client_name)

        client.send(b"Connection Established")

        # Wait for the client to acknowledge the connection
        ack_bytes = recv_data(client, 3)
        if not ack_bytes:
            print(f"{client_name} disconnected before acknowledging connection.", file=sys.stderr)
            with clients_lock:
                del clients[client]
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
            with clients_lock:
                del clients[client]
            return
        ack = ack_bytes.decode('utf-8').strip()
        if ack != "ACK":
            print(f"{client_name} did not acknowledge future time!", file=sys.stderr)

    except Exception as e:
        print(f"Error in connect_client for {client_name}: {e}", file=sys.stderr)
        with clients_lock:
            if client in clients:
                del clients[client]
        if client in name_array:
            del name_array[client]
    finally:
        print(f"connect_client for {client_name} finished.")








def gameplay(clients, server):
    # print("Starting gameplay with select...")
    client_sockets = list(clients.keys())
    if len(client_sockets) != 2:
        print("Error: Not enough clients to start gameplay.", file=sys.stderr)
        return

    while True:
        # print("Inside the server gameplay loop (select)")
        readable, _, _ = select.select(client_sockets, [], [], 0.01)  # Non-blocking select with a timeout
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
                data_bytes = recv_data(sock, length)
                if not data_bytes:
                    print(f"Client {clients[sock]} disconnected during message.", file=sys.stderr)
                    del clients[sock]
                    client_sockets.remove(sock)
                    if not client_sockets:
                        print("All clients disconnected. Ending gameplay.")
                        return

                message = data_bytes.decode('utf-8').strip()
                print(f"Received from {clients[sock]}: {message}")
                # Parse the received message
                try:
                    client_id, note_id, note_judgment = message.split(", ")
                    note_id = int(note_id.strip())
                    note_judgment = note_judgment.strip()
                    print(f"Parsed message - Client ID: {client_id}, Note ID: {note_id}, Note Judgment: {note_judgment}")
                    
                except ValueError as e:
                    print(f"Error parsing message from {clients[sock]}: {e}", file=sys.stderr)
                    continue
                notify = server.receive_score(note_id, note_judgment)  # Update server gamestate with received data
                if notify:
                    message = message.encode('utf-8')
                    for soc in client_sockets: # tell all clients that a note was hit
                        print(f"sending {message} to {soc}")
                        soc.sendall(struct.pack("!I", len(message)))
                        soc.sendall(message)

            except Exception as e:
                print(f"Error handling client {clients[sock]}: {e}", file=sys.stderr)
                del clients[sock]
                client_sockets.remove(sock)
                if not client_sockets:
                    print("All clients disconnected. Ending gameplay.")
                    return

        # Send "Hello Server" to all connected clients at a regular interval (simulating tick)
        # if int(round(time.time()*1000)) % 16 == 0:
        #     server_message = "Hello Server".encode('utf-8')
        #     for sock in client_sockets:
        #         try:
        #             sock.sendall(struct.pack("!I", len(server_message)))
        #             sock.sendall(server_message)
        #         except Exception as e:
        #             print(f"Error sending to client {clients[sock]}: {e}")
                    # Handle disconnection if necessary

        time.sleep(0.016) # Roughly 60 ticks per second


    









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