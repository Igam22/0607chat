import socket
import pickle
import time
import common

def create_server_ring(server_list):
    """Create a sorted ring of servers based on IP addresses"""
    binary_ips = sorted([socket.inet_aton(ip) for ip in server_list])
    sorted_ips = [socket.inet_ntoa(binary_ip) for binary_ip in binary_ips]
    return sorted_ips

def find_next_server(ring, current_ip, direction='clockwise'):
    """Find the next server in the ring"""
    try:
        current_index = ring.index(current_ip)
        if direction == 'clockwise':
            next_index = (current_index + 1) % len(ring)
        else:
            next_index = (current_index - 1) % len(ring)
        return ring[next_index]
    except ValueError:
        return None

# Election socket
election_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
election_socket.bind(('', common.ELECTION_PORT))

def initiate_leader_election():
    """Start the leader election process"""
    # Check if election is already in progress
    if common.election_in_progress:
        print(f'[ELECTION] Election already in progress, skipping...')
        return
    
    # Check if we already have a leader
    if common.current_leader is not None:
        print(f'[ELECTION] Leader already exists: {common.current_leader}')
        return
    
    # Set election in progress flag
    common.election_in_progress = True
    
    server_ring = create_server_ring(common.active_servers)
    print(f'[ELECTION] Ring topology: {server_ring}')
    print(f'[ELECTION] Election started on {common.my_ip}:{common.ELECTION_PORT}')
    
    next_server = find_next_server(server_ring, common.my_ip, 'clockwise')
    
    if next_server and next_server != common.my_ip:
        print(f'[ELECTION] Next server in ring: {next_server}')
        election_msg = pickle.dumps([common.my_ip, False])
        election_socket.sendto(election_msg, (next_server, common.ELECTION_PORT))
    else:
        # Only server in network
        common.current_leader = common.my_ip
        common.election_in_progress = False
        print(f'[ELECTION] Self-elected as leader: {common.current_leader}')
        return
    
    # Listen for election messages with timeout
    election_socket.settimeout(10.0)  # 10 second timeout
    election_start_time = time.time()
    
    while True:
        try:
            # Check for election timeout
            if time.time() - election_start_time > 10.0:
                print(f'[ELECTION] Election timeout, resetting election state')
                common.election_in_progress = False
                break
                
            data, sender_addr = election_socket.recvfrom(1024)
            if data:
                election_msg = pickle.loads(data)
                process_election_message(election_msg, (next_server, common.ELECTION_PORT))
        except socket.timeout:
            # Election timeout - reset state and break
            print(f'[ELECTION] No election messages received, election failed')
            common.election_in_progress = False
            break
        except Exception as e:
            print(f'[ELECTION] Error: {e}')
            common.election_in_progress = False
            break

def process_election_message(election_msg, next_server_addr):
    """Process incoming election messages"""
    candidate_ip = election_msg[0]
    leader_confirmed = election_msg[1]
    
    if candidate_ip < common.my_ip:
        # My IP is higher, forward my IP as candidate
        new_msg = pickle.dumps([common.my_ip, leader_confirmed])
        election_socket.sendto(new_msg, next_server_addr)
    
    elif candidate_ip > common.my_ip:
        # Forward the higher IP candidate
        election_socket.sendto(pickle.dumps(election_msg), next_server_addr)
    
    elif candidate_ip == common.my_ip and not leader_confirmed:
        # Election message returned to me, I'm the leader
        leader_confirmed = True
        confirmation_msg = pickle.dumps([common.my_ip, leader_confirmed])
        election_socket.sendto(confirmation_msg, next_server_addr)
    
    elif candidate_ip == common.my_ip and leader_confirmed:
        # Leader confirmation complete
        common.current_leader = common.my_ip
        common.election_in_progress = False
        print(f'[ELECTION] New leader elected: {common.current_leader}')
        return