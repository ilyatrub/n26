import os
import socket
import ssl
import socketserver
import threading
import logging


def perform_dot(data):
    """
    Send request to DoT
    :param data: DNS message (TCP format)
    :return: DNS message (TCP format)
    """
    out_s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ctx = ssl.create_default_context()
    tls_s = ctx.wrap_socket(out_s, server_hostname=DOT_ADDRESS)
    res = None
    try:
        tls_s.connect((DOT_ADDRESS, DOT_PORT))
        tls_s.sendall(data)
        res = tls_s.recv(1024)
    except socket.error as e:
        logging.exception(f"DoT Socket error: {e}")
    except ssl.SSLError as e:
        logging.exception(f"DoT TLS error: {e}")
    finally:
        tls_s.close()
    return res


class ThreadedTCPRequestHandler(socketserver.StreamRequestHandler):
    def handle(self):
        """
        Receive DNS message (TCP format) from client and send it to DoT
        """
        data = self.request.recv(1024)
        logging.info(f"Processing request from {self.client_address}")
        logging.debug(data)
        res = perform_dot(data)
        self.request.sendall(res)


class ThreadedUDPRequestHandler(socketserver.DatagramRequestHandler):
    def handle(self):
        """
        Receive DNS message (UDP format) from client, convert to TCP format and send to DoT
        :return:
        """
        data, sock = self.request
        data = len(data).to_bytes(2, 'big') + data
        logging.info(f"Processing request from {self.client_address}")
        logging.debug(data)
        res = perform_dot(data)
        res = res[2:]
        sock.sendto(res, self.client_address)


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


class ThreadedUDPServer(socketserver.ThreadingMixIn, socketserver.UDPServer):
    pass


def main():
    """
    Create a multithreaded server that listens for TCP or UDP connections
    and proxies them to DoT
    """
    server = None
    try:
        if PROTO == 'tcp':
            server = ThreadedTCPServer((BIND_ADDRESS, BIND_PORT), ThreadedTCPRequestHandler)
        elif PROTO == 'udp':
            server = ThreadedUDPServer((BIND_ADDRESS, BIND_PORT), ThreadedUDPRequestHandler)
    except Exception as e:
        logging.exception(f"Server creation error: {e}")

    with server:
        server_thread = threading.Thread(target=server.serve_forever())
        server_thread.daemon = True
        server_thread.start()
        server.shutdown()


if __name__ == "__main__":
    # Setting variables from environment
    BIND_ADDRESS = os.getenv("BIND_ADDRESS", "")
    BIND_PORT = int(os.getenv("BIND_PORT", 53))
    PROTO = os.getenv("PROTO", "udp")
    DOT_ADDRESS = os.getenv("DOT_ADDRESS", "1.1.1.1")
    DOT_PORT = int(os.getenv("DOT_PORT", 853))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "info")

    level = logging.INFO
    if LOG_LEVEL == 'debug':
        level = logging.DEBUG
    log_format = '%(asctime)s [%(levelname)s] %(message)s'
    logging.basicConfig(format=log_format, level=level)
    logging.info(f"Starting {PROTO} server on {BIND_ADDRESS}:{BIND_PORT}")
    logging.info(f"DoT config:")
    logging.info(f"     Address:    {DOT_ADDRESS}")
    logging.info(f"     Port:       {DOT_PORT}")
    main()
