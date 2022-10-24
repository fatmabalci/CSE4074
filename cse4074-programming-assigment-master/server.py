#    Authors:
#        - Fatma BALCI
#        - Alper DOKAY

from socket import *
import threading
import logging
import select
from database import UserRepository, remove_online_users


TCP_PORT = 10000
UDP_PORT = 10050
THREAD_LIST = {}
remove_online_users()
repository = UserRepository()
logging.basicConfig(filename="server.log", level=logging.INFO)


class ServerBase(threading.Thread):

    def __init__(self):
        logging.info("Welcome to the Peer-to-peer Chatting")
        logging.info("Loading...")
        print("Welcome to the Peer-to-peer Chatting")
        print("Loading...")
        self.users = dict()
        self.hostname = gethostname()
        try:
            self.host = gethostbyname(self.hostname)
            self.ADDR = (str(self.host), TCP_PORT)
            logging.info("IP address and port of main server {0}:{1}".format(
                str(self.host), str(TCP_PORT)))
            print("IP address and port of main server {0}".format(self.ADDR))
        except:
            logging.info("It could not get host")
            exit()

        self.tcp_socket = socket(AF_INET, SOCK_STREAM)
        self.udp_socket = socket(AF_INET, SOCK_DGRAM)
        self.tcp_socket.bind((self.host, TCP_PORT))
        self.udp_socket.bind((self.host, UDP_PORT))

        logging.info("Program is starting...")
        logging.info("Reyhan and Alper says hello :)")
        print("Program is starting...")
        print("Reyhan and Alper says hello :)")

        self.start()

    def start(self):
        self.tcp_socket.listen(5)

        socketList = [self.tcp_socket, self.udp_socket]

        while socketList:
            read, write, _except = select.select(socketList, [], [])

            for value in read:
                # If the incoming message comes to the tcp, the connection is accepted, then a thread is created for it
                # then this thread is initialized
                if value is self.tcp_socket:
                    tcp_client_socket, addr = self.tcp_socket.accept()
                    new_thread = ClientHandler(
                        addr[0], addr[1], tcp_client_socket)
                    new_thread.start()
                # if message that received goes to the udp
                elif value is self.udp_socket:
                    # it took the received udp msg and then separated it
                    message, client_address = value.recvfrom(1024)
                    message = message.decode().split()
                    # then it checks it is hello message or not
                    if message[0] == "HELLO":
                        # it checks if the account from which this hello msg was sent is online or not
                        if message[1] in THREAD_LIST:
                            # it resets the time for that peer from hello msg is came
                            THREAD_LIST[message[1]].resetTimeout()
                            print("Hello is received from " + message[1])
                            logging.info("It is received from " + client_address[0] + ":" + str(
                                client_address[1]) + " -> " + " ".join(message))

        self.tcp_socket.close()


class ClientHandler(threading.Thread):
    def __init__(self, ip, port, tcp_client_socket):
        threading.Thread.__init__(self)
        # connected peer's ip
        self.ip = ip
        # connected peer's port number
        self.port = port
        # peer's socket
        self.tcp_client_socket = tcp_client_socket
        # initializing username, online status, udp server
        self.user_name = None
        self.is_online = True
        self.udp_server = None
        print("Initialized new thread for " + ip + ":" + str(port))

    # main of the thread
    def run(self):
        # thread locks that is going to be use for synchronization of threads
        self.lock = threading.Lock()
        print("Connection request is from: " + self.ip + ":" + str(self.port))
        print("IP connected: " + self.ip)

        while True:
            try:
                message = self.tcp_client_socket.recv(1024).decode().split()
                logging.info("It is received from " + self.ip + ":" +
                             str(self.port) + " " + " ".join(message))
                print("It is received from " + self.ip + ":" +
                      str(self.port) + " " + " ".join(message))

                if message[0] == "JOIN":

                    is_success, response = repository.add_new_user(
                        message[1], message[2])

                    print("From " + self.ip + ":" +
                          str(self.port) + " " + response)
                    logging.info("Message sent " + self.ip + ":" +
                                 str(self.port) + " " + response)
                    self.tcp_client_socket.send(response.encode())

                elif message[0] == "LOGIN":
                    repository.load_data()
                    is_success, response = repository.login(
                        message[1], message[2])

                    full_response = str(is_success) + '\t' + response

                    if is_success:
                        self.lock.acquire()
                        try:
                            THREAD_LIST[message[1]] = self
                        finally:
                            self.lock.release()

                        logging.info("Message sent " + self.ip + ":" +
                                     str(self.port) + " " + response)
                        self.tcp_client_socket.send(full_response.encode())
                        self.udp_server = udp_server(
                            self.user_name, self.tcp_client_socket)
                        self.udp_server.start()
                        self.udp_server.timer.start()

                    else:
                        logging.info("Message sent " + self.ip + ":" +
                                     str(self.port) + " " + response)

                        self.tcp_client_socket.send(full_response.encode())

                elif message[0] == "LOGOUT":
                    repository.load_data()
                    result = repository.logout(message[1])

                    if result:
                        self.lock.acquire()
                        try:
                            if message[1] in THREAD_LIST:
                                del THREAD_LIST[message[1]]
                        finally:
                            self.lock.release()

                        self.tcp_client_socket.send(str(result).encode())
                        self.tcp_client_socket.close()
                        self.udp_server.timer.cancel()
                        break

                elif message[0] == "SEARCH":
                    repository.load_data()
                    result, response = repository.search(message[1])
                    
                    if result:
                        user_info = repository.get_user(message[1])
                        print(user_info)
                        full_message = str(result) + '\t' + user_info.ip + '\t' + user_info.port

                        logging.info("Message sent " + self.ip + ":" +
                                         str(self.port) + " " + full_message)
                        self.tcp_client_socket.send(full_message.encode())
                    
                    else:
                        full_message = str(result) + '\t' + response
                        logging.info("Message sent " + self.ip + ":" +
                                         str(self.port) + " " + full_message)
                        self.tcp_client_socket.send(full_message.encode())
                    
            except OSError as oErr:
                logging.error("OSError: {0}".format(oErr))

    # it is in order to reset time for the thread of udp timer
    def resetTimeout(self):
        self.udp_server.resetTimer()


class udp_server(threading.Thread):

    # initializing udp server thread
    def __init__(self, user_name, user_socket):
        threading.Thread.__init__(self)
        self.user_name = user_name
        # initialized the timer thread for udp server
        self.timer = threading.Timer(20, self.get_hello_message)
        self.tcp_socket = user_socket

    # peer will be disconnected if the hello msg is not taken before the time is up

    def get_hello_message(self):
        if self.user_name == None:
            self.tcp_socket.close()
            print("Removing " + self.user_name + " from online peers")
            

        repository.user_logout(self.user_name)
        if self.user_name in THREAD_LIST:
            del THREAD_LIST[self.user_name]

    # it is resetting timer for the udp server

    def resetTimer(self):
        self.timer.cancel()
        self.timer = threading.Timer(20, self.get_hello_message)
        self.timer.start()


mainObj = ServerBase()
