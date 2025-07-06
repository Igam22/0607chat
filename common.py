import socket
import threading
import enum
import pickle
import time

# Configuration constants
ENCODING = 'utf-8'
CHAT_PORT = 9000
DISCOVERY_GROUP_IP = '224.1.1.1'
DISCOVERY_PORT = 9001
DISCOVERY_ADDRESS = (DISCOVERY_GROUP_IP, DISCOVERY_PORT)
ELECTION_PORT = 9002
HEARTBEAT_INTERVAL = 2.0

# Global state
active_servers = []
connected_clients = []
current_leader = None
network_topology_changed = False
server_failure_detected = False
new_server_joined = False
client_disconnected = False

class MessageType(enum.Enum):
    SERVER_DISCOVERY = 'SERVER_DISCOVERY'
    CLIENT_DISCOVERY = 'CLIENT_DISCOVERY'
    CLIENT_DISCONNECT = 'CLIENT_DISCONNECT'

class ChatType(enum.Enum):
    CONNECT = 'CONNECT'
    MESSAGE = 'MESSAGE'
    DISCONNECT = 'DISCONNECT'

def get_local_ip():
    """Get local IP address"""
    temp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        temp_socket.connect(("8.8.8.8", 80))
        local_ip = temp_socket.getsockname()[0]
    finally:
        temp_socket.close()
    return local_ip

def create_thread(target_function, args=()):
    """Create and start a new thread"""
    thread = threading.Thread(target=target_function, args=args)
    thread.daemon = True
    thread.start()
    return thread

def deserialize_discovery_message(data):
    """Deserialize discovery message"""
    message_data = pickle.loads(data)
    return DiscoveryMessage(message_data[0], message_data[1], message_data[2], message_data[3], message_data[4])

def deserialize_chat_message(data):
    """Deserialize chat message"""
    message_data = pickle.loads(data)
    return ChatMessage(message_data[0], message_data[1], message_data[2])

class DiscoveryMessage:
    def __init__(self, msg_type, server_list, client_list, leader_ip, client_name):
        self.msg_type = msg_type
        self.server_list = server_list
        self.client_list = client_list
        self.leader_ip = leader_ip
        self.client_name = client_name

class ChatMessage:
    def __init__(self, msg_type, username, content):
        self.msg_type = msg_type
        self.username = username
        self.content = content

# Global variables
my_ip = get_local_ip()
server_socket = None