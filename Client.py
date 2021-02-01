import websocket, event_emitter, time, json, threading

class Thread(threading.Thread):
    def __init__(self,  *args, **kwargs):
        super(Thread, self).__init__(*args, **kwargs)
        self._stop_event = threading.Event()
    def stop(self):
        self._stop_event.set()
    def stopped(self):
        return self._stop_event.is_set()

class Client:
    def __init__(self):
        self.eventEmitter = event_emitter.EventEmitter()
        self.uri = "wss://www.multiplayerpiano.com:443"
        self.ws = None
        self.serverTimeOffset = 0
        self.user = None
        self.participantId = None
        self.channel = None
        self.ppl = None
        self.connectionTime = None
        self.connectionAttempts = 0
        self.desiredChannelId = None
        self.desiredChannelSettings = None
        self.pingInterval = None
        self.noteBuffer = []
        self.noteBufferTime = 0
        self.noteFlushInterval = None
        self.canConnect = True
        self.isConnected = False
        self.eventEmitter.on("hi", self.evHi)
        self.eventEmitter.on("t", self.evT)
        self.eventEmitter.on("ch", self.evCh)
        self.eventEmitter.on("p", self.evP)
        self.eventEmitter.on("m", self.evM)
        self.eventEmitter.on("bye", self.evBye)
    def evHi(self, msg):
        self.user = msg["u"]
        self.receiveServerTime(msg["t"], msg["e"] or None)
        if self.desiredChannelId:
            self.setChannel()
    def evT(self, msg):
        self.receiveServerTime(msg["t"], msg["e"] or None)
    def evCh(self, msg):
        self.desiredChannelId = msg["ch"]["_id"]
        self.desiredChannelSettings = msg["ch"]["settings"]
        self.channel = msg["ch"]
        if msg.p:
            self.participantId = msg["p"]
        self.setParticipants(msg["ppl"])
    def evP(self, msg):
        self.participantUpdate(msg);
        self.eventEmitter.emit("participant update", self.findParticipantById(msg["id"]));
    def evM(self, msg):
        if self.ppl[msg["id"]]:
            self.participantUpdate(msg);
    def evBye(self, msg):
        self.removeParticipant(msg["p"]);
    def connect(self):
        if not self.canConnect or self.isConnected:
            return
        self.ws = websocket.WebSocketApp(self.uri, on_message=self.OnMessage, on_error=self.OnError, on_close=self.OnClose, origin="https://www.multiplayerpiano.com")
        self.ws.on_open = self.OnOpen
        self.ws.run_forever()
    def send(self, m):
        if self.isConnected:
            self.ws.send(m)
    def sendArray(self, a):
        self.send(json.dumps(a))
    def setChannel(self, id, set=None):
        self.desiredChannelId = id or self.desiredChannelId or "lobby"
        self.desiredChannelSettings = set or self.desiredChannelSettings or None
        self.sendArray([{"m": "ch", "_id": self.desiredChannelId, "set": self.desiredChannelSettings}])
    def countParticipants(self):
        return len(self.ppl)
    def participantUpdate(self, update):
        part = self.ppl[update.id] or None
        if part == None:
            part = update
            self.ppl[part.id] = part
            self.eventEmitter.emit("participant added", part)
            self.eventEmitter.emit("count", self.countParticipants())
        else:
            if update.x:
                part.x = update.x
            if update.y:
                part.y = update.y
            if update.color:
                part.color = update.color
            if update.name:
                part.name = update.name
    def removeParticipant(self, id):
        if self.ppl[id]:
            part = self.ppl[id]
            del self.ppl[id]
            self.eventEmitter.emit("participant removed", part)
            self.eventEmitter.emit("count", self.countParticipants())
    def setParticipants(self, ppl):
        for id in self.ppl:
            found = False
            for j in range(len(ppl)):
                if ppl[j].id == id:
                    found = True
                    break
            if not found:
                self.removeParticipant(id)
        for i in range(len(ppl)):
            self.participantUpdate(ppl[i])
    def pingServer(self, interval):
        self.sendArray([{"m": "t", "e": time.time()}])
        time.sleep(interval)
        self.pingServer(interval)
    def flushNotes(self, interval):
        if self.noteBufferTime and len(self.noteBuffer) > 0:
            self.sendArray([{"m": "n", "t": self.noteBufferTime + self.serverTimeOffset, "n": self.noteBuffer}])
            self.noteBufferTime = 0
            self.noteBuffer = []
    def OnMessage(self, msg):
        transmission = json.loads(msg)
        for i in range(len(transmission)):
            self.eventEmitter.emit(transmission[i]["m"], transmission[i])
    def OnClose(self):
        self.user = None
        self.participantId = None
        self.channel = None
        self.setParticipants([])
        self.pingInterval.stop()
        self.noteFlushInterval.stop()
        self.eventEmitter.emit("disconnect")
        self.eventEmitter.emit("status", "Offline mode")
    def OnError(self, err):
        self.eventEmitter.emit("wserror", err)
        self.ws.close()
    def OnOpen(self):
        self.connectionTime = time.time()
        self.isConnected = True
        self.sendArray([{"m": "hi"}])
        self.pingInterval = Thread(target=self.pingServer, args=(20,))
        self.pingInterval.start()
        self.noteBuffer = []
        self.noteBufferTime = 0
        self.noteFlushInterval = Thread(target=self.flushNotes, args=(.2,))
        self.noteFlushInterval.start()
        self.eventEmitter.emit("connect")
        self.eventEmitter.emit("status", "Joining channel...")