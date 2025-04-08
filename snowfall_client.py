import socket
import argparse
import sys


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

    # Send name to the server
    server_socket.send(name.encode())


    # Receive a response from the server
    data = server_socket.recv(1024)
    print('Received', repr(data.decode()))

    # Close the connection
    server_socket.close()


if __name__ == "__main__":
    main()