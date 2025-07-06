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
election_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
    election_socket.bind(('', common.ELECTION_PORT))
    print(f'[ELECTION] Election socket bound to port {common.ELECTION_PORT}')
except Exception as e:
    print(f'[ELECTION] Error binding election socket: {e}')

def handle_election_messages():
    """Background thread to handle incoming election messages"""
    while True:
        try:
            election_socket.settimeout(1.0)
            data, sender_addr = election_socket.recvfrom(1024)
            if data:
                print(f'[ELECTION] Background handler received message from {sender_addr}')
                election_msg = pickle.loads(data)
                
                # Find next server in ring
                server_ring = create_server_ring(common.active_servers)
                next_server = find_next_server(server_ring, common.my_ip, 'clockwise')
                
                if next_server:
                    process_election_message(election_msg, (next_server, common.ELECTION_PORT))
                else:
                    print(f'[ELECTION] No next server found for message forwarding')
                    
        except socket.timeout:
            continue
        except Exception as e:
            print(f'[ELECTION] Background handler error: {e}')
            time.sleep(1.0)

def initiate_leader_election():
    """Start the leader election process"""
    print(f'[ELECTION] === STARTING LEADER ELECTION ===')
    print(f'[ELECTION] My IP: {common.my_ip}')
    print(f'[ELECTION] Active servers: {common.active_servers}')
    print(f'[ELECTION] Current leader: {common.current_leader}')
    print(f'[ELECTION] Election in progress: {common.election_in_progress}')
    
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
    print(f'[ELECTION] Set election_in_progress = True')
    
    server_ring = create_server_ring(common.active_servers)
    print(f'[ELECTION] Ring topology: {server_ring}')
    print(f'[ELECTION] Election started on {common.my_ip}:{common.ELECTION_PORT}')
    
    next_server = find_next_server(server_ring, common.my_ip, 'clockwise')
    print(f'[ELECTION] Next server in ring: {next_server}')
    
    if next_server and next_server != common.my_ip:
        print(f'[ELECTION] Sending election message to: {next_server}')
        election_msg = pickle.dumps([common.my_ip, False])
        print(f'[ELECTION] Election message content: [candidate={common.my_ip}, leader_confirmed=False]')
        election_socket.sendto(election_msg, (next_server, common.ELECTION_PORT))
        print(f'[ELECTION] Election message sent to {next_server}:{common.ELECTION_PORT}')
    else:
        # Only server in network
        common.current_leader = common.my_ip
        common.election_in_progress = False
        print(f'[ELECTION] Only server in network - Self-elected as leader: {common.current_leader}')
        return
    
    # Listen for election messages with timeout
    election_socket.settimeout(10.0)  # 10 second timeout
    election_start_time = time.time()
    print(f'[ELECTION] Listening for election messages with 10s timeout...')
    
    while True:
        try:
            # Check for election timeout
            if time.time() - election_start_time > 10.0:
                print(f'[ELECTION] Election timeout after 10 seconds, resetting election state')
                common.election_in_progress = False
                break
                
            print(f'[ELECTION] Waiting for election message...')
            data, sender_addr = election_socket.recvfrom(1024)
            if data:
                print(f'[ELECTION] Received election message from {sender_addr}')
                election_msg = pickle.loads(data)
                print(f'[ELECTION] Election message: {election_msg}')
                process_election_message(election_msg, (next_server, common.ELECTION_PORT))
        except socket.timeout:
            # Election timeout - reset state and break
            print(f'[ELECTION] Socket timeout - no election messages received, election failed')
            common.election_in_progress = False
            break
        except Exception as e:
            print(f'[ELECTION] Error during election: {e}')
            common.election_in_progress = False
            break
    
    print(f'[ELECTION] Election process ended. Final leader: {common.current_leader}')
    print(f'[ELECTION] === ELECTION COMPLETE ===\n')

def process_election_message(election_msg, next_server_addr):
    """Process incoming election messages"""
    candidate_ip = election_msg[0]
    leader_confirmed = election_msg[1]
    
    print(f'[ELECTION] Processing election message:')
    print(f'[ELECTION]   Candidate IP: {candidate_ip}')
    print(f'[ELECTION]   Leader confirmed: {leader_confirmed}')
    print(f'[ELECTION]   My IP: {common.my_ip}')
    print(f'[ELECTION]   Next server: {next_server_addr}')
    
    if candidate_ip < common.my_ip:
        # My IP is higher, forward my IP as candidate
        print(f'[ELECTION] My IP ({common.my_ip}) > candidate IP ({candidate_ip}) - forwarding my IP')
        new_msg = pickle.dumps([common.my_ip, leader_confirmed])
        election_socket.sendto(new_msg, next_server_addr)
        print(f'[ELECTION] Forwarded my IP to {next_server_addr}')
    
    elif candidate_ip > common.my_ip:
        # Forward the higher IP candidate
        print(f'[ELECTION] Candidate IP ({candidate_ip}) > my IP ({common.my_ip}) - forwarding candidate')
        election_socket.sendto(pickle.dumps(election_msg), next_server_addr)
        print(f'[ELECTION] Forwarded candidate {candidate_ip} to {next_server_addr}')
    
    elif candidate_ip == common.my_ip and not leader_confirmed:
        # Election message returned to me, I'm the leader
        print(f'[ELECTION] Election message returned to me - I am the leader!')
        leader_confirmed = True
        confirmation_msg = pickle.dumps([common.my_ip, leader_confirmed])
        election_socket.sendto(confirmation_msg, next_server_addr)
        print(f'[ELECTION] Sent leader confirmation to {next_server_addr}')
    
    elif candidate_ip == common.my_ip and leader_confirmed:
        # Leader confirmation complete
        print(f'[ELECTION] Leader confirmation received - election complete!')
        common.current_leader = common.my_ip
        common.election_in_progress = False
        print(f'[ELECTION] New leader elected: {common.current_leader}')
        return
    
    else:
        print(f'[ELECTION] Unexpected election message scenario - ignoring')