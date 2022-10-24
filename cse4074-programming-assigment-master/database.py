import json


class UserRepository:

    def __init__(self):
        self.users = []
        self.online_users = []
        self.admin_key = "1234567890"
        self.is_initialized = False

        self.load_data()

    # function for opening json file and loading data
    def load_data(self):
        self.users = []
        # opening jason file
        with open('database.json') as json_file:
            data = json.load(json_file)

            for user_data in data["users"]:
                ip, port, status = "", "", 0
                if "ip" in user_data:
                    ip = user_data["ip"]
                if "port" in user_data:
                    port = user_data["port"]
                if "status" in user_data:
                    status = user_data["status"]

                if status == 1:
                    if not self.is_user_already_added_to_online(user_data["user_name"]):
                        user = User(
                            user_data["user_name"], user_data["password"], ip, port, status)
                        self.online_users.append(user)

                if not self.is_user_already_added(user_data["user_name"]):
                    user = User(user_data["user_name"],
                                user_data["password"], ip, port, status)
                    self.users.append(user)

    # checks if the user is added before or not
    def is_user_already_added(self, user_name):
        for user in self.users:
            if user.user_name == user_name:
                return True

        return False

    def is_user_already_added_to_online(self, user_name):
        for user in self.online_users:
            if user.user_name == user_name:
                return True

        return False

    # this function is adding new user
    def add_new_user(self, user_name, password):
        if len(user_name) < 2 and password < 6:
            return False, "Username should have at least 2 characters, password should have at least 6 characters"

        # it checks if given username is taken or not
        for user in self.users:
            if user_name == user.user_name:
                # if it is taken, it returns false and gives warning msg
                return False, "This username is already taken, please select another!"

        new_user = User(user_name, password)

        self.users.append(new_user)
        self.update_database_file()

        # if everything is alright, user is added
        return True, "User has been succesfully added"

    # this function is for removing online peer
    def remove_online_user(self, user_name):

        for user in self.users:
            if user.user_name == user_name:
                user.status = 3
                self.online_users.remove(user)
                self.update_database_file()
                return True, "{0} has been removed from online user list!".format(user.user_name)

        return False, "User does not exist!"

    # it is for removing given user
    def remove_user(self, user_name, admin_key):

        if self.admin_key == admin_key:
            for user in self.users:
                if user.user_name == user_name:
                    self.status = 3
                    self.online_users.remove(user)
                    self.update_database_file()
                    return True, "{0} has been removed from online user list!".format(user.user_name)

            return False, "User does not exist!"

        else:
            return False, "Your admin key is wrong!"

    # it checks if the given user is online or not
    def is_user_online(self, user_name):

        for user in self.online_users:
            if user.user_name == user_name:
                return True

        return False

    def get_user(self, user_name):

        for user in self.users:
            if user.user_name == user_name:
                return user

        return None

    # function that logs in with the given username and password
    def login(self, user_name, password):
        # checks for if the given user is online or not
        for user in self.online_users:
            if user.user_name == user_name:
                return False, "Your user is already online!"

        for user in self.users:
            if user.user_name == user_name:
                if user.password == password:
                    user.status = 1
                    self.online_users.append(user)
                    self.update_database_file()
                    return True, "User logged in successfully!"
                else:
                    return False, "Check your credentials!"

        # if there is no such user, it gives a warning
        return False, "There is no user with the given username!"

    # the function that performs the logout operation
    def logout(self, user_name):
        for user in self.online_users:
            if user.user_name == user_name:
                user.status = 3
                self.update_user(user)
                self.online_users.remove(user)
                self.update_database_file()
                return True

        return False

    # this function is for updating user client server address
    def update_user_client_server_addr(self, user_name, ip, port):
        for user in self.online_users:
            if user.user_name == user_name:
                user.ip = ip
                user.port = port

        for user in self.users:
            if user.user_name == user_name:
                user.ip = ip
                user.port = port
                user.status = 1
                self.update_database_file()
                # self.update_database_file()
                return True, "User client server address is updated!"

        # if there is not such a user, it gives warning
        return False, "User does not exists!"

    # this function is for updating json file
    def update_database_file(self):

        dict_list = []

        for user in self.users:
            new = {
                "user_name": user.user_name,
                "password": user.password,
                "ip": user.ip,
                "port": str(user.port),
                "status": user.status
            }
            dict_list.append(new)

        data = {}
        data["users"] = dict_list

        json_string = json.dumps(data, indent=4)
        with open('database.json', 'w') as output:
            output.write(json_string)

    # function for updating given user
    def update_user(self, updated_user):
        for user in self.users:
            if user.user_name == updated_user.user_name:
                user.status = updated_user.status
                self.update_database_file()
                return True

        return False

    def search(self, user_name):
        # it checks şs the given user is exist or not
        is_user_exist = False
        for user in self.users:
            if user.user_name == user_name:
                is_user_exist = True
                break

        if not is_user_exist:
            return False, "NOT FOUND"

        is_user_online = False

        for user in self.online_users:
            if user.user_name == user_name:
                is_user_online = True
                break

        if not is_user_online:
            return False, "The user that you are searching for is not online!"

        return True, "The user is ready to chat!"


class User:

    def __init__(self, user_name, password, ip=str(), port=str(), status=0):
        self.user_name = user_name
        self.password = password
        self.ip = ip
        self.port = port
        """
            Status types are the following; (available by default)
                1 - Available
                2 - Busy (meaning that the user is chatting with someone)
                3 - Logged out
        """
        self.status = status

    def __str__(self):
        status_text = str()

        if self.status == 1:
            status_text = "Available"
        elif self.status == 2:
            status_text = "Busy"
        else:
            status_text = "Not specified!"

        return "Username: {0}, password: {1}, status: {2}, IP address: {3}, Port: {4}".format(
            self.user_name, self.password, status_text, self.ip, self.port)


# this function is for removing online users
def remove_online_users():
    users, user_name_list = [], []
    with open('database.json') as json_file:
        data = json.load(json_file)

        for user_data in data["users"]:
            ip, port, status = "", "0", 0
            if "ip" in user_data:
                ip = user_data["ip"]

            user = User(user_data["user_name"],
                        user_data["password"], ip, port, status)

            if user.user_name not in user_name_list:
                user_name_list.append(user.user_name)
                users.append(user)

    dict_list = []

    for user in users:
        new = {
            "user_name": user.user_name,
            "password": user.password,
            "ip": user.ip,
            "port": str(user.port),
            "status": user.status
        }
        dict_list.append(new)

    data = {}
    data["users"] = dict_list

    json_string = json.dumps(data, indent=4)
    with open('database.json', 'w') as output:
        output.write(json_string)


repo = UserRepository()
