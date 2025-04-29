# CS21_Snowfall
## Files:


### For user use:
 
- snowfall_client.py: \
    Is run to start the client side of the program- handles all concurrency and
message passing and receiving on the client’s side.

- snowfall_server.py: \
    Is run to start the server side of the program- handles all concurrency and
message passing and receiving on the server’s side.

- osurip.py: \
    Can be used to create a new .chart file using .osu files.

### Backend:


- client.py: \
    The Client class. Handles running and logic of the game.

- server.py: \
    The Server class. Stores data that the clients give it in regards to the 
    game.

- gamestate.py: \
    The Gamestate class. Holds time-sensitive data about the game. Is passed 
between the client and server for communication.

- stats.py: \
    The stats class. Holds data that is only relevant until the end of the game
for the final score and final combo. Is printed to the server’s terminal at the
end of the game.


## Setup & Gameplay:


- Start the server: \
`python .\snowfall_server.py --host "{Server IP here}" --port {port number here}
 --chart "{chart file here}"`

- Start a client: \
`python .\snowfall_client.py --host "{Server IP here}" --port {port number here}
 --chart "{chart file here}" --name "{name here}"`


Use keys `QWER` and `OP[]` to play!