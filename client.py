class Client:
	'Common base class for all connected classes'
	connectedClientsCount = 0

	def __init__(self, join_id, name, room_ref, port, ipaddress):
		self.join_id = join_id
		self.name = name
		self.room_ref = room_ref
		self.port = port
		self.ipaddress = ipaddress
		Client.connectedClientsCount += 1

	def displayClientCount(self):
		print "Total Clients Connected: %d" % Client.connectedClientsCount

	def displayClientDetails(self):
		print "Name: %s, Join ID: %d, Room Ref: %d, Port: %d, IP: %s" % (self.name, self.join_id, self.room_ref, self.port, self.ipaddress)

	def getClientName(self):
		return self.name

	def getClientPort(self):
		return self.port

	def getClientIPAddress(self):
		return self.ipaddress

	def getClientRoomRef(self):
		return self.room_ref
		