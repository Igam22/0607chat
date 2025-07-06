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

# Global variables for election management
election_receiver_socket = None
election_running = False

def initialize_election_receiver():
    """Initialize the election receiver socket"""
    global election_receiver_socket
    try:
        election_receiver_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        election_receiver_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        election_receiver_socket.bind(('', common.ELECTION_PORT))
        election_receiver_socket.settimeout(1.0)
        print(f'[ELECTION] Election receiver socket bound to port {common.ELECTION_PORT}')
        return True
    except Exception as e:
        print(f'[ELECTION] Error binding election receiver socket: {e}')
        return False

def handle_election_messages():
    """Background thread to handle incoming election messages"""
    global election_running
    
    if not initialize_election_receiver():
        print(f'[ELECTION] Failed to initialize election receiver')
        return
        
    print(f'[ELECTION] Background election handler started')
    
    while True:
        try:
            data, sender_addr = election_receiver_socket.recvfrom(1024)
            if data:
                print(f'[ELECTION] Background handler received message from {sender_addr}')
                election_msg = pickle.loads(data)
                
                # Only process if not actively running an election
                if not election_running:
                    print(f'[ELECTION] Processing message in background mode')
                    # Find next server in ring
                    server_ring = create_server_ring(common.active_servers)
                    next_server = find_next_server(server_ring, common.my_ip, 'clockwise')
                    
                    if next_server:
                        process_election_message(election_msg, next_server)
                    else:
                        print(f'[ELECTION] No next server found for message forwarding')
                else:
                    print(f'[ELECTION] Election in progress, background handler ignoring message')
                    
        except socket.timeout:
            continue
        except Exception as e:
            print(f'[ELECTION] Background handler error: {e}')
            time.sleep(1.0)

def initiate_leader_election():
    """Start the leader election process"""
    global election_running
    
    print(f'[ELECTION] === STARTING LEADER ELECTION ===')
    print(f'[ELECTION] My IP: {common.my_ip}')
    print(f'[ELECTION] Active servers: {common.active_servers}')
    print(f'[ELECTION] Current leader: {common.current_leader}')
    print(f'[ELECTION] Election in progress: {common.election_in_progress}')
    
    # Check if election is already in progress
    if common.election_in_progress or election_running:
        print(f'[ELECTION] Election already in progress, skipping...')
        return
    
    # Check if we already have a leader
    if common.current_leader is not None:
        print(f'[ELECTION] Leader already exists: {common.current_leader}')
        return
    
    # Set election flags
    common.election_in_progress = True
    election_running = True
    print(f'[ELECTION] Set election flags = True')
    
    server_ring = create_server_ring(common.active_servers)
    print(f'[ELECTION] Ring topology: {server_ring}')
    
    next_server = find_next_server(server_ring, common.my_ip, 'clockwise')
    print(f'[ELECTION] Next server in ring: {next_server}')
    
    if next_server and next_server != common.my_ip:
        # Create sender socket for sending election message
        sender_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        try:
            print(f'[ELECTION] Sending election message to: {next_server}')
            election_msg = pickle.dumps([common.my_ip, False])
            print(f'[ELECTION] Election message content: [candidate={common.my_ip}, leader_confirmed=False]')
            sender_socket.sendto(election_msg, (next_server, common.ELECTION_PORT))
            print(f'[ELECTION] Election message sent to {next_server}:{common.ELECTION_PORT}')
        except Exception as e:
            print(f'[ELECTION] Error sending election message: {e}')
            common.election_in_progress = False
            election_running = False
            return
        finally:
            sender_socket.close()
        
        # Wait for election completion by monitoring current_leader
        print(f'[ELECTION] Waiting for election completion...')
        election_start_time = time.time()
        
        while (time.time() - election_start_time) < 15.0:  # 15 second timeout
            time.sleep(0.1)
            
            # Check if leader was elected
            if common.current_leader is not None:
                print(f'[ELECTION] Leader elected: {common.current_leader}')
                break
                
            # Check if election is no longer in progress (completed or failed)
            if not common.election_in_progress:
                print(f'[ELECTION] Election completed without leader')
                break
        
        # Clean up election state
        election_running = False
        if common.current_leader is None:
            common.election_in_progress = False
            print(f'[ELECTION] Election timed out - no leader elected')
    else:
        # Only server in network
        common.current_leader = common.my_ip
        common.election_in_progress = False
        election_running = False
        print(f'[ELECTION] Only server in network - Self-elected as leader: {common.current_leader}')
    
    print(f'[ELECTION] Election process ended. Final leader: {common.current_leader}')
    print(f'[ELECTION] === ELECTION COMPLETE ===\n')

def process_election_message(election_msg, next_server_ip):
    """Process incoming election messages"""
    candidate_ip = election_msg[0]
    leader_confirmed = election_msg[1]
    
    print(f'[ELECTION] Processing election message:')
    print(f'[ELECTION]   Candidate IP: {candidate_ip}')
    print(f'[ELECTION]   Leader confirmed: {leader_confirmed}')
    print(f'[ELECTION]   My IP: {common.my_ip}')
    print(f'[ELECTION]   Next server: {next_server_ip}')
    
    # Create sender socket for forwarding messages
    sender_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    try:
        if candidate_ip < common.my_ip:
            # My IP is higher, forward my IP as candidate
            print(f'[ELECTION] My IP ({common.my_ip}) > candidate IP ({candidate_ip}) - forwarding my IP')
            new_msg = pickle.dumps([common.my_ip, leader_confirmed])
            sender_socket.sendto(new_msg, (next_server_ip, common.ELECTION_PORT))
            print(f'[ELECTION] Forwarded my IP to {next_server_ip}')
        
        elif candidate_ip > common.my_ip:
            # Forward the higher IP candidate
            print(f'[ELECTION] Candidate IP ({candidate_ip}) > my IP ({common.my_ip}) - forwarding candidate')
            sender_socket.sendto(pickle.dumps(election_msg), (next_server_ip, common.ELECTION_PORT))
            print(f'[ELECTION] Forwarded candidate {candidate_ip} to {next_server_ip}')
        
        elif candidate_ip == common.my_ip and not leader_confirmed:
            # Election message returned to me, I'm the leader
            print(f'[ELECTION] Election message returned to me - I am the leader!')
            leader_confirmed = True
            confirmation_msg = pickle.dumps([common.my_ip, leader_confirmed])
            sender_socket.sendto(confirmation_msg, (next_server_ip, common.ELECTION_PORT))
            print(f'[ELECTION] Sent leader confirmation to {next_server_ip}')
        
        elif candidate_ip == common.my_ip and leader_confirmed:
            # Leader confirmation complete
            print(f'[ELECTION] Leader confirmation received - election complete!')
            common.current_leader = common.my_ip
            common.election_in_progress = False
            print(f'[ELECTION] New leader elected: {common.current_leader}')
            return
        
        else:
            print(f'[ELECTION] Unexpected election message scenario - ignoring')
            
    except Exception as e:
        print(f'[ELECTION] Error processing election message: {e}')
    finally:
        sender_socket.close()