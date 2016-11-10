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
UTF = "utf-8"
JOIN_CHATROOM = "JOIN_CHATROOM: "
CLIENT_NAME = "CLIENT_NAME: "
RESPONSE_PACKET_TWO = 2
STUDENT_ID = "13319349"
allThreadsWorking = []
waiting_conns = []
PORT = 8000
chatroom_names = ["first", "second"]
chatroom_dict = {} # name, chatroom object
client_dict = {} #joinid, client object
error_dict = {1: 'Invalid chatroom name'}



def analysePacket(clientSocket, address):
	data = (clientSocket.recv(BUFFER)).decode(UTF)
	data = str(data)
	whichPacket = handleInput(data)
	if whichPacket == JOIN_CHATROOM:
		print ("Client requesting to join...")
		packetArray = data.split("\\n")
		if checkChatroomName(packetArray): # the packet contains an existing chat room
			print ("Valid chatroom!")
			response = joinClient(packetArray, address)
			clientSocket.sendall(response.encode())
			clientSocket.close()
			displayCurrentStats()
		else:
			sendErrMsg(1, clientSocket)
			clientSocket.close()

	elif whichPacket == RESPONSE_PACKET_TWO:
		clientSocket.close()
	print ("Thread finished!\nClosed connection!")

def checkChatroomName(packet):
	for name in chatroom_names:
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
	firstline = packet[0]
	lastLine = packet[3]
	chatroomName = firstline[len(JOIN_CHATROOM):(len(firstline))]
	chatroom = chatroom_dict[chatroomName]
	room_ref = chatroom.getRoomRef()
	join_id = randint(1, 100)
	while(client_dict.has_key(join_id)):
		join_id = randint(1, 100)
	New_Client = Client.Client(join_id, lastLine[len(CLIENT_NAME):len(lastLine)], room_ref, address[1], address[0])
	client_dict[join_id] = New_Client
	chatroom.addClient(New_Client)
	print ("Successfully added client!")
	ipaddress = chatroom.getIPAddress()
	port = chatroom.getPort()
	return getJoinedResponse(chatroomName, ipaddress, port, room_ref, join_id)

def displayCurrentStats():
	print "=== CURRENT CHATROOMS ==="
	for x in chatroom_names:
		chatroom_dict[x].displayChatroomDetails()

	print "=== CHATROOM CLIENTS ==="
	for x in chatroom_names:
		clients = chatroom_dict[x].getListOfClients()
		for y in clients:
			if (y is not None):
				y.displayClientDetails()


	print "=== CURRENT CLIENTS CONNECTED ON THE SERVER ==="
	for x in client_dict:
		client_dict[x].displayClientDetails()
	print "====================="

def handleInput(data):
	if ("JOIN_CHATROOM" in data):
		return JOIN_CHATROOM


def setUpChatrooms():
	roomref = 1
	for name in chatroom_names:
		x = Chatroom.Chatroom(name, "localhost", 8000, roomref, [])
		chatroom_dict[name] = x
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