from paho.mqtt import client as mqtt_client
import random


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

        self.connectMqtt()

    def subscribeTotopic(self, topic):
        if self.client is not None:
            self.client.subscribe(topic)

    def connectMqtt(self):
        def on_connect(client, userdata, flags, rc):
            if self.funcOnConnect:
                self.funcOnConnect(rc)
        
        def on_disconnect(client, userdata, rc):
            if rc != 0:
                if self.funcOnDisconnect:
                    self.funcOnDisconnect()
                self.client = self.connectMqtt()

        def on_message(client, userdata, msg):
            print(f"Received message: {msg.payload.decode()} from topic: {msg.topic}")

        client = mqtt_client.Client(f"mqtt_client_{self.name}_{random.randint(1000,9999)}")
        client.username_pw_set(self.user, self.passw)
        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        client.on_message = on_message
        try:
            # Set a keepalive interval (60 seconds)
            client.connect(self.brokerUrl, self.port, keepalive=60)
            # Start a background thread to maintain the connection
            client.loop_start()
        except:
            client = None
            print(f"Connection error to Mqtt server: {self.brokerUrl}")

        self.client = client


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