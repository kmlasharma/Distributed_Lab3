import argparse
import time
import socket
import threading
from random import randint
import chatrooms as Chatroom
import client as Client

max_threads = 10
HOST = "localhost"
BUFFER = 1024
MAX_CHATROOMS = 100
MAX_CLIENTS = 1000
UTF = "utf-8"
HELO_TEXT = "HELO"
KILL_SERVICE = "KILL_SERVICE"
JOIN_CHATROOM = "JOIN_CHATROOM: "
LEAVE_CHATROOM = "LEAVE_CHATROOM: "
DISCONNECT_CHATROOM = "DISCONNECT: "
CLIENT_NAME = "CLIENT_NAME: "
PORT_NAME  = "PORT: "
JOIN_ID = "JOIN_ID: "
CHAT = "CHAT: "
MESSAGE = "MESSAGE: "
RESPONSE_PACKET_TWO = 2
STUDENT_ID = "13319349"
allThreadsWorking = []
waiting_conns = []
PORT = 8000
chatroom_names = ["first", "second"]
chatroom_dict = {} # roomref, chatroom object
client_dict = {} #joinid, client object
error_dict = {1: 'Invalid chatroom ref', 2: 'Client is not part of this chat', 3: 'Client does not exist on chat server', 
4: 'Invalid Join ID', 5: 'Invalid Join ID, client name combination'}
chatroomName_ToRoomRef = {} #chatroomname, roomref
clientName_ToJoinID = {}
clientWhoLeftChat_dict = {} #roomref, client
clientNamesActive = []
activeSockets = []


def analysePacket(clientSocket, address):
	data = (clientSocket.recv(BUFFER)).decode(UTF)
	data = str(data)
	whichPacket = handleInput(data)
	packetArray = data.split("\\n")
	if whichPacket == JOIN_CHATROOM:
		print ("Client requesting to join...")
		if checkJoinChatroomName(packetArray): # the packet contains an existing chat room
			print ("Client joining an existing chatroom...")
		else:
			if (len(chatroom_names) < MAX_CHATROOMS):
				print ("Creating a new chatroom...")
				createChatroom(packetArray)
		response = joinClient(packetArray, address)
		clientSocket.sendall(response.encode())
		displayCurrentStats()

	elif whichPacket == LEAVE_CHATROOM:
		print ("Client requesting to leave...")
		response = leaveClient(packetArray, address, clientSocket)
		if (response == ""):
			print ("Thread finished!\nClosed connection!")
		displayCurrentStats()

	elif whichPacket == DISCONNECT_CHATROOM:
		print ("Client requesting to disconnect")
		disconnectClient(packetArray, clientSocket)
		displayCurrentStats()

	elif whichPacket == CHAT:
		print ("Client request to send a msg to a chatroom")
		sendMsg(packetArray, clientSocket)

	elif whichPacket == HELO_TEXT:
		ipaddress = address[0]
		portnum = address[1]
		response = "HELO text\nIP:[%s]\nPort:[%d]\nStudentID:[%s]\n" % (ipaddress, portnum, STUDENT_ID)
		clientSocket.sendall(response.encode())
		clientSocket.close()

	elif whichPacket == DISCONNECT_CHATROOM:
		clientSocket.close()

def disconnectClient(packetArray, socket):
	clientname = isolateTextFromInput(packetArray[2], CLIENT_NAME)
	if not clientname in clientNamesActive:
		print "This client %s is not on the chat server.." % clientname
		sendErrMsg(3, socket)
	else:
		port = int(isolateTextFromInput(packetArray[1], PORT_NAME))
		ip = isolateTextFromInput(packetArray[0], DISCONNECT_CHATROOM)
		addr = (ip,port)
		for sock in activeSockets:
			if (sock[1] == addr):
				sock[0].close()
				activeSockets.remove((sock[0],addr))
				clientNamesActive.remove(clientname)
				joinid = clientName_ToJoinID[clientname]
				client = client_dict[joinid]
				roomref = client.getClientRoomRef()
				chatroom = chatroom_dict[roomref]
				chatroom.removeClient(client)
				del client_dict[joinid]
				print "Successfully disconnected client."

def sendMsg(packetArray, socket):
	joinid = int(isolateTextFromInput(packetArray[1], JOIN_ID))
	if (client_dict.has_key(joinid)):
		clientname = isolateTextFromInput(packetArray[2], CLIENT_NAME)
		if (clientName_ToJoinID[clientname] == joinid):
			client = client_dict[joinid]
			roomref = int(isolateTextFromInput(packetArray[0], CHAT))
			if (roomref == client.getClientRoomRef()):
				chatroom = chatroom_dict[roomref]
				msg = isolateTextFromInput(packetArray[3], MESSAGE)
				response = "CHAT: %d\nCLIENT_NAME: %s\nMESSAGE: %s" % (roomref, clientname, msg)
				broadcastMsgToChatroom(response, chatroom)
			else:
				print "Client %s is not a member of this chat: %d" % (clientname, roomref)
				print "from packet %d vs from server %d" % (roomref, client.getClientRoomRef())
				sendErrMsg(2, socket)
		else:
			print "Invalid Join ID, client name combination: %d , %s" % (joinid, clientname)
			sendErrMsg(5, socket)
	else:
		print "Invalid Join ID %d" % joinid
		sendErrMsg(4, socket)




def leaveClient(packetArray, address, socket):
	roomrefToLeave = int(isolateTextFromInput(packetArray[0], LEAVE_CHATROOM))
	if not chatroom_dict.has_key(roomrefToLeave):
		print ("Invalid chat ref. Sending error msg...")
		sendErrMsg(1, socket)
		return ""
	else: #check if client is a member of this chatroom
		chatroom = chatroom_dict[roomrefToLeave]
		client_joinID = int(isolateTextFromInput(packetArray[1], JOIN_ID))
		if not client_dict.has_key(client_joinID):
			if clientWhoLeftChat_dict.has_key(roomrefToLeave):
				print "Client has already left chat server."
				response = "LEFT_CHATROOM: %d\nJOIN_ID: %d" % (roomrefToLeave, client_joinID)
				return response
			else:
				print ("Client doesnt exist on chat server...")
				sendErrMsg(3, socket)
				return ""
		client = client_dict[client_joinID]
		if not chatroom.checkIfClientInChatroom(client):
			print ("The client: %s is not a member of the chatroom: %s. Sending error msg...") % (client.getClientName(), chatroom.getChatroomName())
			sendErrMsg(2, socket)
			return ""
		else:
			print ("Deleting Client from Chat Server...")
			chatroom.removeClient(client)
			client = client_dict[client_joinID]
			ip = client.getClientIPAddress()
			port = client.getClientPort()
			addr = (ip,port)
			for sock in activeSockets:
				if addr == sock[1]:
					"Found client requesting to leave socket"
					del client_dict[client_joinID]
					clientNamesActive.remove(client.getClientName())
					response = "LEFT_CHATROOM: %d\nJOIN_ID: %d" % (roomrefToLeave, client_joinID)
					clientWhoLeftChat_dict[roomrefToLeave] = client
					del clientName_ToJoinID[client.getClientName()]
					broadcastMsgToChatroom("Client %s has left the chatroom!" % client.getClientName(), chatroom)
					sock[0].sendall(response.encode())

def broadcastMsgToChatroom(msg, chatroom):
	clients = chatroom.getListOfClients()
	for client in clients:
		ipaddress = client.getClientIPAddress()
		port = client.getClientPort()
		addr = (ipaddress, port)
		for sock in activeSockets:
			if sock[1] == addr:
				socket = sock[0]
				socket.sendall(msg.encode())
				print ("sent msg %s") % msg

def isolateTextFromInput(line, stripText):
	return line[len(stripText):len(line)]

def getValidID(lowerbound, upperbound, dictToCheck):
	refID = randint(lowerbound, upperbound)
	while(dictToCheck.has_key(refID)):
		refID = randint(lowerbound, upperbound)
	return refID

def createChatroom(packet):
	firstline = packet[0]
	chatroomName = isolateTextFromInput(packet[0], JOIN_CHATROOM)
	chatroom_names.append(chatroomName)
	roomref = getValidID(1, MAX_CHATROOMS, chatroom_dict)
	x = Chatroom.Chatroom(chatroomName, "localhost", PORT, roomref, [])
	chatroom_dict[roomref] = x
	chatroomName_ToRoomRef[chatroomName] = roomref


def handleInput(data):
	if (JOIN_CHATROOM in data):
		return JOIN_CHATROOM
	elif (LEAVE_CHATROOM in data):
		return LEAVE_CHATROOM
	elif (DISCONNECT_CHATROOM in data):
		return DISCONNECT_CHATROOM
	elif (CHAT in data):
		return CHAT
	elif (HELO_TEXT in data):
		return HELO_TEXT
	elif (KILL_SERVICE in data):
		return KILL_SERVICE

# chatroom name mentioned in the first line of all join packets
def checkJoinChatroomName(packet):
	for name in chatroom_names:
		if (name in packet[0]):
			return True
	return False

# chatroom ref mentioned in the first line of all packets
def checkChatroomRef(packet): 
	for room in chatroom_dict:
		if (name in packet[0]):
			return True
	return False

def sendErrMsg(code, socket):
	msg = error_dict[code]
	response = "ERROR_CODE: %d\nERROR_DESCRIPTION: %s" % (code, msg)
	socket.sendall(response.encode())

def getJoinedResponse(chatroom_name, ipaddress, port, roomref, join_id):
	msg = "JOINED_CHATROOM: %s\nSERVER_IP: %s\nPORT: %d\nROOM_REF: %d\nJOIN_ID: %d" % (chatroom_name, ipaddress, port, roomref, join_id)
	return msg

def joinClient(packet, address):
	chatroomName = isolateTextFromInput(packet[0], JOIN_CHATROOM)
	room_ref = chatroomName_ToRoomRef[chatroomName]
	chatroom = chatroom_dict[room_ref]
	join_id = getValidID(1, MAX_CLIENTS, client_dict)
	clientname = isolateTextFromInput(packet[3], CLIENT_NAME)
	New_Client = Client.Client(join_id, clientname, room_ref, address[1], address[0])
	client_dict[join_id] = New_Client
	chatroom.addClient(New_Client)
	print ("Successfully added client!")
	ipaddress = chatroom.getIPAddress()
	port = chatroom.getPort()
	clientNamesActive.append(clientname)
	clientName_ToJoinID[clientname] = join_id
	return getJoinedResponse(chatroomName, ipaddress, port, room_ref, join_id)

def displayCurrentStats():
	print "=== CURRENT CHATROOMS ==="
	for x in chatroom_names:
		roomref = chatroomName_ToRoomRef[x]
		chatroom_dict[roomref].displayChatroomDetails()

	print "=== CHATROOM CLIENTS ==="
	for x in chatroom_names:
		roomref = chatroomName_ToRoomRef[x]
		clients = chatroom_dict[roomref].getListOfClients()
		for y in clients:
			y.displayClientDetails()


	print "=== CURRENT CLIENTS CONNECTED ON THE SERVER ==="
	for x in client_dict:
		client_dict[x].displayClientDetails()
	print "====================="


def setUpChatrooms():
	roomref = 1
	for name in chatroom_names:
		x = Chatroom.Chatroom(name, "localhost", PORT, roomref, [])
		chatroom_dict[roomref] = x
		chatroomName_ToRoomRef[name] = roomref
		roomref += 1

def main():
	
	setUpChatrooms()
	serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	serversocket.bind((HOST, PORT))
	serversocket.listen(10)
	
	print "Here......."
	while 1:
		print ("Waiting for client connections...")
		#accept connections from outside

		for t in allThreadsWorking:
				if (not t.isAlive()):
					allThreadsWorking.remove(t)
					print ("Removed an unworking thread from the pool.")

		for connTuple in activeSockets:
			print("POLLING ACTIVE SOCKETS")
			sock = connTuple[0]
			address = connTuple[1]
			data = (sock.recv(BUFFER)).decode(UTF)
			if (data):
				print("got one")
				thread = threading.Thread(target=analysePacket, args = (sock, address))
				allThreadsWorking.append(thread)
				thread.start()
				print ("Current working threads: " + str(len(allThreadsWorking)))

		(clientsocket, address) = serversocket.accept()
		activeSockets.append((clientsocket,address))
		waiting_conns.append((clientsocket,address))
		print ("Current amount of queued connections: %d" % (len(waiting_conns)))


		if (len(allThreadsWorking) <= max_threads): #can create a new thread
			connTuple = waiting_conns.pop()
			clsocket = connTuple[0]
			address = connTuple[1]
			thread = threading.Thread(target=analysePacket, args = (clsocket, address))
			allThreadsWorking.append(thread)
			thread.start()
			print ("Current working threads: " + str(len(allThreadsWorking)))
		print ("Still Current amount of queued connections: %d" % (len(waiting_conns)))

main()