import socket
import struct
import pickle
import time
import threading
import common

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

def periodic_discovery_announce():
    """Sende regelmäßig Discovery-Nachrichten, damit alle Server sich finden und synchronisieren."""
    while True:
        try:
            discovery_msg = pickle.dumps([
                common.MessageType.SERVER_DISCOVERY.value,
                common.active_servers,
                common.connected_clients,
                common.current_leader,
                ''
            ])
            sender_socket.sendto(discovery_msg, common.DISCOVERY_ADDRESS)
        except Exception as e:
            print(f'[DISCOVERY] Fehler beim Senden der Discovery-Nachricht: {e}')
        time.sleep(2)  # Alle 2 Sekunden

def start_periodic_discovery():
    """Starte den Discovery-Thread beim Serverstart."""
    thread = threading.Thread(target=periodic_discovery_announce)
    thread.daemon = True
    thread.start()

def handle_discovery_messages():
    """Handle incoming discovery messages"""
    while True:
        try:
            data, sender_addr = receiver_socket.recvfrom(1024)
            message = common.deserialize_discovery_message(data)
            
            if message.msg_type == common.MessageType.SERVER_DISCOVERY.value:
                # Vereinige empfangene Serverliste mit eigener
                received_servers = message.server_list if message.server_list else []
                if sender_addr[0] not in received_servers:
                    received_servers.append(sender_addr[0])
                if common.my_ip not in received_servers:
                    received_servers.append(common.my_ip)
                # Vereinige mit lokaler Liste
                for ip in received_servers:
                    if ip not in common.active_servers:
                        common.active_servers.append(ip)
                # Debug-Ausgabe
                print(f"[DISCOVERY] Aktive Server auf {common.my_ip}: {common.active_servers}")
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