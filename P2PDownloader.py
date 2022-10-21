from cmath import sqrt
from multiprocessing import process
from socket import *
from Peers import *
from TCPPeerDownload import requestFromPeer
from UDPGetTorrent import *
import sys
import os
import threading
import time


arguments = str(sys.argv)
print(arguments)


if len(sys.argv) == 1:
    givenFileName = 'redsox.jpg'
    serverName = 'date.cs.umass.edu'
    serverPort = 19876
else:
    givenFileName = sys.argv[1]
    serverName = sys.argv[2]
    serverPort = int(sys.argv[3])

#Global Variables 
header = []              #Grabs the header from UDP
incompletedBlocks = []   #Contains all the blocks not completed yet
totalBlocks = 0          #Stores total number of blocks

knownPeers = []          #Peers that we have sent a request and know their speed are stored here
unknownPeers = []        #Peers that haven't been benchmarked are stored here
activePeers = []         #The peers that we are currently working with are stored here 

"""
NOTES
2 Different Threads used
TrackerThread      - In Charge of grabing UDP, finding peers, testing these peers connection to be stored/benchmarked
WorkerThread        - Once Peers are knowed it will open connection with the fast currently Avaliable Thread

"""

#Looks at the known peers and will establish a connection with the fastest avaliable one
def workerFuncion(id):
    
    global incompletedBlocks
    global knownPeers
    global unknownPeers
    global activePeers

    lock = threading.Lock()

    while True:
        
        #Check if we have completed The download
        lock.acquire()
        if len(incompletedBlocks) == 0: 
            lock.release()
            break 
        lock.release() 
        
        #Go through all the known peers
        for i in range(0, len(knownPeers)):
            lock.acquire()
            curPeer = knownPeers[i] 

            #We only care if that peer is not active
            if curPeer in activePeers: 
                lock.release() 
                continue
            else: 
                failedBlocks = []

                #Before Download we check if need to still download
                if (len(incompletedBlocks) == 0):
                    lock.release()
                    break

                #Move that peer to the active peers (No other thread can use that peer)
                activePeers.append(curPeer)
                block = incompletedBlocks.pop(0)
                lock.release() 

                #Start a download with that peer
                time.sleep(0.1)
                requestFromPeer(givenFileName, curPeer, block, failedBlocks, id)
                
                #Release that peer
                lock.acquire()
                activePeers.remove(curPeer)
                lock.release() 

                #Checks if we have any timeouts
                if len(failedBlocks) != 0:
                    knownPeers.remove(curPeer)
                    incompletedBlocks += failedBlocks
                    print(incompletedBlocks)
                break 

#Takes a new peer and benchmarks it
def processUnknownPeer(id):
    global incompletedBlocks
    global knownPeers
    global unknownPeers
    global activePeers
    lock = threading.Lock()

    #Check to see if we finished everything
    lock.acquire() 
    if len(incompletedBlocks) == 0:
        lock.release()
        return
    if len(unknownPeers) == 0:
        lock.release()
        return
    curPeer = unknownPeers.pop(0)
    block = incompletedBlocks.pop(0)
    failedBlocks = []
    lock.release() 

    #Benchmark that peer
    print("TRACKER IS REQUESTING TCP")
    requestFromPeer(givenFileName, curPeer, block, failedBlocks, id)
    print("TRACKER IS FINISHED TCP")  

    #If the download failed readd it back to incompleted blocks
    if len(failedBlocks) != 0:
        incompletedBlocks += failedBlocks
        print(incompletedBlocks)
    else:

        #Add it the known peers, and then sort it by speed, FAST -> SLOW
        lock.acquire() 
        knownPeers.append(curPeer)
        sortedBySpeed = sorted(knownPeers, key=lambda x: x.speed)
        sortedBySpeed.reverse()
        knownPeers = sortedBySpeed
        lock.release() 

#Grabs two new peers to benchmark
def findNewPeers(id):
    global knownPeers
    global unknownPeers
    global activePeers
    lock = threading.Lock()

    #Use UDP Get Torrent to grab two peers
    twoNewPeers = []
    twoNewPeers += getTwoNewPeers(givenFileName, serverName, serverPort)

    #If that peer is already benchmarked ignore it
    lock.acquire()
    for peer in twoNewPeers:
        ip = peer.ip
        port = peer.port
        if not any(x.port == port and x.ip == ip for x in knownPeers):
            unknownPeers.append(peer)
    lock.release() 


#This Thread Type will update the peers and benchmark them
class TrackerTread(threading.Thread):
    def __init__(self, id):

        global knownPeers
        global unknownPeers
        global activePeers

        threading.Thread.__init__(self)

        self.id = id
        
        #Starting Thread will grab 2 peers
        twoNewPeers = []
        while True:
            twoNewPeers += getTwoNewPeers(givenFileName, serverName, serverPort)
            if len(twoNewPeers) != 0:
                break
    
        #We will determine how many total blocks that we have and add them to a queue
        global totalBlocks
        totalBlocks = header[0]
        for i in range (0, totalBlocks):
            global incompletedBlocks
            incompletedBlocks.append(i) 
        print(header)

        #Append unkown peers and then find 2 more peers, at this point threads a working on proccessing unkown
        unknownPeers += twoNewPeers
        time.sleep(2)
        findNewPeers(self.id)
  
    def run(self):
        global incompletedBlocks
        global knownPeers
        global unknownPeers
        global activePeers
        lock = threading.Lock()

        while True:

            #Check to see if we are done with download
            lock.acquire()
            if len(incompletedBlocks) == 0: 
                lock.release()
                break 
            lock.release()

            #We will try and process all the unkown unbenchmarked peers 
            while True: 
                lock.acquire()
                if len(unknownPeers) == 0 or len(incompletedBlocks) == 0:
                    lock.release() 
                    break 
                lock.release() 
                processUnknownPeer(self.id)
            
            #Check to see if we are done with download
            lock.acquire()
            if (len(incompletedBlocks) == 0):
                lock.release() 
                break
            lock.release() 

            #Grabs two new peers using UDP and adds them to unkownPeers
            print("GRABING FROM UDP RN")
            findNewPeers(self.id)
            
        print("KILLING THREAD", self.id)

#Will only execute 1TCP connection then exit     
# We use this type of thread in the beginning to make use of the empty threads       
class TrackerHelperThread(threading.Thread):
    def __init__(self, id):
        threading.Thread.__init__(self)
        self.id = id
    def run(self):
        processUnknownPeer(self.id)
        print("KILLING THREAD", self.id)


#This thread will grab all the best peers and establish connection between them
#Given a list of peers, we will find the best ones and           
class WorkerThread(threading.Thread): 
    def __init__(self, id):
        threading.Thread.__init__(self)
        self.id = id
    
    def run(self):
        print('ACTIVATING', self.id)
        workerFuncion(self.id)
        print("KILLING THREAD ", self.id)


def main():

    t0 = time.time()
    global knownPeers
    global unknownPeers
    global activePeers

    #Open 1 Tracker - It will stay open unitil end
    tracker = TrackerTread('T') 
    tracker.start()


    #Open 3 threads to process tracker's unknown users
    helper1 = TrackerHelperThread('H1')
    helper1.start()
    helper2 = TrackerHelperThread('H2')
    helper2.start()
    helper3 = TrackerHelperThread('H3')
    helper3.start()

    #Wait for them to complete and close
    helper1.join()
    helper2.join()
    helper3.join()
    
    #Open 3 new threads that will process known peers
    worker1 = WorkerThread(1)
    worker2 = WorkerThread(2)
    worker3 = WorkerThread(3)
    worker1.start()
    worker2.start()
    worker3.start()

    #Make main thread do work
    workerFuncion(0)
    
    #Wait for everything to finish
    tracker.join()
    worker1.join()
    worker2.join()
    worker3.join()
    
    #Calculate Statstics 
    mean = 0
    for peer in knownPeers: 
        speed = peer.speed
        mean += speed
    mean /= len(knownPeers)
    summation = 0 
    for peer in knownPeers:
        speed = peer.speed
        summation += pow(speed - mean, 2)
    summation /= len(knownPeers) - 1
    sd = sqrt(summation)

    #Print Statistics of run
    print("MEAN IS ", mean)
    print("SD IS", sd)

    #Merge all the blocks together
    mergeFiles()
    t1 = time.time()
    print('Total Run Time: ', t1 - t0)

#We will store the Peers as an object along with 
def getTwoNewPeers(givenFileName, serverName, serverPort):

    global header
    header = requestFromTracker(givenFileName, serverName, serverPort)
    if len(header) == 0:
        return []
   
    peer1 = Peers(header[2], header[3], 0)
    peer2 = Peers(header[4], header[5], 0)

    return [peer1, peer2]

#Takes all the blocks and merges them together 
def mergeFiles():
    file = open(givenFileName, 'wb')
    file.close() 
    
    for i in range (0, totalBlocks):
        targetFile = givenFileName + str(i)
        with open(targetFile, 'rb') as input:
            with open (givenFileName, 'ab') as output:
                for line in input:
                    output.write(line)
    
        if os.path.exists(targetFile):
            os.remove(targetFile)
        else:
            print(targetFile, "Does Not Exist")
    

if __name__=="__main__":
    main()