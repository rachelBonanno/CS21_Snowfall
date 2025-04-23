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

    client_game = Client(name=name, gamestate=Gamestate.empty_gamestate(), stats=Stats.empty_stats(), starttime=future_time)
    client_game.set_socket(server_socket)  

    # gameplay time
    
    # Start threads for sending and receiving messages
    receive_thread = threading.Thread(target=receive_messages, args=[server_socket, name, client_game])
    send_thread = threading.Thread(target=send_messages, args=[server_socket, name, client_game])
    receive_thread.daemon = True
    send_thread.daemon = True

    receive_thread.start()
    send_thread.start()

    client_game.client_init()

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



    # while True:
    #     if int(round(time.time()*1000)) % 16 == 0:
    #         print(round(time.time()*1000))
    #         bytes = 15
    #         server_socket.send(struct.pack("!I", bytes))
    #         server_socket.send(f"{name}Hello, server!".encode()) 
    #         # wait for a hundredth of a second
    #         time.sleep(0.01)

    # # Close the connection
    # server_socket.close()


def receive_messages(server_socket, client_name, client_instance):
    while True:
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
            print(f"{client_name} received: {message}")
            # use to update the gamestate 
        except Exception as e:
            print(f"{client_name}: Error receiving message: {e}")
            break

def send_messages(server_socket, client_name, client):
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
    while True:
        # Check if the recent_id has changed
        if client.gamestate.recent_id != previous_id:
        # Update the previous_id to the new value
            previous_id = client.gamestate.recent_id

            # Get the recent_id and recent_judgment
            recent_id = client.gamestate.recent_id
            recent_judgment = client.gamestate.recent_judgment

            # Prepare the data to send
            data_to_send = f"{client_name}, {recent_id}, {recent_judgment}".encode() #TO DO: this needs to be recieved and we need to pick a correct format to send this data we def want the name of the client as well as the id of the the note and the judgment to be sent when the data is recieved im thinking the sever will comapare it with the other data to see if there is already a score i think we already have this fucntion some where so look before making it and then the data can be sent back to the clients with the correct judgment for that node that way it doesn't matter who the client is and they will just both update (this way we say fuck it to making life complicated and the code is just stream lined tis will remove checking who the client is)

            # Send the length of the data followed by the data itself
            server_socket.sendall(struct.pack("!I", len(data_to_send)))
            server_socket.sendall(data_to_send)
        else:
            break





if __name__ == "__main__":
    main()