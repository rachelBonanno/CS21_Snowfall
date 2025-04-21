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
    while len(clients) < 1: # change back to 2 later
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

    print("Asking for client name")
    client.send(b"Retrieving client name...")

    # Receive the length of the name (4 bytes)
    name_length = struct.unpack("!I", recv_data(client, 4))[0]

    # Receive the name based on the length
    client_name = recv_data(client, name_length).decode('utf-8').strip()

    with clients_lock:
        clients[client] = client_name
        print("This player has joined!:", client_name)
        
    client.send(b"Connection Established")

    # Wait for the client to acknowledge the connection
    ack = recv_data(client, 3).decode('utf-8').strip()
    if ack != "ACK":
        print("Client did not acknowledge connection!", file=sys.stderr)
        return

    # Send the future time to the client
    client.send(future_time)  # Ensure all bytes are sent

    # Wait for the client to acknowledge the future time
    ack = recv_data(client, 3).decode('utf-8').strip()
    if ack != "ACK":
        print("Client did not acknowledge future time!", file=sys.stderr)

    # onwards to gameplay



def gameplay(client, server):
    olddata = b"a"
    throlddata = b"b"
    while True:
        try:
            # receive data from one of the clients
            print("before finding the length")
            len_data = recv_data(client, 4)
            print("after finding the length")
            if not len_data:
                break  # Client disconnected
            length = struct.unpack("!I", len_data)[0]
            print("before parsing the data")
            data = recv_data(client, length)
            print("after parsing the data")
            if (throlddata == data and olddata == data):
                print("two in a row")
            print(data)
            throlddata = olddata
            olddata = data

            note_data = data.decode('utf-8')
            # name, note_id, judgment
            print(note_data)
            # parse the note data
            # note = note_data.split(",")
            # print(note)
            # server.receive_note(note_data)

            # client.send(data) 

        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            break




def recv_data(client, length):
    # receive data from the client
    data = b""
    print(f"Receiving {length} bytes of data...")
    print(data)
    while len(data) < length:
        print("before packets")
        packet = client.recv(length - len(data))
        print("after packets")
        if not packet:
            print("before break")
            break
        print("before data +=")
        data += packet
        print("after data +=")
    print("outside of while")
    return data


if __name__ == "__main__":
    main()