import socket
import time
import sys
import common
import election

def monitor_server_health():
    """Monitor health of neighboring servers using heartbeat"""
    while True:
        # Report current leader status every heartbeat
        print(f'[HEARTBEAT] === HEARTBEAT STATUS ===')
        print(f'[HEARTBEAT] Current leader: {common.current_leader}')
        print(f'[HEARTBEAT] My IP: {common.my_ip}')
        print(f'[HEARTBEAT] Active servers: {common.active_servers}')
        print(f'[HEARTBEAT] Election in progress: {common.election_in_progress}')
        
        # Create heartbeat socket
        heartbeat_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        heartbeat_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        heartbeat_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        heartbeat_socket.settimeout(1.0)
        
        # Get server ring and find next server to monitor
        server_ring = election.create_server_ring(common.active_servers)
        target_server = election.find_next_server(server_ring, common.my_ip, 'clockwise')
        
        if target_server and target_server != common.my_ip:
            print(f'[HEARTBEAT] Checking health of: {target_server}')
            time.sleep(common.HEARTBEAT_INTERVAL)
            
            try:
                # Send heartbeat to target server
                heartbeat_socket.connect((target_server, common.CHAT_PORT))
                print(f'[HEARTBEAT] Server {target_server} is alive')
                
            except Exception as e:
                # Server failed to respond
                print(f'[HEARTBEAT] Server {target_server} failed to respond: {e}')
                
                # Remove failed server from active list
                if target_server in common.active_servers:
                    common.active_servers.remove(target_server)
                    print(f'[HEARTBEAT] Removed {target_server} from active servers')
                
                # Check if failed server was the leader
                if common.current_leader == target_server:
                    print(f'[HEARTBEAT] Leader {common.current_leader} has failed - need new election')
                    common.server_failure_detected = True
                    common.current_leader = None 
                    
                    # Elect new leader
                    common.current_leader = common.my_ip
                    common.network_topology_changed = True
                    print(f'[HEARTBEAT] Temporarily set self as leader: {common.my_ip}')
                    #election.initiate_leader_election()
                else:
                    print(f'[HEARTBEAT] Non-leader server {target_server} has failed')
                    common.server_failure_detected = True
            
            finally:
                heartbeat_socket.close()
        else:
            print(f'[HEARTBEAT] No other servers to monitor')
        
        print(f'[HEARTBEAT] === END HEARTBEAT STATUS ===\n')
        time.sleep(common.HEARTBEAT_INTERVAL)