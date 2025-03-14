import paho.mqtt.client as mqtt
import json
from datetime import datetime
from collections import deque
import numpy as np
import os
import requests
from dotenv import load_dotenv
import time

load_dotenv()

# MQTT Broker settings
BROKER = "broker.emqx.io"
PORT = 1883
BASE_TOPIC = os.getenv('BASE_TOPIC')
TOPIC = BASE_TOPIC + "/#"


def on_connect(client, userdata, flags, rc):
    """Callback for when the client connects to the broker."""
    if rc == 0:
        print("Successfully connected to MQTT broker")
        client.subscribe(TOPIC)
        print(f"Subscribed to {TOPIC}")
    else:
        print(f"Failed to connect with result code {rc}")



def on_message(client, userdata, msg):
    """Callback for when a message is received."""
    try:
        # Parse JSON message
        payload = json.loads(msg.payload.decode())
        
        if msg.topic.startswith(BASE_TOPIC):
            print(payload)

            type = None
            if msg.topic.endswith("/temperature"):
                type = 'Temperature'
            elif msg.topic.endswith("/pressure"):
                type = 'Pressure'
            else:
                print('invalid topic')
                return
            
            value = payload['value']
            
            address = msg.topic.split('/')[3]

            try:
                requests.post('http://localhost:8000/api/data', json={'value': float(value), 'type': type, 'address': address, 'api_key': os.getenv('API_KEY')})
            except:
                print('Request could not be made')

            
            
    except json.JSONDecodeError:
        print(f"\nReceived non-JSON message on {msg.topic}:")
        print(f"Payload: {msg.payload.decode()}")



def main():
    # Create MQTT client
    print("Creating MQTT client...")
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    client.enable_logger()

    # Set the callback functions onConnect and onMessage
    print("Setting callback functions...")
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        # Connect to broker
        print("Connecting to broker...")
        client.connect(BROKER, PORT, 60)
        
        # Start the MQTT loop
        print("Starting MQTT loop...")
        client.loop_forever()
        
    except KeyboardInterrupt:
        print("\nDisconnecting from broker...")
        # make sure to stop the loop and disconnect from the broker
        client.loop_stop()
        client.disconnect()
        print("Exited successfully")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()