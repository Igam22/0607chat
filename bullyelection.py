import socket
import pickle
import time
import threading
import common

# Bully Election Message Types
class MessageType:
    ELECTION = 'ELECTION'
    OK = 'OK'
    COORDINATOR = 'COORDINATOR'

# Global variables for bully election management
election_receiver_socket = None
election_in_progress = False
election_lock = threading.Lock()
received_ok_responses = []

def get_server_id(ip_address):
    """Convert IP address to a comparable server ID"""
    # Convert IP to integer for comparison (higher IP = higher priority)
    return socket.inet_aton(ip_address)

def get_higher_servers():
    """Get list of servers with higher IDs than current server"""
    my_id = get_server_id(common.my_ip)
    higher_servers = []
    
    for server_ip in common.active_servers:
        if server_ip != common.my_ip:
            server_id = get_server_id(server_ip)
            if server_id > my_id:
                higher_servers.append(server_ip)
    
    return higher_servers

def get_lower_servers():
    """Get list of servers with lower IDs than current server"""
    my_id = get_server_id(common.my_ip)
    lower_servers = []
    
    for server_ip in common.active_servers:
        if server_ip != common.my_ip:
            server_id = get_server_id(server_ip)
            if server_id < my_id:
                lower_servers.append(server_ip)
    
    return lower_servers

def initialize_bully_election_receiver():
    """Initialize the bully election receiver socket"""
    global election_receiver_socket
    try:
        election_receiver_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        election_receiver_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        election_receiver_socket.bind(('', common.ELECTION_PORT))
        election_receiver_socket.settimeout(1.0)
        print(f'[BULLY] Election receiver socket bound to port {common.ELECTION_PORT}')
        return True
    except Exception as e:
        print(f'[BULLY] Error binding election receiver socket: {e}')
        return False

def send_election_message(target_ip, msg_type, data=None):
    """Send election message to target server"""
    try:
        sender_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        message = {
            'type': msg_type,
            'sender': common.my_ip,
            'data': data
        }
        
        serialized_msg = pickle.dumps(message)
        sender_socket.sendto(serialized_msg, (target_ip, common.ELECTION_PORT))
        print(f'[BULLY] Sent {msg_type} message to {target_ip}')
        sender_socket.close()
        return True
    except Exception as e:
        print(f'[BULLY] Error sending {msg_type} message to {target_ip}: {e}')
        return False

def handle_bully_election_messages():
    """Background thread to handle incoming bully election messages"""
    global election_in_progress, received_ok_responses
    
    if not initialize_bully_election_receiver():
        print(f'[BULLY] Failed to initialize bully election receiver')
        return
        
    print(f'[BULLY] Background bully election handler started')
    
    while True:
        try:
            data, sender_addr = election_receiver_socket.recvfrom(1024)
            if data:
                message = pickle.loads(data)
                sender_ip = message['sender']
                msg_type = message['type']
                
                print(f'[BULLY] === RECEIVED {msg_type} MESSAGE ===')
                print(f'[BULLY] From: {sender_ip}')
                print(f'[BULLY] My IP: {common.my_ip}')
                print(f'[BULLY] Current leader: {common.current_leader}')
                
                if msg_type == MessageType.ELECTION:
                    handle_election_message(sender_ip)
                elif msg_type == MessageType.OK:
                    handle_ok_message(sender_ip)
                elif msg_type == MessageType.COORDINATOR:
                    handle_coordinator_message(sender_ip)
                else:
                    print(f'[BULLY] Unknown message type: {msg_type}')
                    
        except socket.timeout:
            continue
        except Exception as e:
            print(f'[BULLY] Background handler error: {e}')
            time.sleep(1.0)

def handle_election_message(sender_ip):
    """Handle incoming ELECTION message"""
    print(f'[BULLY] Processing ELECTION message from {sender_ip}')
    
    # Send OK response
    send_election_message(sender_ip, MessageType.OK)
    
    # Start my own election if I have higher priority
    my_id = get_server_id(common.my_ip)
    sender_id = get_server_id(sender_ip)
    
    if my_id > sender_id:
        print(f'[BULLY] My ID ({common.my_ip}) > sender ID ({sender_ip}), starting my own election')
        initiate_bully_election()

def handle_ok_message(sender_ip):
    """Handle incoming OK message"""
    global received_ok_responses
    print(f'[BULLY] Received OK from {sender_ip}')
    
    with election_lock:
        if sender_ip not in received_ok_responses:
            received_ok_responses.append(sender_ip)

def handle_coordinator_message(sender_ip):
    """Handle incoming COORDINATOR message"""
    global election_in_progress
    
    print(f'[BULLY] Received COORDINATOR message from {sender_ip}')
    
    # Accept the new coordinator
    with election_lock:
        common.current_leader = sender_ip
        election_in_progress = False
        
    print(f'[BULLY] New leader accepted: {sender_ip}')

def initiate_bully_election():
    """Start the Bully Algorithm election process"""
    global election_in_progress, received_ok_responses
    
    print(f'[BULLY] === STARTING BULLY ELECTION ===')
    print(f'[BULLY] My IP: {common.my_ip}')
    print(f'[BULLY] Active servers: {common.active_servers}')
    print(f'[BULLY] Current leader: {common.current_leader}')
    
    with election_lock:
        if election_in_progress:
            print(f'[BULLY] Election already in progress, skipping...')
            return
        
        election_in_progress = True
        received_ok_responses = []
    
    print(f'[BULLY] Set election_in_progress = True')
    
    # Get servers with higher IDs
    higher_servers = get_higher_servers()
    print(f'[BULLY] Higher priority servers: {higher_servers}')
    
    # Debug: Show all server IDs for comparison
    print(f'[BULLY] Server priority comparison:')
    my_id = get_server_id(common.my_ip)
    print(f'[BULLY]   My ID: {common.my_ip} = {my_id}')
    for server in common.active_servers:
        if server != common.my_ip:
            server_id = get_server_id(server)
            comparison = "HIGHER" if server_id > my_id else "LOWER"
            print(f'[BULLY]   {server} = {server_id} ({comparison})')
    
    if not higher_servers:
        # No higher servers, I am the coordinator
        print(f'[BULLY] No higher priority servers found - declaring myself leader')
        declare_coordinator()
        return
    
    # Send ELECTION messages to all higher servers
    print(f'[BULLY] Sending ELECTION messages to higher priority servers: {higher_servers}')
    sent_count = 0
    for server_ip in higher_servers:
        if send_election_message(server_ip, MessageType.ELECTION):
            sent_count += 1
        else:
            print(f'[BULLY] Failed to send ELECTION message to {server_ip}')
    
    print(f'[BULLY] Successfully sent ELECTION messages to {sent_count}/{len(higher_servers)} servers')
    
    if sent_count == 0:
        print(f'[BULLY] Could not contact any higher priority servers - declaring myself leader')
        declare_coordinator()
        return
    
    # Wait for OK responses
    print(f'[BULLY] Waiting for OK responses (5s timeout)...')
    timeout = 5.0  # 5 second timeout
    start_time = time.time()
    
    while (time.time() - start_time) < timeout:
        time.sleep(0.1)
        
        with election_lock:
            # Check if we received any OK responses
            if received_ok_responses:
                print(f'[BULLY] Received OK responses from: {received_ok_responses}')
                print(f'[BULLY] Higher priority server is handling election, stepping back')
                election_in_progress = False
                return
    
    # No OK responses received, I am the coordinator
    print(f'[BULLY] Timeout reached - no OK responses received after 5 seconds')
    print(f'[BULLY] Declaring myself leader since higher priority servers did not respond')
    declare_coordinator()

def declare_coordinator():
    """Declare myself as the coordinator"""
    global election_in_progress
    
    print(f'[BULLY] === DECLARING COORDINATOR ===')
    
    with election_lock:
        common.current_leader = common.my_ip
        election_in_progress = False
    
    print(f'[BULLY] I am the new leader: {common.my_ip}')
    
    # Send COORDINATOR messages to all lower servers
    lower_servers = get_lower_servers()
    print(f'[BULLY] Sending COORDINATOR messages to: {lower_servers}')
    
    for server_ip in lower_servers:
        send_election_message(server_ip, MessageType.COORDINATOR)
    
    print(f'[BULLY] === COORDINATOR DECLARATION COMPLETE ===\n')

def trigger_election_if_needed():
    """Trigger election if no leader exists or if I have higher priority than current leader"""
    print(f'[BULLY] === CHECKING IF ELECTION NEEDED ===')
    print(f'[BULLY] My IP: {common.my_ip}')
    print(f'[BULLY] Current leader: {common.current_leader}')
    print(f'[BULLY] Active servers: {common.active_servers}')
    
    if common.current_leader is None:
        print(f'[BULLY] No leader exists - triggering election')
        initiate_bully_election()
    elif common.current_leader not in common.active_servers:
        print(f'[BULLY] Current leader {common.current_leader} not in active servers - triggering election')
        common.current_leader = None
        initiate_bully_election()
    else:
        # Check if I have higher priority than current leader
        my_id = get_server_id(common.my_ip)
        leader_id = get_server_id(common.current_leader)
        
        print(f'[BULLY] Comparing priorities:')
        print(f'[BULLY]   My priority: {common.my_ip} = {my_id}')
        print(f'[BULLY]   Leader priority: {common.current_leader} = {leader_id}')
        
        if my_id > leader_id:
            print(f'[BULLY] I have higher priority than current leader - challenging leadership!')
            initiate_bully_election()
        else:
            print(f'[BULLY] Current leader has higher or equal priority - no election needed')
    
    print(f'[BULLY] === ELECTION CHECK COMPLETE ===\n')

def get_election_status():
    """Get current election status for debugging"""
    return {
        'election_in_progress': election_in_progress,
        'current_leader': common.current_leader,
        'active_servers': common.active_servers,
        'my_ip': common.my_ip,
        'higher_servers': get_higher_servers(),
        'lower_servers': get_lower_servers()
    }