class Client:
	'Common base class for all connected classes'
	connectedClientsCount = 0

	def __init__(self, join_id, name, room_ref, socket):
		self.join_id = join_id
		self.name = name
		self.room_ref = room_ref
		self.socket = socket
		Client.connectedClientsCount += 1

	def displayClientCount(self):
		print "Total Clients Connected: %d" % Client.connectedClientsCount

	def displayClientDetails(self):
		print "Name: %s, Join ID: %d, Room Ref: %d" % (self.name, self.join_id, self.room_ref)

	def getClientName(self):
		return self.name

	def getClientSocket(self):
		return self.socket

	def getClientRoomRef(self):
		return self.room_ref
		