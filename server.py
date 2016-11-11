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
JOIN_CHATROOM = "JOIN_CHATROOM: "
LEAVE_CHATROOM = "LEAVE_CHATROOM: "
CLIENT_NAME = "CLIENT_NAME: "
JOIN_ID = "JOIN_ID: "
RESPONSE_PACKET_TWO = 2
STUDENT_ID = "13319349"
allThreadsWorking = []
waiting_conns = []
PORT = 8000
chatroom_names = ["first", "second"]
chatroom_dict = {} # roomref, chatroom object
client_dict = {} #joinid, client object
error_dict = {1: 'Invalid chatroom ref', 2: 'Client is not part of this chat', 3: 'Client does not exist on chat server'}
chatroomName_ToRoomRef = {}



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
			clientSocket.close()
			print ("Thread finished!\nClosed connection!")
		else:
			print response
			clientSocket.sendall(response.encode())
			displayCurrentStats()

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
			print ("Client doesnt exist...")
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
			del client_dict[client_joinID]
			response = "LEFT_CHATROOM: %d\nJOIN_ID: %d" % (roomrefToLeave, client_joinID)
			return response


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
	x = Chatroom.Chatroom(chatroomName, "localhost", 8000, roomref, [])
	chatroom_dict[roomref] = x
	chatroomName_ToRoomRef[chatroomName] = roomref


def handleInput(data):
	if (JOIN_CHATROOM in data):
		return JOIN_CHATROOM
	elif (LEAVE_CHATROOM in data):
		return LEAVE_CHATROOM

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
		x = Chatroom.Chatroom(name, "localhost", 8000, roomref, [])
		chatroom_dict[roomref] = x
		chatroomName_ToRoomRef[name] = roomref
		roomref += 1

def main():
	
	setUpChatrooms()
	serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	serversocket.bind((HOST, PORT))
	serversocket.listen(5)

	while 1:
		print ("Waiting for client connections...")
		#accept connections from outside
		(clientsocket, address) = serversocket.accept()
		waiting_conns.append((clientsocket, address))
		print ("Current amount of queued connections: %d" % (len(waiting_conns)))

		for t in allThreadsWorking:
				if (not t.isAlive()):
					allThreadsWorking.remove(t)
					print ("Removed an unworking thread from the pool.")

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