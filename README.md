# lorawan-mqtt-consumer

## Requirements

- URSALINK UG85 LORAWAN Gateway with embedded network server https://resource.ursalink.com/document/ug85_quick_start_guide_en.pdf
- CATENA 4610 lorawan device https://store.mcci.com/collections/lorawan-iot-and-the-things-network/products/mcci-catena-4610-integrated-node-for-lorawan-technology
- Broker MQTT de type mosquitto
- Python 3.x or highest

## Usage

- Update these variables before launch 
```
broker_address = "192.168.1.45"
lora_sub_topic = "/lora/devices/uplink"
lora_pub_topic = "/data/uplink"
```
- Start the python script
```
python3 lora_mqtt_consummer.py
```
- A CSV file is created after each launch. The data in this file are also published on another topic on the same mqtt 
broker.
The colums labels are extracted from the JSON published on mqtt. 