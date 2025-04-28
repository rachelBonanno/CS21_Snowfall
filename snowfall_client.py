# snowfall_client.py
# CS21 Concurrent Programming
# Final Project -- Snowfall
# Team Snowfall -- Stephanie Wilson, Rachel Bonanno, Justin Millette
# 4/28/25
#
# This file defines the client-side, server-concurrency-related processing 
# during the runtime of Snowfall. It first connects to a server with the given
# host and port information, with the name given as a command-line argument.
# It passes the given chart to the gameplay logic, and then starts gameplay at 
# the server-designated time.
#
# For information on running this code, see the README.

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

def main():
    # create a socket object
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # parse command-line arguments
    parser = argparse.ArgumentParser(description="Client for connecting to a server.")
    parser.add_argument('--host', type=str, required=True, help='Server hostname or IP address')
    parser.add_argument('--port', type=int, required=True, help='Server port number')
    parser.add_argument('--chart', type=str, default='./charts/basic.chart', help='Path to the chart file.')
    parser.add_argument('--name', type=str, required=True, help='Client name')
    args = parser.parse_args()

    # assign host and port from arguments
    host = args.host
    port = args.port
    name = args.name
    chartfile = args.chart

    stop_event = threading.Event()

    # connect to the server
    try:
        server_socket.connect((host, port))
        print(f"Connected to server at {host}:{port}")
    except socket.error as e:
        print(f"Error connecting to server at {host}:{port}: {e}", file=sys.stderr)

    # receive connection response from server
    data = server_socket.recv(1024) 

    # send name length and name to the server
    name_bytes = name.encode()
    server_socket.send(struct.pack("!I", len(name_bytes)))  
    server_socket.send(name_bytes)  

    # receive acknowledgment for connection
    data = server_socket.recv(1024)  
    server_socket.send(b"ACK")

    # ping for latency
    data = server_socket.recv(5)  
    if data:
        server_socket.send(b"pong!")

    # receive the future time from the server
    data = server_socket.recv(8)  
    if data:
        future_time = struct.unpack("!d", data)[0]
        print(f"Received future time: {future_time}")
    server_socket.send(b"ACK")

    
    # create client object (runs game)
    client_game = Client(name=name, gamestate=Gamestate.empty_gamestate(), stats=Stats.empty_stats(), starttime=future_time)
    client_game.set_socket(server_socket)  
    
    # start threads for sending and receiving messages
    receive_thread = threading.Thread(target=receive_messages, args=[server_socket, name, client_game, stop_event])
    send_thread = threading.Thread(target=send_messages, args=[server_socket, name, client_game, stop_event])
    # this helps prevent errors with sockets passing messages around
    receive_thread.daemon = True
    send_thread.daemon = True
    # start threads
    receive_thread.start()
    send_thread.start()
    # gameplay!
    # returns when song is over (really, when we reach "end" time in the chart)
    client_game.client_init(chartfile)
    # tell listener and sender threads to wrap up
    stop_event.set()
    # end threads
    server_socket.close()
    receive_thread.join()
    send_thread.join()



def receive_messages(server_socket, client_name, client_instance, stop_event):
    """
    Threading function to receive messages from the server.
    messsage receiving follows this pattern:
        - recv waits for 4 byte int indicating how much data to receive
        - then we recv again and wait for that much data
        - we split up that message (which is always a note confirmation from the server)
        - use that to call the gameplay client's "receive_hit_confirmation" method
        - repeat
    This repeats until told to stop by "stop_event." If any recv fails, this is because
    the server has stopped for some reason. In that case we break and tell all threads to quit.
    """
    while not stop_event.is_set(): # go until told to stop
        try:
            len_data_bytes = server_socket.recv(4)
            if not len_data_bytes:
                print(f"{client_name}: Connection to server closed (receiving).")
                stop_event.set()
                break
            message_length = struct.unpack("!I", len_data_bytes)[0]
            message_bytes = server_socket.recv(message_length)
            if not message_bytes:
                print(f"{client_name}: Connection to server closed (receiving).")
                stop_event.set()
                break
            message = message_bytes.decode('utf-8')
            try:
                _, note_id, note_judgment = message.split(", ") # first split is client id, which we don't care about
                note_id = int(note_id.strip())
                note_judgment = note_judgment.strip()
            except ValueError as e:
                print(f"Error parsing message: {e}", file=sys.stderr)
                continue
            client_instance.receive_hit_confirmation(note_id, note_judgment)
        except Exception as e:
            msg = str(e)
            if "established connection was aborted" in msg: # server has stopped
                print(f"The server has stopped. Closing client...")
                client_instance.gamestate.outbox.put(None)
            else:
                print(f"{client_name}: Error receiving message: {e}")
            break

def send_messages(server_socket, client_name, client, stop_event):
    """
    Threading function to send messages to the server.
    messsage sending follows this pattern:
        - whenever 
        - send 4 byte int indicating how much data to receive
        - send that much data
        - we split up that message (which is always a note confirmation from the server)
        - use that to call the gameplay client's "receive_hit_confirmation" method
        - repeat
    This repeats until told to stop by "stop_event." If any recv fails, this is because
    the server has stopped for some reason. In that case we break and tell all threads to quit.
    """
    while not stop_event.is_set():
        # Check if the recent_id has changed and hasn't been sent before
        try: 
            item = client.gamestate.outbox.get()
            if item is None: # quit
                break
            note_id, judgment = item # otherwise parse note

            # encode data
            data_to_send = f"{client_name}, {note_id}, {judgment}".encode()

            # send the length of the data followed by the data itself
            server_socket.sendall(struct.pack("!I", len(data_to_send)))
            server_socket.sendall(data_to_send)
            # done with task in queue
            client.gamestate.outbox.task_done() 
        except Exception as e:
            print(f"Error sending message: {e}")
            break

if __name__ == "__main__":
    main()