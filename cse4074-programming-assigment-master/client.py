#    Authors:
#        - Fatma Balcı
#        - Alper Dokay
from socket import *
import threading
import select
import logging
import random
from database import UserRepository

HEADER = 1024
logging.basicConfig(filename="client.log", level=logging.INFO)

repository = UserRepository()

# This is the client base
class ClientBase(threading.Thread):

    def __init__(self, user):
        threading.Thread.__init__(self)
        # set the user given
        self.user = user
        # create the TCP socket for communication
        self.tcp_server_socket = socket(AF_INET, SOCK_STREAM)
        # set chat status
        self.chat_status = 0
        # set the connected user details by default, it will be updated later
        self.tcp_connected_user = None
        self.connected_user_ip = None
        self.connected_user_port = None
        self.connected_user_name = None


    def run(self):
        # form the client address
        client_addr = (self.user.ip, self.user.port)

        # connect to it
        self.tcp_server_socket.bind(client_addr)
        # start listening
        self.tcp_server_socket.listen(4)

        # add the socket to the socket list
        socket_list = [self.tcp_server_socket]

        # continue till there is no socket in the list
        while socket_list:

            try:
                # get the read value
                read, _, _ = select.select(socket_list, [], [])

                # go through the read value
                for value in read:
                    
                    # check if it is a TCP socket
                    if value is self.tcp_server_socket:
                        # get the value
                        connected, addr = value.accept()
                        connected.setblocking(0)
                        # add the new client to the socket list
                        socket_list.append(connected)

                        # check if the chat was initiated
                        if self.chat_status == 0:
                            print(self.user.user_name +
                                " is connected at " + str(addr))
                            # set the connected user details
                            self.tcp_connected_user = connected
                            self.connected_user_ip = addr[0]

                    else:
                        # get the message for the chat to get started
                        message = value.recv(HEADER).decode()

                        save_info_log("Message received by " + str(self.connected_user_ip) + " -> " + str(message))

                        # split it to check the command
                        message_splitted = message.split("\t")

                        # Check if this was a request
                        if message_splitted[0] == "CHAT-REQUEST":
                            
                            # check if the value was the connected users value
                            if value is self.tcp_connected_user:
                                # split the message
                                message = message.split()
                                # set the connected port
                                self.connected_user_port = int(
                                    message[1])

                                # set the connected user name for printing
                                self.connected_user_name = message[2]

                                print("Incoming chat request from " + self.connected_user_name 
                                + "\n" + "Enter OK to accept or REJECT to reject:  ")

                                # set chat as started
                                self.chat_status = 1

                            elif value is not self.tcp_connected_user and self.chat_status == 1:
                                message = "BUSY"
                                value.send(message.encode())

                                socket_list.remove(value)

                        # Check if the message is OK
                        elif message == "OK":
                            self.chat_status = 1
                            repository.update_user(self.user)

                        # Check if the message is REJECT
                        elif message == "REJECT":
                            self.chat_status = 0
                            # remove the socket as it is rejected
                            socket_list.remove(value)

                        # Check if the message is OK
                        elif message == "QUIT":
                            self.chat_status = 0
                            socket_list.clear()
                            socket_list.append(self.tcp_server_socket)

                            print("Your chat has been terminated!")

                        # Check if the message is a normal message
                        elif len(message) > 0:
                            print("\n" + self.connected_user_name + ": " + message + "\n" + self.user.user_name + ":")

                        # Check if the message was empty, shut down the chatting
                        elif len(message) == 0:
                            self.user.status = 1
                            repository.update_user(self.user)
                            socket_list.clear()
                            socket_list.append(self.tcp_server_socket)
            # catch the exception
            except Exception as err:
                save_error_log("Error occured: {0}".format(err))

# This is the class for User Client to handle internal operations for chatting
class UserClient(threading.Thread):
    def __init__(self, ip, port, user_server, message):
        threading.Thread.__init__(self)
        # create the tcp socket for communication
        self.tcp_client_socket = socket(AF_INET, SOCK_STREAM)
        # set the user server
        self.user_server = user_server

        # set the connected users details
        self.ip = ip
        self.port = port
        self.client_response = message
        self.chat_status = False

    # This is the run function for thread
    def run(self):
        
        # connect to the socket
        self.tcp_client_socket.connect((self.ip, int(self.port)))
        
        # check the response received from the client and check if the user is online
        if self.user_server.user.status == 1 and self.client_response is None:
            # prepare the command
            request_message = "CHAT-REQUEST\t" + str(self.user_server.user.port) + "\t" + self.user_server.user.user_name

            # save the log
            save_info_log("Message sent to " + self.ip + ":" +
                         str(self.port) + " -> " + request_message)
            # send the message
            self.tcp_client_socket.send(request_message.encode())
            # print the message
            print("Request message " + request_message + " is sent...")
            # get the response
            self.client_response = self.tcp_client_socket.recv(HEADER).decode()
            # save the log
            save_info_log("Received from " + self.ip + ":" +
                         str(self.port) + " -> " + self.client_response)
            print("Response is " + self.client_response)
            self.client_response = self.client_response.split()

            # check if the response was ok, meaning the chat was accepted
            if self.client_response[0] == "OK":
                # set user status to 2, as it is in a chat
                self.user_server.user.status = 2

                # set the user's name for printing
                self.user_server.connected_user_name = self.client_response[1]

                # while user is busy, run the messaging part
                while self.user_server.user.status == 2:
                    # get input to be sent
                    message_sent = input(self.user_server.user.user_name + ": ")
                    # send the message
                    self.tcp_client_socket.send(message_sent.encode())
                    # save the info
                    save_info_log("Message sent to " + self.ip + ":" +
                                 str(self.port) + " -> " + message_sent)
                    # check if the message was a QUIT command
                    if message_sent == "QUIT":
                        # set the status to available
                        self.user_server.user.status = 1
                        self.chat_status = True
                        break
                # check if the user was logged out
                if self.user_server.user.status == 3:
                    # check if the chat is still ongoing
                    if not self.chat_status:
                        try:
                            # send the quit message
                            self.tcp_client_socket.send(
                                "QUIT".encode())
                            # save the log
                            save_info_log("Message sent to " + self.ip +
                                         ":" + str(self.port) + " -> QUIT")
                        except BrokenPipeError as bpErr:
                            save_error_log("BrokenPipeError: {0}".format(bpErr))

                    # close the socket and set values to None
                    self.client_response = None
                    self.tcp_client_socket.close()

            # Check if it was rejected
            elif self.client_response[0] == "REJECT":
                # set the mode as busy for user
                self.user_server.user.status = 2
                print("Client rejected your request...")
                # send the command
                self.tcp_client_socket.send("REJECT".encode())
                # save the log
                save_info_log("Message sent to " + self.ip + ":" +
                             str(self.port) + " -> REJECT")
                # close the socket
                self.tcp_client_socket.close()
            
            # Check if the user is Busy
            elif self.client_response[0] == "BUSY":
                print("User is BUSY at the moment")
                # close the socket
                self.tcp_client_socket.close()

        # check if the message was OK
        elif self.client_response == "OK":
            
            # set status to available
            self.user_server.user.status = 1

            ok_message = "OK"
            # send the command
            self.tcp_client_socket.send(ok_message.encode())
            # save the log
            save_info_log("Message sent to " + self.ip + ":" +
                         str(self.port) + " -> " + ok_message)
            print("Client accepted your request. You can start messaging")

            # While user is available
            while self.user_server.user.status == 1:
                # prepare the message
                message_sent = input(self.user_server.user.user_name + ": ")
                # send the message
                self.tcp_client_socket.send(message_sent.encode())
                # save the log
                save_info_log("Message sent to " + self.ip + ":" +
                             str(self.port) + " -> " + message_sent)
                # check if the message was a QUIT command
                if message_sent == "QUIT":
                    # set the status to offline
                    self.user_server.user.status = 0
                    self.chat_status = True
                    break
            # check if the user got offline
            if self.user_server.chat_status == 0:
                # check if the chat is still ongoing
                if not self.chat_status:
                    # send quit message
                    self.tcp_client_socket.send("QUIT".encode())
                    # save the log
                    save_info_log("Message sent to " + self.ip +
                                 ":" + str(self.port) + " -> QUIT")
                # set values to none and close the socket
                self.client_response = None
                self.tcp_client_socket.close()

# This is the main part of the client interface
class ClientOperationHandler:

    # initiation
    def __init__(self):
        
        # get the same host name for the client
        self.hostname = gethostname()
        self.server_name = gethostbyname(self.hostname)

        # set the port same as the server
        self.server_port = 10000
        # create sockets for the operations
        self.tcp_client_socket = socket(AF_INET, SOCK_STREAM)
        self.udp_client_socket = socket(AF_INET, SOCK_DGRAM)
        # set the udp port same as the server
        self.server_udp_port = 10050
        # set the user and its properties none by default, fill it when user logs in
        self.user = None
        self.user_server_port = None
        self.user_server = None
        self.user_client = None
        # set users time none by default, it will be created later
        self.timer = None

        # run the main function when this obj is initiated
        self.run()

    # This is the main method
    def run(self):
        # connect to the server over TCP socket
        self.tcp_client_socket.connect((self.server_name, self.server_port))
        # keep the command to navigate between operations
        command = ""

        print("You can write HELP to get the command list!")

        fetched_user = None

        # as long as the command is not equal to logout, continue
        while command != "LOGOUT":
            
            # get the command
            command = input("Command: ")
            # update the repository with the latest data before the operation
            repository.load_data()

            # This part is for register
            if command.upper() == "REGISTER":
                # Get the username unless it is not empty string
                user_name = input("Enter your username: ")
                while user_name == "":
                    print("Please enter a username to continue!")
                    user_name = input("Enter your username: ")
                # Get the password unless it is not empty string
                password = input("Enter your password: ")
                while password == "":
                    print("Please enter a password to continue!")
                    password = input("Enter your password: ")

                # create the user by using the register function
                self.register(user_name, password)
                # add user to database
                repository.add_new_user(
                    user_name, password)

            # This is part for login operations
            elif command.upper() == "LOGIN":
                # Get the username unless it is not empty string
                user_name = input("Enter your username: ")

                while user_name == "":
                    print("Please enter a username to continue!")
                    user_name = input("Enter your username: ")
                # Get the password unless it is not empty string
                password = input("Enter your password: ")
                while password == "":
                    print("Please enter a password to continue!")
                    password = input("Enter your password: ")

                # get a randomized new port for the ClientBase for chatting operations
                new_client_port = random.randint(30000, 60000)

                # login the user with the port given
                is_success, message = self.login(
                    user_name, password, new_client_port)

                # print response
                print(message)

                # check if login was successful
                if is_success:
                    # get the user from database
                    self.user = repository.get_user(user_name)
                    # update user's client server information with the new port
                    repository.update_user_client_server_addr(
                        user_name, self.server_name, new_client_port)
                    
                    # create user server object and start it
                    self.user_server = ClientBase(self.user)
                    self.user_server.start()

                    # start sending messages over UDP to keep online
                    self.send_hello_message()
            
            # This is the part for logout operation
            elif command.upper() == "LOGOUT":
                # logout the user
                result = self.logout()

                # check if logout was successful
                if result:
                    # set user status to three meaning the user logged out
                    self.user.status = 3
                    # set user to None
                    self.user = None
                    # set server's user status to three meaning the user logged out as well
                    self.user_server.user.status = 3

                    # close the open sockets
                    self.user_server.tcp_server_socket.close()
                    if self.user_client is not None:
                        self.user_client.tcp_client_socket.close()
                    print("Logged out successfully")
                    exit()
                else:
                    print("Error!")

            # This is the part for search operation
            elif command.upper() == "SEARCH":
                
                # check if user logged in
                if self.user_server == None:
                    print("You should log in first to search for a user!")
                    continue

                # Get the username unless it is not empty string
                user_name = input("Username to be searched: ")

                while user_name == "":
                    print("Please enter a username to continue!")
                    user_name = input("Username to be searched: ")

                # make the search
                is_success, result_message = self.search_for_user(user_name)
                
                # check if the search was successful
                if is_success:
                    print("Contact address of " +
                          user_name + " is " + result_message)
                else:
                    # print the error
                    print(result_message)

            # This is the part for starting a chat
            elif command.upper() == "START CHAT":
                # Check if the user logged in
                if self.user_server == None:
                    print("You should log in first to start chatting!")
                    continue
                
                # Get the username unless it is not empty string
                user_name = input("Enter the username of user to start chat: ")

                while user_name == "":
                    print("Please enter a username to continue!")
                    user_name = input(
                        "Enter the username of user to start chat: ")

                # search for the user first
                result, result_message = self.search_for_user(user_name)

                # Check if the search was successful
                if result:
                    # fetch the user from database
                    fetched_user = repository.get_user(user_name)
                    # create new client thread for chatting
                    self.user_client = UserClient(
                        fetched_user.ip, fetched_user.port, self.user_server, None)
                    # start the client and join the thread
                    self.user_client.start()
                    self.user_client.join()

            # This is the part for printing the navigation
            elif command.upper() == "HELP":
                
                # Check if user logged in
                if self.user_server == None:
                    print("\n")
                    print("\tREGISTER      \t -> Create new user")
                    print("\tLOGIN         \t -> Login to the application")
                    print("\n")
                else:
                    print("\n")
                    print("\tREGISTER      \t -> Create new user")
                    print("\tLOGIN         \t -> Login to the application")
                    print("\tLOGOUT        \t -> Logout from the application")
                    print("\tSEARCH A USER \t -> Search a user")
                    print("\tSTART CHAT    \t -> Start chat with a user")
                    print("\n")

            # This is the part for accepting the chat request
            elif command.upper() == "OK":
                
                # Send OK message to the client
                ok_message = "OK " + self.user.user_name
                save_info_log(
                    "Message sent to " + self.user_server.user.ip + " -> " + ok_message)
                # send the message
                self.user_server.tcp_connected_user.send(ok_message.encode())
                # create new client thread for chatting
                self.user_client = UserClient(
                    self.user_server.connected_user_ip, self.user_server.connected_user_port, self.user_server, "OK")
                # Start and join the thread of socket
                self.user_client.start()
                self.user_client.join()

            # This is the part where user rejects the chat request
            elif command.upper() == "REJECT":
                
                # send the message
                self.user_server.tcp_connected_user.send(command.encode())
                # set the status to rejected
                self.user_server.user.status = 4
                
                save_info_log(
                    "Message sent to " + self.user_server.connected_user_ip + " -> REJECT")
            # This is the part where interpreter could not find any related command
            else:
                print("There is no command like '{0}', please type HELP to see options!".format(
                    command))

        # close the socket if user logs out
        self.tcp_client_socket.close()

    # This is the method for register
    def register(self, username, password):
        # Prepare the command
        command = "JOIN " + username + " " + password
    
        # Send the command
        self.tcp_client_socket.send(command.encode())
        # save the log
        save_info_log("Message sent to " + self.server_name + ":" +
                     str(self.server_port) + " -> " + command)

        # get the response
        response = self.tcp_client_socket.recv(HEADER).decode()

        print(response)
        # save the log
        save_info_log("Received from " + self.server_name + " -> " + response)

    # This is the method for login
    def login(self, username, password, client_port):
        # Prepare the command
        command = "LOGIN " + username + " " + password + " " + str(client_port)
        
         # Send the command
        self.tcp_client_socket.send(command.encode())
        # Save the log
        save_info_log("Message sent to " + self.server_name + ":" +
                     str(self.server_port) + " -> " + command)

        response = self.tcp_client_socket.recv(HEADER).decode()
        # Save the log
        save_info_log("Response received from " + self.server_name + " -> " + response)

        # split the response
        splitted_message = response.split("\t")

        result = False

        if splitted_message[0] == "True":
            result = True

        return result, splitted_message[1]

    def logout(self):
        # Prepare the command
        command = "LOGOUT" + " " + self.user.user_name

        # Send the command
        self.tcp_client_socket.send(command.encode())
        # Save the log
        save_info_log("Message sent to " + self.server_name + ":" +
                     str(self.server_port) + " -> " + command)

        # get the response
        response = self.tcp_client_socket.recv(HEADER).decode()
        
        # Save the log
        save_info_log("Response received from " + self.server_name + " -> " + response)

        if response == "True":
            self.timer.cancel()
            return True
        else:
            return False


    def search_for_user(self, username):
        # Prepare the command
        command = "SEARCH " + username
        
         # Send the command
        self.tcp_client_socket.send(command.encode())

        # Save the log
        save_info_log("Message sent to " + self.server_name + ":" +
                     str(self.server_port) + " -> " + command)
        
        # get the response
        response = self.tcp_client_socket.recv(HEADER).decode()
        save_info_log("Response received from " + self.server_name + " -> " + response)

        # split the response
        splitted_response = response.split('\t')

        # check if the first parameter was true
        if splitted_response[0] == 'True':
            return True, splitted_response[1] + ':' + splitted_response[2]

        else:
            return False, splitted_response[1]

    def send_hello_message(self):
        # Prepare the command
        command = "HELLO " + self.user_server.user.user_name
        
        # Send the command
        self.udp_client_socket.sendto(
            command.encode(), (self.server_name, self.server_udp_port))
        
        # Save the log
        save_info_log("Message sent to " + self.server_name + ":" +
                     str(self.server_udp_port) + " -> " + command)

        # Start the timer for the next message to be sent
        self.timer = threading.Timer(6, self.send_hello_message)
        self.timer.start()

# This is the method for saving information logs
def save_info_log(message):
    logging.info(message)

# This is the method for saving error logs
def save_error_log(message):
    logging.error(message)

# Create an object of the handler
main = ClientOperationHandler()
