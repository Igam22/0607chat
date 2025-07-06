import socket
import time
import sys
import common
import bullyelection

def monitor_server_health():
    """Monitor health of neighboring servers using heartbeat"""
    while True:
        # Report current leader status every heartbeat
        print(f'[HEARTBEAT] === HEARTBEAT STATUS ===')
        print(f'[HEARTBEAT] Current leader: {common.current_leader}')
        print(f'[HEARTBEAT] My IP: {common.my_ip}')
        print(f'[HEARTBEAT] Active servers: {common.active_servers}')
        print(f'[HEARTBEAT] Election in progress: {common.election_in_progress}')
        
        # Show if I think I'm the leader
        if common.current_leader == common.my_ip:
            print(f'[HEARTBEAT] *** I AM THE LEADER ***')
        else:
            print(f'[HEARTBEAT] I am NOT the leader')
        
        # Create heartbeat socket
        heartbeat_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        heartbeat_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        heartbeat_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        heartbeat_socket.settimeout(1.0)
        
        # Monitor all other servers (not just next in ring)
        other_servers = [server for server in common.active_servers if server != common.my_ip]
        
        if not other_servers:
            print(f'[HEARTBEAT] No other servers to monitor')
        else:
            for target_server in other_servers:
                print(f'[HEARTBEAT] Checking health of: {target_server}')
                
                try:
                    # Create new socket for each check
                    check_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    check_socket.settimeout(1.0)
                    check_socket.connect((target_server, common.CHAT_PORT))
                    print(f'[HEARTBEAT] Server {target_server} is alive')
                    check_socket.close()
                    
                except Exception as e:
                    # Server failed to respond
                    print(f'[HEARTBEAT] Server {target_server} failed to respond: {e}')
                    
                    # Remove failed server from active list
                    if target_server in common.active_servers:
                        common.active_servers.remove(target_server)
                        print(f'[HEARTBEAT] Removed {target_server} from active servers')
                        
                        # Check if failed server was the leader
                        if common.current_leader == target_server:
                            print(f'[HEARTBEAT] Leader {target_server} has failed - triggering bully election')
                            common.server_failure_detected = True
                            common.current_leader = None
                            
                            # Trigger bully election immediately
                            common.create_thread(bullyelection.initiate_bully_election)
                        else:
                            print(f'[HEARTBEAT] Non-leader server {target_server} has failed')
                            # Still trigger election as network topology changed
                            print(f'[HEARTBEAT] Network topology changed - triggering bully election')
                            common.create_thread(bullyelection.trigger_election_if_needed)
                            
                        common.server_failure_detected = True
                        common.network_topology_changed = True
        
        # Close the main heartbeat socket
        heartbeat_socket.close()
        
        print(f'[HEARTBEAT] === END HEARTBEAT STATUS ===\n')
        time.sleep(common.HEARTBEAT_INTERVAL)