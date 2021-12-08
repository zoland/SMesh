# SMesh
Smart Manor project : Simple Mesh network based on ESP-Now for ESP32

SMesh is a tiny mesh network  which I created for my Smart Manor projects. Smesh is Iimplemented on the ESP32 microcontroller, based on the Expressif ESP-Now protocol using the terminology used in MQTT - The Publisher publishes news, the contents of which the Subscriber can receive over the network by specifying the name of the news topic. Knowledge of the MAC addresses of network nodes is not required.

The news that is published by the Publisher can be implicit (broadcast) or explicit, for which the Subscriber will need to additionally specify:
    • quality level of delivery - QoS, which allows the Publisher to determine the delivery protocol of publications
    • expirie time for the Subscriber of news. If no updates have been received during this period, it is possible that the Publisher is not online. With an explicit request, the Subscriber is notified of this in order to make a decision - to wait until the connection is restored or to continue working.
      
The quality level of delivery of an explicit subscription QoS determines how carefully the Publisher will try to deliver news to Subscribers. If there are several Subscribers, then the Publisher provides delivery with the highest level declared by one of the Subscribers. Higher QoS levels are more reliable, but involve more latency. Acceptable levels:
    • 0 : news delivery without Subscriber confirmation.
    • 1 : news delivery with confirmation of delivery by the Subscriber. When publishing, the Publisher will be notified that the news has been delivered safely or not. This is useful if the Publisher needs to control the Subscriber's presence on the network.
    • 2 : unlike the quality of delivery QoS=1, the content of the news and the serial number remain unchanged until the subscriber's confirmation of receipt is received. This is useful in case of publishing news about emergency situations to fix the moment of the incident.
      
Foolproof protection is practically absent in order to minimize the code under the assumption that the jambs associated with the operation will be identified independently at the network setup stage.
The only significant limitation other than those imposed by the ESP-Now protocol is the uniqueness of the names of news topics published by the Publisher.

Due to the fact that time synchronization is not implemented in the network, the date of the event can be determined only by the difference in the serial numbers of publications.


There is only four functions with one class Smesh:

SMesh ( node_name [, on_receive_func] ) - configuration
SMesh.post ( topic, data ) - post news by Publisher
SMesh.subs ( topic [,QoS=0] [,expirie=0]) - set explisit subscribe with parameters
SMesh.request ( topic ) - request explisit subscribe

That’s all )
