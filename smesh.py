# smesh.py - Smart Mannor Project : simple mesh network based on ESP_NOW for ESP32
#
# Released under the MIT licence
# Copyright (c) @ZolAnd 2021
#
# 22-apr-2021 : @zoland - creation
# 07-oct-2021 : @zoland - changed basic logic to Pub/Sub like MQTT
# 18-nov-2021 : @zoland - add queue Pubs

import gc
from micropython import const
from machine import Timer
from utime import sleep, ticks_ms, ticks_diff

import network
from esp import espnow
gc.collect()


_verboseA = False

_t_stump    = 0

_PROTOCOL   = 'A2'
_CH_SPLIT   = '~'
_BCAST      = b'\xff'*6
_MAX_ORDER  = const(999)

_PUB_FREQ   = 3*1000 # publications frequence, 3 sec in msec


def pid_gen():
    pid = 0
    while True:
        pid = (pid + 1)%_MAX_ORDER
        yield pid


class MSG():
    def __init__(self):
        self.MAC     = ''
        self.node_name  = ''
        self.cmd     = ''  # command type
        self.topic   = ''  # topic name
        self.order   = 0     # sequence number, if Negative - message DUPlicated
        self.payload = bytearray()
        self.QoS     = 0  # Quality of Service ( 0:Fire&Forget, 1:At least once, 2:Exactly once )
        self.CRC     = 0


class NEWS(): # Publication/Subscription payload
    def __init__(self):
        self.is_pub   = True  # Pub/ Sub
        self.is_dup   = False # duplicate news
        self.MAC      = _BCAST # for Subs - Publishers MAC-address
        self.node_name  = ''
        self.order    = 0     # message counter, if Negative - message DUPlicated
        self.payload  = bytearray()
        self.QoS      = 0    # Quality of Service
        self.t_exp    = 0    # expire time for News
        self.t_stamp  = 0


class SMesh():
    
    _news    = {}    # list of topics
    _pub_que = {} # que of messages
    _nodes   = {}   # nodes map for the future
    _new_pid = pid_gen()
        
    # node_name : name
    # on_news : callback - if we plain to receive broadcast Posts, default : None
    # pub_t : time interval for sending messages
    def __init__(self, node_name, on_news = None, pub_t = _PUB_FREQ):
        
        SMesh.node_name = node_name # node_name name
        
        #  A WLAN interface must be active for send()/recv()
        print('WiFi STA_IF   started')
        wifi = network.WLAN(network.STA_IF)
        wifi.active(True)
        local = wifi.config('mac')
        
        SMesh._nodes={node_name:bytearray(local)} # create list of MAC-address & there _nodes

        print('ESPNow node {} started'.format(node_name))
        SMesh.en = espnow.ESPNow()
        SMesh.en.init()
        SMesh.en.add_peer(_BCAST) # add broadcast peer first
        self.on_news = on_news if on_news else self._on_news
        SMesh.en.config(on_recv=self._listen)
            
        _pubsT = Timer(4) # pulse Pubs
        _pubsT.init(period=pub_t, mode=Timer.PERIODIC, callback=self._pubs_post) 
        
        print('SMesh network started')
        
        
    # empty News
    def _on_news(self,node_name,topic,order,data):
        return True
    
    
    # empty Log
    def _log(self,node_name,topic,order,data):
        return True
    
    
    @staticmethod
    def _check_peer(MAC):
        try:
            SMesh.en.add_peer(MAC)
        except OSError as err:
            if len(err.args) < 2:
                raise err
            elif err.args[1] == 'ESP_ERR_ESPNOW_EXIST':
                ...
            else:
                raise err


    # PACK Protocol
    @staticmethod
    def _pack_msg(topic,cmd):
        msg=SMesh._news[topic]
        CRC = 0
        return '{}~{}~{}~{}~{}~{}~{}~{}'.format(_PROTOCOL,msg.node_name,cmd,topic,msg.order,msg.payload,msg.QoS,CRC)


    # UnPACK Protocol
    @staticmethod
    def _unpack_msg(msg):

        _verboseA and print('unpack : ',msg)

        if msg[0] != _PROTOCOL:
            _verboseA and print('Warn:Wrong protocol: ',msg[0])
            return None
        
        post = MSG()
        post.node_name = msg[1]
        post.cmd       = msg[2]
        post.topic     = msg[3]
        post.order     = msg[4]
        post.payload   = msg[5]
        post.QoS       = msg[6]
        post.CRC       = msg[7] # check CRC (may be later)

        return post

    @staticmethod
    def _pubs_post(_): # post from queue
        for topic,cmd in SMesh._pub_que.items():

            delivered = SMesh.en.send(SMesh._news[topic].MAC,SMesh._pack_msg(topic,cmd),True) # place in que
 
            _verboseA and print('{} Sent: {} {} : {} ... and waiting for any msg'.format(SMesh.node_name,topic,SMesh._news[topic].order,SMesh._news[topic].payload))
            _verboseA and print()
           
            if delivered or SMesh.news[topic].QuE == 0:
                del SMesh._pub_que[topic] # update pub & drop out from que
            else:
                SMesh.news[topic].is_dup = True
                
            
    # main callback routine, analyse all received messages
    def _listen(self,en): # on receive callback
        while en.poll(): # collect all receives
            
            MAC, data = self.en.irecv(0)
            u_data = data.decode('utf-8')
            post = self._unpack_msg(u_data.split(_CH_SPLIT))
            if not post: return None # Bad protocol, here we can check protocol version by the way
        
            self._nodes[post.node_name]=bytearray(MAC) # keep MAP 0f net for the future
            
            if post.topic in self._news: # the node_name is alive!
                if post.cmd == 'NEW': # SUB: get new data
                    self._news[post.topic].t_stamp = ticks_ms() # zero expired time
                    if self._news[post.topic].QoS: # need approve to stop Publisher to send duplicates
                        self._news[post.topic].node_name = post.node_name # ws it's name
                        self._news[post.topic].MAC = bytearray(MAC)  # keep MAC for sending 'ACK' and 'CON'
                        self._check_peer(MAC)
                        self._pub_que[post.topic] = 'CON' # confirmation

                    self.on_news(post.node_name,post.topic,post.order,post.payload ) # if not in news list - just transparent transmission
                    
                elif self._news[post.topic].is_pub: # I'm PUBliser?
                    if post.cmd == 'ACK': # PUB: request from SUB, make peer if not public
                        if self._news[post.topic].QoS < post.QoS: self._news[post.topic].QoS = post.QoS  # rise QoS level
                        if self._news[post.topic].QoS:
                            self._news[post.topic].MAC = bytearray(MAC)  # keep MAC for sending 'ACK' and 'CON'
                            self._check_peer(MAC)
                        self._pub_que[post.topic] = 'NEW' # confirmation
                                            
                    elif post.cmd == 'CON': # PUB: CONfirmation from SUB that news been received for QoS=1
                        self._news[post.topic].is_dup = False
                        if post.topic in self._pub_que:
                            del self._pub_que[post.topic] # stop send duplicates
            else:
                self.on_news(post.node_name,post.topic,post.order,post.payload ) # if not in news list - just transparent transmission
                
                
    # peered link to Pub
    @classmethod
    def subs(cls,topic,QoS=0,expired=0):
        # topic    - head of News
        # QoS      - Quality of Service
        # response - waiting time for the news between tries, default : 0 sec - no Wait
        # expired  - time for 'fresh' News, default : 0 - don't worry about 'fresh' news
        
        if not topic in cls._news: # new sub
            post = NEWS()
            cls._news[topic]=post
            cls._news[topic].is_pub = False
        cls._news[topic].QoS     = QoS
        cls._news[topic].t_exp   = expired*1000
        cls._news[topic].t_stamp = ticks_ms() # zero expired time
      

    # SUBscriber search NEWS in SMesh Area
    @classmethod
    def request(cls,topic):
        # topic   - name
        #
        # return False if time expiried

        if not topic in cls._news: # new sub
            post = NEWS()
            cls._news[topic]=post
            cls._news[topic].is_pub = False
            cls._news[topic].t_stamp = ticks_ms() # zero expired time
        
        cls._pub_que[topic] = 'ACK'
            
        return True if ticks_diff(ticks_ms(), cls._news[topic].t_stamp) < cls._news[topic].t_exp else False


    # Post PUBlication or DUPlicate it
    @classmethod
    def post(cls,topic,payload):
        if not topic in cls._news: # new pub
            post = NEWS()
            cls._news[topic]=post
            cls._news[topic].node_name = cls.node_name
            
        if cls._news[topic].QoS == 2 and cls._news[topic].is_dup: # duplicate messages ws QoS == 2
            ... # wait 'CON' confirmation from subsctiber 
        else:
            cls._news[topic].order   = next(cls._new_pid)  # limit orders
            if payload: cls._news[topic].payload = payload # refresh news

        cls._news[topic].t_stamp = ticks_ms() # zero expired time

        cls._pub_que[topic] = 'NEW'
