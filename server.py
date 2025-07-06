import sys
import time
import common
import chat_handler
import discovery
import election
import heartbeat

def display_network_status():
    """Display current network status"""
    print(f'[NETWORK] Servers: {common.active_servers} => Leader: {common.current_leader}')
    print(f'[NETWORK] Connected clients: {len(common.connected_clients)}')

def main():
    """Main server application"""
    print(f'[SERVER] Starting server on {common.my_ip}')
    
    # Initialize discovery service
    discovery.initialize_discovery_receiver()
    
    # Start chat server in background
    common.create_thread(chat_handler.start_chat_server)
    
    # Announce server presence
    server_discovered = discovery.announce_server_presence()
    
    # Add self to server list
    if common.my_ip not in common.active_servers:
        common.active_servers.append(common.my_ip)
    
    display_network_status()
    
    # Start leader election
    election.initiate_leader_election()
    
    # Start background services
    common.create_thread(discovery.handle_discovery_messages)
    common.create_thread(heartbeat.monitor_server_health)
    
    # Main server loop
    while True:
        try:
            # Handle leader responsibilities
            if common.current_leader == common.my_ip and (common.network_topology_changed or common.server_failure_detected):
                discovery.announce_server_presence()
                common.server_failure_detected = False
                common.network_topology_changed = False
                display_network_status()
            
            # Handle topology changes for non-leaders
            if common.current_leader != common.my_ip and common.network_topology_changed:
                common.network_topology_changed = False
                display_network_status()
            
            # Handle new server joining
            if common.current_leader == common.my_ip and common.new_server_joined:
                common.new_server_joined = False
                display_network_status()
            
            # Handle client disconnections
            if common.client_disconnected:
                common.client_disconnected = False
                print(f'[NETWORK] Connected clients: {len(common.connected_clients)}')
            
            time.sleep(0.1)  # Small delay to prevent busy waiting
            
        except KeyboardInterrupt:
            print(f'\n[SERVER] Shutting down server on {common.my_ip}:{common.CHAT_PORT}')
            if common.server_socket:
                common.server_socket.close()
            sys.exit(0)

if __name__ == '__main__':
    main()
    if common.current_leader is None and common.server_failure_detected:
        print('[SERVER] Leader failure detected. Initiating new election.')

    # Zurücksetzen des Flags, um Endlosschleifen zu vermeiden
        common.server_failure_detected = False 

    # Starten Sie die Wahl. Diese Funktion blockiert, bis ein Leader gewählt ist.
    # Danach wird die Hauptschleife fortgesetzt.
        election.initiate_leader_election()

    # Nachdem ein neuer Leader gewählt wurde, den neuen Zustand bekannt geben.
        common.network_topology_changed = True

# ... Rest der Schleife
