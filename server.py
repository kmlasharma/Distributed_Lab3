import argparse
import time
import socket
import threading
from random import randint
import chatrooms as Chatroom
import client as Client
import sys

max_threads = 10
HOST = "10.62.0.145"
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
PORT = 8010
chatroom_names = ["first", "second"]
chatroom_dict = {} # roomref, chatroom object
client_dict = {} #joinid, client object
error_dict = {1: 'Invalid chatroom ref', 2: 'Client is not part of this chat', 3: 'Client does not exist on chat server', 
4: 'Invalid Join ID', 5: 'Invalid Join ID, client name combination'}
chatroomName_ToRoomRef = {} #chatroomname, roomref
clientName_ToJoinID = {}
clientWhoLeftChat_dict = {} #roomref, client
clientNamesActive = []
isSocketAlive = True
def analysePacket(clientSocket, address):
	while isSocketAlive:
		data = (clientSocket.recv(BUFFER)).decode(UTF)
		if (data):
			data = str(data)
			print "DATA: %s" % data
			whichPacket = handleInput(data)
			packetArray = data.split("\n")
			print ("PACKET ARRAY: %s") % packetArray
			if whichPacket == JOIN_CHATROOM:
				print ("Client requesting to join...")
				if checkJoinChatroomName(packetArray): # the packet contains an existing chat room
					print ("Client joining an existing chatroom...")
				else:
					if (len(chatroom_names) < MAX_CHATROOMS):
						print ("Creating a new chatroom...")
						createChatroom(packetArray)
				joinClient(packetArray, clientSocket)
				displayCurrentStats()

			elif whichPacket == LEAVE_CHATROOM:
				print ("Client requesting to leave...")
				response = leaveClient(packetArray, clientSocket)
				if (response == ""):
					print ("Thread finished!\nClosed connection!")
				displayCurrentStats()

			elif whichPacket == DISCONNECT_CHATROOM:
				print ("Client requesting to disconnect")
				disconnectClient(packetArray)
				return

			elif whichPacket == CHAT:
				print ("Client request to send a msg to a chatroom")
				sendMsg(packetArray, clientSocket)

			elif whichPacket == HELO_TEXT:
				response = "HELO BASE_TEXT\nIP:%s\nPort:%d\nStudentID:%s" % (HOST, PORT, STUDENT_ID)
				clientSocket.sendall(response.encode())
				
			elif whichPacket == KILL_SERVICE:
				print "Client requesting to kill service"
				clientSocket.close()
				sys.exit()
				return
			else:
				print "UNKNOWN!!!!!!!!"


def disconnectClient(packetArray):
	clientname = isolateTextFromInput(packetArray[2], CLIENT_NAME)
	joinid = clientName_ToJoinID[clientname]
	client = client_dict[joinid]
	clientsocket = client.getClientSocket()
	if not clientname in clientNamesActive:
		print "This client %s is not on the chat server.." % clientname
		sendErrMsg(3, clientsocket)
	else:
		clientsocket.close()
		clientNamesActive.remove(clientname)
		roomref = client.getClientRoomRef()
		chatroom = chatroom_dict[roomref]
		chatroom.removeClient(client)
		del client_dict[joinid]
		print "Successfully disconnected client."
		isSocketAlive = False

				
def sendMsg(packetArray, socket):
	joinid = int(isolateTextFromInput(packetArray[1], JOIN_ID))
	if (client_dict.has_key(joinid)):
		clientname = isolateTextFromInput(packetArray[2], CLIENT_NAME)
		print clientName_ToJoinID
		print "LOOK UP!!!!!!"
		if (clientName_ToJoinID[clientname] == joinid):
			client = client_dict[joinid]
			roomref = int(isolateTextFromInput(packetArray[0], CHAT))
			if (roomref == client.getClientRoomRef()):
				chatroom = chatroom_dict[roomref]
				msg = isolateTextFromInput(packetArray[3], MESSAGE)
				response = "CHAT: %d\nCLIENT_NAME: %s\nMESSAGE: %s\n\n" % (roomref, clientname, msg)
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




def leaveClient(packetArray, socket):
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
				response = "LEFT_CHATROOM: %d\nJOIN_ID: %d\n\n" % (roomrefToLeave, client_joinID)
				client = clientWhoLeftChat_dict[roomrefToLeave]
				socket = client.getClientSocket()
				socket.sendall(response.encode())
				return
			else:
				print ("Client doesnt exist on chat server...")
				sendErrMsg(3, socket)
				return ""
		print "WE getting %d" % client_joinID
		print chatroom.getChatroomName() 
		client = client_dict[client_joinID]
		found = False
		list = chatroom.getListOfClients()
		for cl in list:
			id = cl.getJoinId()
			print id
			print client_joinID
			if (id == client_joinID):
				print "Client is found in this chatroom"
				found = True
				break
		if not found:
			print ("The client: %s is not a member of the chatroom: %s. Sending error msg...") % (client.getClientName(), chatroom.getChatroomName())
			#sendErrMsg(2, socket)
			response = "LEFT_CHATROOM: %d\nJOIN_ID: %d\n" % (roomrefToLeave, client_joinID)
			socket.sendall(response.encode())
			msg = "CHAT: %d\nCLIENT_NAME: %s\nMESSAGE: %s has left this chatroom.\n\n" % (roomrefToLeave, client.getClientName(), client.getClientName())
                        broadcastMsgToChatroom(msg, chatroom)
			return ""
		else:
			print ("Deleting Client from Chat Server...")
			response = "LEFT_CHATROOM: %d\nJOIN_ID: %d\n" % (roomrefToLeave, client_joinID)
			clientWhoLeftChat_dict[roomrefToLeave] = client
			del clientName_ToJoinID[client.getClientName()]
			print "Broadcasting leave msg to chatroom"
			msg = "CHAT: %d\nCLIENT_NAME: %s\nMESSAGE: %s has left this chatroom.\n\n" % (roomrefToLeave, client.getClientName(), client.getClientName())
			socket.sendall(response.encode())
			broadcastMsgToChatroom(msg, chatroom)
			chatroom.removeClient(client)
                        del client_dict[client_joinID]
                        clientNamesActive.remove(client.getClientName())

def broadcastMsgToChatroom(msg, chatroom):
	clients = chatroom.getListOfClients()
	for client in clients:
		name = client.getClientName()
		jid = client.getJoinId()
		socket = client.getClientSocket()
		socket.sendall(msg.encode())
		print socket
		print ("sent msg to %s, %d:\n%s") % (name, jid, msg)

def isolateTextFromInput(line, stripText):
	line = line.rstrip()
	return line[len(stripText):(len(line))]

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
	x = Chatroom.Chatroom(chatroomName, HOST, PORT, roomref, [])
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
	response = "ERROR_CODE: %d\nERROR_DESCRIPTION: %s\n\n" % (code, msg)
	socket.sendall(response.encode())

def getJoinedResponse(chatroom_name, ipaddress, port, roomref, join_id):
	msg = "JOINED_CHATROOM:%s\nSERVER_IP:%s\nPORT:%d\nROOM_REF:%d\nJOIN_ID:%d\n" % (chatroom_name, ipaddress, port, roomref, join_id)
	return msg

def joinClient(packet, socket):
	chatroomName = isolateTextFromInput(packet[0], JOIN_CHATROOM)
	print "DICT!!!!!!"
	print chatroomName_ToRoomRef
	room_ref = chatroomName_ToRoomRef[chatroomName]
	chatroom = chatroom_dict[room_ref]
	join_id = getValidID(1, MAX_CLIENTS, client_dict)
	clientname = isolateTextFromInput(packet[3], CLIENT_NAME)
	New_Client = Client.Client(join_id, clientname, room_ref, socket)
	client_dict[join_id] = New_Client
	chatroom.addClient(New_Client)
	print ("Successfully added client!")
	ipaddress = chatroom.getIPAddress()
	port = chatroom.getPort()
	clientNamesActive.append(clientname)
	clientName_ToJoinID[clientname] = join_id
	msg = getJoinedResponse(chatroomName, ipaddress, port, room_ref, join_id)
	socket.sendall(msg.encode())
	chatMsg = "CHAT: %d\nCLIENT_NAME: %s\nMESSAGE: %s has joined this chatroom.\n\n" % (room_ref, clientname, clientname)
	broadcastMsgToChatroom(chatMsg, chatroom)

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
		x = Chatroom.Chatroom(name, HOST, PORT, roomref, [])
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
		
		for t in allThreadsWorking:
				if (not t.isAlive()):
					allThreadsWorking.remove(t)
					print ("Removed an unworking thread from the pool.")

		(clientsocket, address) = serversocket.accept()
		waiting_conns.append((clientsocket,address))
		print ("Current amount of queued connections: %d" % (len(waiting_conns)))

		if (len(allThreadsWorking) <= max_threads): #can create a new thread
			if (len(waiting_conns) > 0):
				connTuple = waiting_conns.pop()
				clsocket = connTuple[0]
				address = connTuple[1]
				thread = threading.Thread(target=analysePacket, args = (clsocket, address))
				thread.setDaemon(True)
				allThreadsWorking.append(thread)
				thread.start()
				print ("Current working threads: " + str(len(allThreadsWorking)))
			
				
		print ("Still Current amount of queued connections: %d" % (len(waiting_conns)))

main()
