from concurrent.futures import thread
from Peers import *
from socket import *
import socket
import time 
SIZE = 1024

#Prints to the file and returns the speed of that peer
def requestFromPeer(givenFileName, peer, blockNumber, failedBlock, threadID):

    try:
        serverName = peer.ip
        serverPort = peer.port
        
        clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        clientSocket.connect((serverName, serverPort))

        request = 'GET ' + givenFileName + ":" + str(blockNumber) + '\n'
        headerinfo = b''
        clientSocket.settimeout(10)
        clientSocket.send(request.encode())
        
        #Keep track the bytes we have written so far
        bitCounter = 0

        t0 = time.time()
        #Keeps on making requests until we get all of the header
        while True:
            data = clientSocket.recv(SIZE)
            headerinfo += data
            targetString = '\n\n'
            if targetString.encode() in headerinfo:
                break 
        
        #Seperates payload from the head, prints everything in header
        entireFirstPacket = headerinfo.split('\n\n'.encode())
        header = entireFirstPacket[0].decode().split('\n')
        
        
        #Seperates all the information in the head, grabing the Body Length
        header = ' '.join(header)
        header = header.split(' ')
        bodyByteLengthIndex = header.index('BODY_BYTE_LENGTH:') + 1 
        totalBytes = int(header[bodyByteLengthIndex])

        open(givenFileName + str(blockNumber), 'wb')

        #print("BLOCK ", blockNumber, " wants to get", len(entireFirstPacket))

        ranFirstTime = False

        #Creates a new File for the datagram from header
        for i in (range(len(entireFirstPacket) - 1)):
            bitCounter += len(entireFirstPacket[i + 1])
            with open(givenFileName + str(blockNumber), 'ab') as f:
                if ranFirstTime:
                    bitCounter += len('\n\n'.encode())
                    f.write('\n\n'.encode())
                f.write(entireFirstPacket[i + 1])
            ranFirstTime = True
        
        #Continues until we have all of the block
        while True:   
            data = clientSocket.recv(SIZE)
            bitCounter += len(data)
            with open(givenFileName + str(blockNumber), 'ab') as f: 
                f.write(data)
            #print(blockNumber, ':', bitCounter, "/", totalBytes)
            if bitCounter == totalBytes:
                break
            
        #print("PAYLOAD OF BLOCK", blockNumber, " is", len(payload))
        clientSocket.close()

        #Calculate the total time in BPS 
        t1 = time.time()
        totalTime = t1 - t0 
        bps = totalBytes / totalTime
        print('THREAD ' + str(threadID) + ' BLOCK ' + str(blockNumber) + ' ' +  serverName + ':' + str(serverPort) +' BPS: '+ str(bps))

        peer.speed = max(bps, peer.speed)

    #When we get a time out, put the block back into the queue
    except timeout:
        print('TCP TIMEOUT ON BLOCK ' + str(blockNumber) + ' TRIED TO USE ' + peer.ip + ":" + str(peer.port))
        failedBlock.append(blockNumber)

    
