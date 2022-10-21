from socket import *
from Peers import *


SIZE = 1024 

HEADER = []
peers = []

def requestFromTracker(givenFileName, serverName, serverPort):

    try: 
        HEADER = []
        
        #Creates a streaming socket
        clientSocket = socket(AF_INET, SOCK_DGRAM)

        #Tries to connect to the existing socket and port
        request = 'GET ' + givenFileName + '.torrent\n'
        clientSocket.settimeout(0.5)
        clientSocket.sendto(request.encode(),(serverName, serverPort))


        #Seperate header from payload
        data = clientSocket.recv(SIZE)
        entireFirstPacket = data.split('\n\n'.encode())

        #Grab the header and print it
        header = entireFirstPacket[0].decode().split('\n')
        
        #Grab all the IP and Ports in the File
        header = ' '.join(header)
        header = header.split(' ')
        
        #HEADER[0] - NUM_BLOCKS
        #HEADER[1] - FILE_SIZE
        #HEADER[2] - IP1
        #HEADER[3] - PORT1
        #HEADER[4] - IP2
        #HEADER[5] - PORT2
        HEADER.append(int(header[header.index('NUM_BLOCKS:') + 1]))   
        HEADER.append(int(header[header.index('FILE_SIZE:') + 1]))
        HEADER.append(header[header.index('IP1:') + 1])
        HEADER.append(int(header[header.index('PORT1:') + 1]))
        HEADER.append(header[header.index('IP2:') + 1])
        HEADER.append(int(header[header.index('PORT2:') + 1]))
        clientSocket.close()

        print('FINISHED UDP')

        return HEADER
    except timeout:
        print('UDP TIMEOUT')
        return []



