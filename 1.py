from socket import *
import threading
import sys
import time

def get_host_ip():
    """ 获取本机 IP """
    try:
        s = socket(AF_INET, SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip

def epsv_handler(s_ext, conn):
    """ 处理 EPSV 数据连接 """
    try:
        # 启用 SO_REUSEADDR
        s_ext.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        # 绑定到随机端口 (0 表示让系统分配可用端口)
        s_ext.bind((IP, 0))  # 动态分配端口
        s_ext.listen(1)
        # 获取系统分配的端口
        _, port = s_ext.getsockname()
        # 发送 EPSV 响应，包含动态端口
        conn.send(f'229 Entering Extended Passive Mode (|||{port}|)\r\n'.encode())
        conn_data, addr = s_ext.accept()
        print(f"[*] Data connection from {addr}")
        conn.send(b'150 Opening BINARY mode data connection.\r\n')
        data = conn_data.recv(1024).decode('utf-8', errors='ignore')
        if data:
            print(f"[*] Data received on data connection: {data}")
        conn.send(b'226 Transfer complete.\r\n')
        conn_data.close()
    except Exception as e:
        print(f"[-] Data connection error: {e}")
        conn.send(b'426 Connection closed; transfer aborted.\r\n')
    finally:
        s_ext.close()

def handle_client(conn, addr, output_file=None):
    """ 处理客户端连接 """
    print(f"[*] Connection from {addr}")
    received_paths = []
    current_directory = ""  # 跟踪当前目录

    try:
        conn.send(b'220 (vsFTPd 3.0.3)\r\n')

        while True:
            msg = conn.recv(1024).decode('utf-8', errors='ignore')
            if not msg:
                break
            print(f"[C] {msg}")

            if msg.startswith('USER'):
                conn.send(b'331 Please specify the password.\r\n')
            elif msg.startswith('PASS'):
                conn.send(b'230 Login successful.\r\n')
            elif msg.startswith('PWD'):
                conn.send(f'257 "{current_directory or "/home/user"}" is the current directory.\r\n'.encode())
            elif msg.startswith('TYPE I'):
                conn.send(b'200 Switching to Binary mode.\r\n')
            elif msg.startswith('EPSV ALL'):
                conn.send(b'200 EPSV ALL ok.\r\n')
            elif msg.startswith('EPSV'):
                s_ext = socket()
                t = threading.Thread(target=epsv_handler, args=(s_ext, conn))
                t.start()
            elif msg.startswith('EPRT'):
                conn.send(b'200 EPRT command successful.\r\n')
            elif msg.startswith('PORT'):
                conn.send(b'200 PORT command successful.\r\n')
            elif msg.startswith('CWD'):
                dir_path = msg[4:].strip()
                if dir_path:
                    if current_directory:
                        current_directory = f"{current_directory}/{dir_path}"
                    else:
                        current_directory = dir_path
                conn.send(b'250 Directory successfully changed.\r\n')
            elif msg.startswith('RETR'):
                file_path = msg[5:].strip()
                full_path = file_path if not current_directory else f"{current_directory}/{file_path}"
                received_paths.append(full_path)
                print(f"[+] Received RETR path: {full_path}")
                conn.send(b'150 Opening BINARY mode data connection.\r\n')
                conn.send(b'226 Transfer complete.\r\n')
            elif msg.startswith('QUIT'):
                conn.send(b'221 Goodbye.\r\n')
                break
            else:
                conn.send(b'500 Unknown command.\r\n')

        # 打印所有接收到的路径
        print("[*] RETR paths received:")
        for path in received_paths:
            print(f"    {path}")
        # 写入日志文件
        if output_file and received_paths:
            with open(output_file, 'a') as f:
                for path in received_paths:
                    f.write(path + '\n')
            print(f"[*] Paths saved to {output_file}")

    except Exception as e:
        print(f"[-] Error handling client: {e}")
    finally:
        conn.close()
        print(f"[*] Connection from {addr} closed.")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python ftp_sniffer.py <port> [output_file]")
        sys.exit(1)

    IP = get_host_ip()
    PORT = int(sys.argv[1])
    ADDR_MAIN = (IP, PORT)

    print(f"[*] Listening on {IP}:{PORT}...")

    output_log = sys.argv[2] if len(sys.argv) > 2 else None

    server = socket()
    server.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)  # 启用 SO_REUSEADDR
    server.bind(ADDR_MAIN)
    server.listen(5)

    try:
        while True:
            conn, addr = server.accept()
            client_thread = threading.Thread(
                target=handle_client,
                args=(conn, addr, output_log)
            )
            client_thread.start()
    except KeyboardInterrupt:
        print("\n[*] Server shutting down.")
    finally:
        server.close()
