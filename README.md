# PythonMPPclient
A client for multiplayerpiano made in python.


# Example usage
```python
import Client # import client
client = Client.Client() # construct client

def sendChat(m):
    client.sendArray([{"m": "a", "message": m}]) # send chat message

def OnConnect():
    client.setChannel("example") # set channel to example
    sendChat("hello from python") # send chat message
    
client.eventEmitter.on("connect", OnConnect) # connect event
client.connect() # make client connect
```
