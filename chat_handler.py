import socket
import common

# Main chat socket
chat_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
chat_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
chat_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
chat_socket.bind((common.my_ip, common.CHAT_PORT))

def start_chat_server():
    """Start the main chat server"""
    print(f'[CHAT] Server started on {common.my_ip}:{common.CHAT_PORT}')
    print('[CHAT] Waiting for clients...')
    
    while True:
        try:
            data, client_addr = chat_socket.recvfrom(1024)
            chat_msg = common.deserialize_chat_message(data)
            
            # Handle new client connections
            if client_addr not in common.connected_clients:
                common.connected_clients.append(client_addr)
                if chat_msg:
                    process_chat_message(chat_msg, client_addr)
                    welcome_msg = f'[SERVER] {chat_msg.username}, welcome to the chat!'
                    chat_socket.sendto(welcome_msg.encode(common.ENCODING), client_addr)
                    
                    client_list_msg = f'[CLIENTS] {common.connected_clients}'
                    chat_socket.sendto(client_list_msg.encode(common.ENCODING), client_addr)
                    
                    # Notify other clients
                    chat_msg.content = 'joined the chat'
                    broadcast_to_clients(chat_msg, client_addr)
                    continue
            
            # Handle existing client messages
            process_chat_message(chat_msg, client_addr)
            broadcast_to_clients(chat_msg, client_addr)
            
        except Exception as e:
            print(f'[CHAT] Error: {e}')
            continue

def process_chat_message(message, client_addr):
    """Process incoming chat messages"""
    if message.msg_type == common.ChatType.CONNECT.value:
        print(f'[CHAT] Client {client_addr} - {message.username} connected')
    
    elif message.msg_type == common.ChatType.MESSAGE.value:
        print(format_chat_message(client_addr, message.username, message.content))
    
    elif message.msg_type == common.ChatType.DISCONNECT.value:
        if client_addr in common.connected_clients:
            common.connected_clients.remove(client_addr)
        print(format_chat_message(client_addr, message.username, message.content))
        print(f'[CLIENTS] {common.connected_clients}')

def broadcast_to_clients(message, sender_addr):
    """Broadcast message to all connected clients except sender"""
    for client_addr in common.connected_clients:
        if client_addr != sender_addr:
            formatted_msg = format_chat_message(sender_addr, message.username, message.content)
            try:
                chat_socket.sendto(formatted_msg.encode(common.ENCODING), client_addr)
            except Exception as e:
                print(f'[CHAT] Failed to send to {client_addr}: {e}')

def format_chat_message(address, username, content):
    """Format chat message for display"""
    return f'[CLIENT] {address} - {username}: {content}'