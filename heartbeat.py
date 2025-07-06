import socket
import time
import sys
import common
import election

def monitor_server_health():
    """Monitor health of neighboring servers using heartbeat"""
    while True:
        # Create heartbeat socket
        heartbeat_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        heartbeat_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        heartbeat_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        heartbeat_socket.settimeout(1.0)
        
        # Get server ring and find next server to monitor
        server_ring = election.create_server_ring(common.active_servers)
        target_server = election.find_next_server(server_ring, common.my_ip, 'clockwise')
        
        if target_server and target_server != common.my_ip:
            time.sleep(common.HEARTBEAT_INTERVAL)
            
            try:
                # Send heartbeat to target server
                heartbeat_socket.connect((target_server, common.CHAT_PORT))
                print(f'[HEARTBEAT] Server {target_server} is alive', file=sys.stderr)
                
            except Exception:
                # Server failed to respond
                print(f'[HEARTBEAT] Server {target_server} failed to respond', file=sys.stderr)
                
                # Remove failed server from active list
                if target_server in common.active_servers:
                    common.active_servers.remove(target_server)
                
                # Check if failed server was the leader
                if common.current_leader == target_server:
                    print(f'[HEARTBEAT] Leader {common.current_leader} has failed', file=sys.stderr)
                    common.server_failure_detected = True
                    common.current_leader= None 
                    
                    # Elect new leader
                    common.current_leader = common.my_ip
                    common.network_topology_changed = True
                    #election.initiate_leader_election()
                else:
                    print(f'[HEARTBEAT] Non-leader server {target_server} has failed', file=sys.stderr)
                    common.server_failure_detected = True
            
            finally:
                heartbeat_socket.close()
        
        time.sleep(common.HEARTBEAT_INTERVAL)