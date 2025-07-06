import socket
import struct
import pickle
import time
import common
import bullyelection

# Multicast sender socket
sender_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sender_socket.settimeout(2)
ttl = struct.pack('b', 1)
sender_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

# Multicast receiver socket
receiver_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def initialize_discovery_receiver():
    """Initialize multicast receiver for discovery messages"""
    receiver_socket.bind(('', common.DISCOVERY_PORT))
    
    # Join multicast group
    group = socket.inet_aton(common.DISCOVERY_GROUP_IP)
    mreq = struct.pack('4sL', group, socket.INADDR_ANY)
    receiver_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

def announce_server_presence():
    """Announce server presence to discover other servers"""
    time.sleep(0.5)  # Small delay before announcing
    
    discovery_msg = pickle.dumps([
        common.MessageType.SERVER_DISCOVERY.value,
        common.active_servers,
        common.connected_clients,
        common.current_leader,
        ''
    ])
    
    sender_socket.sendto(discovery_msg, common.DISCOVERY_ADDRESS)
    
    try:
        # Wait for response from existing servers
        response, addr = sender_socket.recvfrom(1024)
        return True
    except socket.timeout:
        return False

def find_chat_leader(username):
    """Client function to find the chat leader"""
    discovery_msg = pickle.dumps([
        common.MessageType.CLIENT_DISCOVERY.value,
        '',
        common.connected_clients,
        '',
        username
    ])
    
    sender_socket.sendto(discovery_msg, common.DISCOVERY_ADDRESS)
    
    try:
        response, addr = sender_socket.recvfrom(1024)
        leader_info = pickle.loads(response)[0]
        common.current_leader = leader_info
        return True
    except socket.timeout:
        return False

def handle_discovery_messages():
    """Handle incoming discovery messages"""
    while True:
        try:
            data, sender_addr = receiver_socket.recvfrom(1024)
            message = common.deserialize_discovery_message(data)
            
            if message.msg_type == common.MessageType.SERVER_DISCOVERY.value:
                print(f'[DISCOVERY] Server {sender_addr} joining network: {common.DISCOVERY_ADDRESS}')
                
                # Check if this is the first server in our network (not sender's)
                if len(common.active_servers) <= 1:
                    # We are alone or just have ourselves, add the new server
                    if sender_addr[0] not in common.active_servers:
                        common.active_servers.append(sender_addr[0])
                        print(f'[DISCOVERY] Added new server to network: {sender_addr[0]}')
                        # Trigger election when new server joins
                        print(f'[DISCOVERY] New server joined - triggering bully election')
                        common.create_thread(bullyelection.trigger_election_if_needed)
                    receiver_socket.sendto(b'SERVER_JOINED', sender_addr)
                    common.network_topology_changed = True
                
                elif message.leader_ip and common.current_leader != common.my_ip:
                    # Update from existing leader
                    common.active_servers = message.server_list
                    common.connected_clients = message.client_list
                    common.current_leader = message.leader_ip
                    common.election_in_progress = False  # Cancel any ongoing election
                    receiver_socket.sendto(b'SERVER_JOINED', sender_addr)
                    common.network_topology_changed = True
                    common.new_server_joined = True
                    print(f'[DISCOVERY] Updated leader information: {message.leader_ip}')
                
                elif common.current_leader == common.my_ip:
                    # We are the leader, add new server and update network
                    if sender_addr[0] not in common.active_servers:
                        common.active_servers.append(sender_addr[0])
                        print(f'[DISCOVERY] Leader added new server: {sender_addr[0]}')
                        # New server with potentially higher priority joined - trigger election
                        print(f'[DISCOVERY] New server joined while I am leader - triggering bully election')
                        common.create_thread(bullyelection.trigger_election_if_needed)
                    
                    # Send current network state to new server
                    response_msg = pickle.dumps([
                        common.MessageType.SERVER_DISCOVERY.value,
                        common.active_servers,
                        common.connected_clients,
                        common.current_leader,
                        ''
                    ])
                    receiver_socket.sendto(response_msg, sender_addr)
                    common.network_topology_changed = True
                    common.new_server_joined = True
            
            elif message.msg_type == common.MessageType.CLIENT_DISCOVERY.value:
                print(f'[DISCOVERY] Client {sender_addr} - {message.client_name} requesting leader')
                # Send leader information to client
                leader_msg = pickle.dumps([common.current_leader])
                receiver_socket.sendto(leader_msg, sender_addr)
            
            elif message.msg_type == common.MessageType.CLIENT_DISCONNECT.value:
                print(f'[DISCOVERY] Client {sender_addr} - {message.client_name} disconnected')
                common.client_disconnected = True
                
        except KeyboardInterrupt:
            print('[DISCOVERY] Shutting down discovery service')
            break
        except Exception as e:
            print(f'[DISCOVERY] Error: {e}')
            continue