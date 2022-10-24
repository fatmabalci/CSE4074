import logging
from socket import *
import threading
import select


TCP_PORT = 5000
UDP_PORT = 5050


class MainProgram:

    def __init__(self):
        logging.info("Welcome to the Console Based P2P Chatting Program!")
        logging.info("Program is initializing...")
        self.onlineUsers = dict()
        self.users = dict()
        self.hostname = gethostname()
        try:
            self.host = gethostbyname(self.hostname)
            logging.info("Main server's IP address & port {0}:{1}".format(str(self.host), str(TCP_PORT)))
        except:
            logging.info("Could not get the host")
            exit()
        
        self.tcpSocket = socket(AF_INET, SOCK_STREAM)
        self.udpSocket = socket(AF_INET, SOCK_DGRAM)
        self.tcpSocket.bind((self.host, TCP_PORT))
        self.udpSocket.bind((self.host, UDP_PORT))
        
        logging.info("Program is successfully initialized!")
        logging.info("Fatma and Alper says hi! :)")
        logging.info("Starting the program...")

        self.start()

    def start(self):
        self.tcpSocket.listen(5)

        socketList = [self.tcpSocket, self.udpSocket]

        while socketList:
            readable, writable, exceptional = select.select(socketList, [], [])
            
            for s in readable:
                # if the message received comes to the tcp socket
                # the connection is accepted and a thread is created for it, and that thread is started
                if s is self.tcpSocket:
                    tcp_client_socket, addr = self.tcpSocket.accept()
                    newThread = ClientHandler(addr[0], addr[1], tcp_client_socket)
                    newThread.start()
                # if the message received comes to the udp socket
                elif s is self.udpSocket:
                    # received the incoming udp message and parses it
                    message, clientAddress = s.recvfrom(1024)
                    message = message.decode().split()
                    # checks if it is a hello message
                    if message[0] == "HELLO":
                        # checks if the account that this hello message 
                        # is sent from is online
                        if message[1] in self.threadList:
                            # resets the timeout for that peer since the hello message is received
                            self.threadList[message[1]].resetTimeout()
                            print("Hello is received from " + message[1])
                            logging.info("Received from " + clientAddress[0] + ":" + str(clientAddress[1]) + " -> " + " ".join(message))
        
        self.tcpSocket.close()

mainObj = MainProgram()
mainObj.start()