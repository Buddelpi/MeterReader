from paho.mqtt import client as mqtt_client
import random
import threading
import time


class MqttHandler():
    def __init__(self, mqttDesc:dict, name="", funcOnConnect=None, funcOnDisconnect=None) -> None:
                             
        self.brokerUrl =  mqttDesc["brokerUrl"]
        self.port = mqttDesc["brokerTcpPort"]
        self.user = mqttDesc["user"]
        self.passw = mqttDesc["pass"]
        self.name = name
        self.funcOnConnect = funcOnConnect
        self.funcOnDisconnect = funcOnDisconnect
        self.client = None
        self.subscribeDict = {}

        # reconnect/backoff state
        self._reconnect_delay = 1.0
        self._max_reconnect_delay = 60.0
        self._reconnect_timer = None
        self._reconnect_lock = threading.Lock()

        # try immediate connect (failures are retried in background)
        self.connectMqtt()

    def subscribeTotopic(self, topic, callback=None):
        if self.client is not None:
            self.client.subscribe(topic)
            self.subscribeDict[topic] = callback

    def connectMqtt(self):
        # callbacks with signatures compatible with both callback API v1 and v2
        def on_connect(client, userdata, flags, rc=None, properties=None):
            # rc present in both APIs (v2 passes properties as extra arg)
            if self.funcOnConnect:
                try:
                    # many handlers expect rc parameter
                    self.funcOnConnect(rc)
                except TypeError:
                    # fallback if handler expects no args
                    self.funcOnConnect()
        
        def on_disconnect(client, userdata, rc=0, properties=None):
            # rc present in both APIs
            if rc != 0:
                if self.funcOnDisconnect:
                    try:
                        self.funcOnDisconnect()
                    except TypeError:
                        pass
                # schedule reconnect with backoff
                self._schedule_reconnect()

        def on_message(client, userdata, msg):
            # message callback retained as-is
            try:
                payload = msg.payload.decode()
            except Exception:
                payload = msg.payload
            print(f"Received message: {payload} from topic: {msg.topic}")
            if msg.topic in self.subscribeDict.keys() and self.subscribeDict[msg.topic] is not None:
                try:
                    self.subscribeDict[msg.topic](payload)
                except Exception:
                    pass
                

        # create client (do not pass callback_api_version here; use callbacks that accept both forms)
        client = mqtt_client.Client(client_id=f"mqtt_client_{self.name}_{random.randint(1000,9999)}")
        client.username_pw_set(self.user, self.passw)
        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        client.on_message = on_message

        # assign early to avoid destructor issues if connect raises
        self.client = client

        try:
            client.connect(self.brokerUrl, self.port, keepalive=60)
            client.loop_start()
            # reset backoff on success
            with self._reconnect_lock:
                self._reconnect_delay = 1.0
                if self._reconnect_timer:
                    self._reconnect_timer.cancel()
                    self._reconnect_timer = None
        except Exception as e:
            print(f"Connection error to MQTT server {self.brokerUrl}:{self.port} -> {e}")
            # schedule reconnect instead of immediate recursion
            self._schedule_reconnect()

    def _attempt_reconnect(self):
        with self._reconnect_lock:
            # prevent overlapping attempts
            try:
                # create a fresh client object to avoid stale internal state
                client = mqtt_client.Client(client_id=f"mqtt_client_{self.name}_{random.randint(1000,9999)}")
                client.username_pw_set(self.user, self.passw)
                # reuse the same callback wrappers
                client.on_connect = self.client.on_connect
                client.on_disconnect = self.client.on_disconnect
                client.on_message = self.client.on_message
                self.client = client

                client.connect(self.brokerUrl, self.port, keepalive=60)
                client.loop_start()
                # success -> reset delay
                self._reconnect_delay = 1.0
            except Exception as e:
                print(f"Reconnect attempt failed: {e}")
                self._reconnect_delay = min(self._reconnect_delay * 2, self._max_reconnect_delay)
                self._schedule_reconnect()

    def _schedule_reconnect(self):
        with self._reconnect_lock:
            if self._reconnect_timer and self._reconnect_timer.is_alive():
                return
            delay = self._reconnect_delay
            self._reconnect_timer = threading.Timer(delay, self._attempt_reconnect)
            self._reconnect_timer.daemon = True
            self._reconnect_timer.start()


    def publish2opic(self, topic, msg):
        resSucc = False
        resMsg = "Not connected to any broker!"

        if self.client:

            try:
                result = self.client.publish(topic, msg)
                status = result[0]
            except:
                status = 1
                
            if status == 0:
                resMsg = f"Sent topic: {topic}"
                resSucc = True
            else:
                resMsg = f"Failed to send message to topic {topic}"
           
        return resSucc, resMsg