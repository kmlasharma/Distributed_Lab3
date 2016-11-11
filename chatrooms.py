class Chatroom:
	'Common base class for all chatrooms'
	numOfChatrooms = 0

	def __init__(self, name, ipaddress, port, room_ref, list_of_clients):
		self.name = name
		self.ipaddress = ipaddress
		self.port = port
		self.room_ref = room_ref
		self.list_of_clients = list_of_clients
		Chatroom.numOfChatrooms += 1

	def displayChatroomCount(self):
		print "Total chatrooms: %d" % Chatroom.numOfChatrooms

	def displayChatroomDetails(self):
		print "Name: %s, Room Ref: %d, Port: %d, IP: %s" % (self.name, self.room_ref, self.port, self.ipaddress)
	
	def getListOfClients(self):
		return self.list_of_clients

	def getRoomRef(self):
		return self.room_ref

	def getChatroomName(self):
		return self.name

	def getIPAddress(self):
		return self.ipaddress

	def getPort(self):
		return self.port

	def addClient(self, client):
		self.list_of_clients.append(client)

	def removeClient(self, client):
		self.list_of_clients.remove(client)

	def checkIfClientInChatroom(self, client):
		return client in self.list_of_clients