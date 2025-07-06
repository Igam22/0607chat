import socket
import random
import pickle
import os
import time
import common
import discovery

# Get username from user
username = input('Enter your username to join the chat: ')

# Create client socket with random port
client_port = random.randint(7000, 9999)
client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def send_chat_messages():
    """Handle sending chat messages"""
    while True:
        try:
            user_input = input("")
            if user_input.lower() == '/quit':
                # ...
                break

            message = pickle.dumps([common.ChatType.MESSAGE.value, username, user_input])

            # Wenn kein Leader bekannt ist, versuche zu verbinden
            if not common.current_leader:
                print("\n[CLIENT] Leader connection lost. Attempting to reconnect...")
                if not connect_to_server():
                    time.sleep(3) # Warte kurz vor dem nächsten Versuch
                    continue # Gehe zum nächsten Schleifendurchlauf
                else:
                     print("\n[CLIENT] Reconnected successfully to new leader!")

            leader_addr = (str(common.current_leader), common.CHAT_PORT)
            client_socket.sendto(message, leader_addr)

        except Exception as e:
            # Bei einem Fehler annehmen, dass der Leader ausgefallen ist.
            print(f'[ERROR] Failed to send message: {e}. Leader might be down.')
            common.current_leader = None # Leader-Information zurücksetzen
            # Die Schleife wird fortgesetzt und löst den Wiederverbindungsversuch aus

def receive_chat_messages():
    """Handle receiving chat messages"""
    while True:
        try:
            data, server_addr = client_socket.recvfrom(1024)
            print(f'{data.decode(common.ENCODING)}')
            
            # Check for server disconnection
            if not data:
                print("\n[ERROR] Chat server is unavailable.")
                print("Attempting to reconnect in 3 seconds...")
                client_socket.close()
                time.sleep(3)
                # Attempt to reconnect
                connect_to_server()
                
        # In client.py, in receive_chat_messages()
# ...
        except Exception as e:
            print(f'[ERROR] Error receiving message: {e}. Connection may be lost.')
            common.current_leader = None # Leader-Information zurücksetzen, um Neuverbindung zu erzwingen
            time.sleep(3) # Optional eine kleine Pause
            # Die Schleife könnte hier auch neu gestartet oder beendet werden, 
            # aber das Setzen von current_leader auf None ist der entscheidende Schritt.

def connect_to_server():
    """Connect to the chat server"""
    # Initialize discovery
    discovery.initialize_discovery_receiver()
    
    # Find the current leader
    leader_found = discovery.find_chat_leader(username)
    
    if leader_found:
        print(f'[CLIENT] Connected to leader: {common.current_leader}')
        leader_addr = (common.current_leader, common.CHAT_PORT)
        
        # Bind client socket
        client_socket.bind(('', client_port))
        
        # Send connection message
        connect_msg = pickle.dumps([common.ChatType.CONNECT.value, username, ''])
        client_socket.sendto(connect_msg, leader_addr)
        
        return True
    else:
        print("[ERROR] No chat server available. Please try again later.")
        return False

def main():
    """Main client application"""
    try:
        # Connect to server
        if not connect_to_server():
            os._exit(1)
        
        # Start message handling threads
        common.create_thread(send_chat_messages)
        common.create_thread(receive_chat_messages)
        
        # Keep client running
        while True:
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print(f"\n[CLIENT] {username} left the chat")
        
        # Send disconnect message
        try:
            leader_addr = (str(common.current_leader), common.CHAT_PORT)
            disconnect_msg = pickle.dumps([common.ChatType.DISCONNECT.value, username, 'left the chat'])
            client_socket.sendto(disconnect_msg, leader_addr)
        except:
            pass
        
        client_socket.close()
        os._exit(0)

if __name__ == '__main__':
    main()