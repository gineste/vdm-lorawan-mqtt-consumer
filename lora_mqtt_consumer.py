import csv
import json
import os
import time
import logging

from catena_decoder import CatenaDecoder
import paho.mqtt.client as mqtt


class LoraConsummer :
    def __init__ ( self , brokerIp , subscribe_topic , publish_topic ) :
        self._broker_ip = brokerIp
        self._subtopic = subscribe_topic
        self._pubtopic = publish_topic

        logging.info ( "Create mqtt client" )
        self._mqttclient = mqtt.Client ( "LoraConsummer" )  # create new instance
        self._mqttclient.on_message = self.on_message  # attach function to callback
        self._mqttclient.connect ( self._broker_ip , 1883 )
        self._mqttclient.subscribe ( self._subtopic )

        logging.info ( "Create catena payload decoder" )
        self._lora_decoder = CatenaDecoder.CatenaDecoder ()

        self._logfilename = "{}_lora_log.csv".format(int(time.time()))
        logging.info ( "Log in : {}".format(self._logfilename) )


    def run ( self ) :
        self._mqttclient.loop_forever ()

    def on_message ( self , client , userdata , message ) :
        jsonString = str ( message.payload.decode ( "utf-8" ) )
        jsonMsg = json.loads ( jsonString )
        msg = {'ts' : int ( time.time () * 1000 ) , 'topic' : "lora" , 'device' : jsonMsg [ "devEUI" ] ,
               'data' : (self._lora_decoder.parse ( jsonMsg [ "fPort" ] , jsonMsg [ "data" ] ))}
        logging.info ( "Message : {}".format(msg))

        file_exists = os.path.isfile ( self._logfilename )
        with open(self._logfilename, "a", newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=msg.keys())
            if not file_exists:
                logging.info ( "Create {}".format(self._logfilename) )
                writer.writeheader()
            writer.writerow(msg)

        self._mqttclient.publish ( self._pubtopic , json.dumps ( msg ) )

if __name__ == "__main__" :
    broker_address = "avnet-rpi01.local"
    lora_sub_topic = "/lora/devices/uplink"
    lora_pub_topic = "/data/lora"

    logging.basicConfig ( format='%(asctime)s:%(levelname)s:%(message)s' , level=logging.DEBUG )
    logging.info ( "Run consummer" )
    myConsummer = LoraConsummer ( broker_address , lora_sub_topic , lora_pub_topic )
    myConsummer.run ()
