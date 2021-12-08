# SMesh_Tests.py - tests Smart Mesh
#
# In main just change Module name for each Node Module

from utime import sleep

from smesh import SMesh

#=============================================================================================== TEST BLOCK

#=============================================================================================== MONITOR node_name
def view_M( node_name, order, topic, info ):
    print('{} node send {} {}: {}'.format(node_name, topic, order,  info))
    return True
    
    
def module_M(): # Montor : just Subscriber, show all published news

    SMesh( 'M', view_M )   

    SMesh.subs('temp',QoS=1,expired=5)

    while True:
        
        if not SMesh.request('temp'):
            print('                     connection ws topic "temp" been lost')

        sleep(1)

        
#=============================================================================================== SENSORS node_name
def module_S(): # Sensors : just Publisher, post sensors data

    SMesh('S')
    
    temp = 20
    hum = 60
    # main loop
    while True:
        temp = (1 + temp)%999
        SMesh.post('temp',temp)

        hum = (0.7 + hum)%99
        SMesh.post('hum', hum)

        print('Published temp {} and hum {}'.format(temp,hum))
        sleep(2)

        
#=============================================================================================== CONTROL node_name
def news_E( node_name, topic, order,  info ): # Execs : get limits and commands, post Alarm
    if topic == 'alarm':
        print('alarm from ',node_name,info)
    elif topic == 't_min':
        print('t_min',info)
    elif topic == 't_max':
        print('t_max',info)
    elif topic == 'light':
        print('light',info)
    elif topic == 'relay_1':
        print('light',info)
    elif topic == 'relay_2':
        print('light',info)
    return True


def module_E(): # control

    SMesh( 'E', news_E )
    
#    SMesh.subs('alarm',QoS=2,expire=10)        
#    SMesh.subs('t_min',QoS=2,expire=5)
#    SMesh.subs('t_max',QoS=2,expire=5)
        
#    SMesh.subs('light')

    alarm = True
    t_alarm = 0
    # main loop
    while True:    
        t_alarm = (t_alarm+1)%2
        if not t_alarm :
            SMesh.post('alarm',alarm)
            print('Daemon send alarm {}'.format(alarm))
        sleep(3)


#=============================================================================================== VISION node_name
def news_V( node_name, topic, info):
    if topic == 'alarm':
        print('alarm from ',node_name,info)
    elif topic == 'temp':
        print('temp',info)
    elif topic == 'hum':
        print('hum ',info)
    return True


t_min = 0
t_max = 10.1
light = True
    
def module_V(): # visualisation !!! DRAFT !!!
    SMesh('V',news_V) 

    SMesh.subs('alarm')
    SMesh.subs('hum')
    SMesh.subs('temp')

    while True:

        if SMesh.request('alarm', QoS=1): print('No News from "panic"')
        else: print('Subscribed to ALARM')
        
        if SMesh.request('temp',wait=3):  print('No News from "temp"')
        
        SMesh.request('hum',wait=0,expired=10)

        t_min = (1 + t_min)%999
        SMesh.post('min_temp',t_min,t_pub=5,t_dub=1)
        
        t_max = (1.1 + t_max)%99
        SMesh.post('max_temp',t_max)
        
        light = not light
        SMesh.post('light',light,t_pub=2)
        sleep(1)

################################ LOCAL MAIN node_name

print('--- NODE ACTIVATED ---')
module_M()

print('Finished')
