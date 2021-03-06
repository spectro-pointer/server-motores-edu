#!/usr/bin/env python
# 22/05/2014 prueba que lee el estado de las entradas 26, 19, 15 y 10 para
# mover dos motores paso a paso con salidas de pulso y direccion para cada motor
# por 18, 7 para el motor de elevacion y 22, 24 para el de azimut.
# Si la entrada correspondiente esta a masa genera pulsos, de lo contrario deja
# la salida en cero. Las entradas se definen como pull-up por lo que
# solo necesitan un switch a masa sin ninguna resistencia.

# 07/03/2016 se implementa un servidor xml rpc para recibir comandos desde
# un cliente corriendo en otra RPI en red para hacer mover los motores

# 09/03/2016 se agrega que cada rpi (son 2) envie su nombre ademas de la orden y se agrega el bit 4
# como indicador de centrado (idem led amarillo). La rpi del telescopio buscador tiene la prioridad.
# Si se recibe la indicacion de que el buscador esta centrado, recien ahi se le da bola a las ordenes
# del colimador, si no se le da bola a las ordenes del buscador.

# 27/04/16 se agrega a la rutina genera_pulsos el chequeo de dos fines de carrera conectados a 2 entradas.
# Si se cierra alguno de los dos switch el motor no se mueve mas en ese sentido hasta que se abran nuevamente.

# 15/5/2016 se corrige secuencia de generacion de pulsos al motor paso a paso de azimut para que se establezca
# la senial direccion antes de la senial de pulso.

# 19/5/2016 se agrega encendido y apagado del puntero laser, motor zorrino y limpiador de optica.
# Tambien se agrega modo manual o automatico que se puede cambiar desde el panel de control web que se identifica como
# "Mant" para el servidor de motores como un cliente ademas de las camaras.

# 21/05/16 Se corrigen algunos errores en la secuencia de servidor xmlrpc.
# 23/05/2016 se responde diferente en modo manual a la interrogacion de Busca o Coli para que reintenten.
# 25/05/2016 se agrega contador de pulsos en azimut y elevacion para usarlo como modo de medicion de la posicion en el espacio.
# 28/05/2016 se cambia modo de imprimir los comandos recibidos desde los clientes y se agrega coordenadas al print de cada comando
# 29/05/2016 se arreglan varios errores encontrados por Gustavo.
# 06/06/2016 se hace un nuevo mapeo de pines -para el nuevo pcb
# 08/06/2016 se simplifica el seteo de pines de entrada y salida y de la ip de la placa.
# 17/06/2016 se corrige error en limites de carrera en elevacion durante el movimiento automatico.
# 29/06/2016 luego de verificar todos los cambios se unifica la rama coordenadas en master para dejarla como unica rama.
# 05/07/2016 se agrega modo de movimiento lento desde el panel de control para ayudar al apuntamiento manual

import RPi.GPIO as GPIO
import time
import threading
import xmlrpclib
from SimpleXMLRPCServer import SimpleXMLRPCServer

# Definicion de entradas y salidas de la placa:
# ---------------------------------------------
# Salidas:
PULSOS_AZI=40   # pulsos azimut
DIR_AZI=38      # direccion azimut
PULSOS_ELE=32   # pulsos elevacion
DIR_ELE=36      # direccion elevacion
LIMPIA=12       # limpia optica
ZORRO=16        # zorrino
LASER=18        # puntero laser

# Entradas:
PULAZDER=35     # pulsador azimut a la derecha
PULAZIZQ=37     # pulsador azimut a la izquierda
PULELEARR=31    # pulsador elevacion arriba
PULELEABA=33    # pulsador elevacion abajo
FINELEABA=26    # fin de carrera elevacion y cero del medidor de elevacion
FINELEARR=24    # fin de carrera elevacion
HOME=22         # cero del medidor de azimut


# Inicializa variables globales
pulsremazi=True
pulsremele=True
dirremazi=False
dirremele=False
medazi=0
medele=0        # inicializa medidores de azimut y elevacion
modo_lento=False

# Set local address
ip_address = '192.168.0.101'  # aca poner la IP correcta de esta RPI

#------------------------------------------------------
# esta funcion es un thread separado que genera pulsos para los motores de acuerdo
# a si se pulsa o no un boton manual y a las variables dirremazi, pulsremazi, dirremele
# y pulremele que genera la rutina set_motores en funcion de las ordenes de los clientes
# camara buscadora, camara colimadora o control manual.

def genera_pulsos():
    parado=False
    state=True
    dazi=1
    dele=1     # inicializa deltas para medidores de azimut y elevacion
    global medazi
    global medele

    try:
        while True: # do forever
#.....................................................................azimut
            if (not GPIO.input(HOME)):                                   # test cero del azimut
                medazi=0                                                 # pone a cero el contador de azimut

            if (not GPIO.input(PULAZDER)):                               # evalua direccion azimut
                GPIO.output(DIR_AZI, False)                              # gira para un lado fijado por el pulsador
                dazi=-1
            elif (not GPIO.input(PULAZIZQ)):
                GPIO.output(DIR_AZI, True)                               # o para el otro fijado por el otro pulsador
                dazi=1
            elif (not dirremazi):
                GPIO.output(DIR_AZI, False)                              # gira a la derecha por remoto
                dazi=-1
            else:
                GPIO.output(DIR_AZI, True)                               # gira a la izquierda por remoto
                dazi=1
            #........................................................ pulsos en azimut
            if(GPIO.input(PULAZDER) and GPIO.input(PULAZIZQ) and pulsremazi):   # si los dos switch abiertos
                GPIO.output(PULSOS_AZI, False)                           # la salida va a 0v (detenida)
            else:
                GPIO.output(PULSOS_AZI, state)                           # cualquiera de los dos switch genera pulsos en la salida
                medazi=medazi+dazi
#.................................................................... elevacion
            parado=False
            if (not GPIO.input(PULELEABA)):                              # Primero evalua direccion de movimiento y fines de carrera
                GPIO.output(DIR_ELE, True)                               # gira para arriba fijado por el pulsador
                dele=-1
                if (not GPIO.input(FINELEARR)):                          # test fin de carrera
                    parado=True                                          # piso fin de carrera, detiene el motor

            elif (not GPIO.input(PULELEARR)):
                GPIO.output(DIR_ELE, False)                              # o para abajo fijado por el otro pulsador
                dele=1
                if (not GPIO.input(FINELEABA)):
                    medele=0                                             # este fin de carrera es tanbien el cero del medidor de elevacion
                    parado=True                                          # piso fin de carrera, detiene el motor

            elif (not dirremele):
                GPIO.output(DIR_ELE, True)                               # gira para arriba por orden remota
                dele=-1
                if (not GPIO.input(FINELEARR)):
                    parado=True                                          # piso fin de carrera, detiene el motor
            else:
                GPIO.output(DIR_ELE, False)                              # gira para abajo por orden remota
                dele=1
                if (not GPIO.input(FINELEABA)):
                    parado=True                                          # piso fin de carrera, detiene el motor
                    medele=0
            #----------------------------
            if(GPIO.input(PULELEARR) and GPIO.input(PULELEABA) and pulsremele):   # si los dos switch abiertos
                GPIO.output(PULSOS_ELE, False)                           # la salida va a 0v
            else:
                if (not parado):                                         # si se piso algun fin de carrera no mueve elevacion
                    GPIO.output(PULSOS_ELE, state)                       # cualquiera de los dos switch genera pulsos en la salida
                    medele=medele+dele
            #----------------------------
            state = not state
            if not modo_lento:  #entrada 8 cerrada a masa para alta velocidad
                time.sleep(0.005)  # 0.001 con 1600 pulsos por vuelta funciona bien hasta 0.0001 , o sea 100 useg funciona
            else:
                time.sleep(0.05)
    except KeyboardInterrupt:
        GPIO.cleanup()
#       exit
#-------------------------------------------------
# SERVIDOR:
# Definimos la funcion que va a atender los llamados desde el cliente para saber si mueve el motor.
# Cada cliente envia la orden y el nombre del cliente, "Busca" para la camara buscadora, "Coli" para
# la camara colimadora y "Mant" para el panel de mantenimiento (pagina web).
# En el parametro orden viene el valor que dice si se mueve o no y en que direccion:
# Ordenes de las camaras (Busca, Coli):
# ----------------------
# orden=0 => todo detenido
# orden=1 => gira + en azimut
# orden=3 => gira - en azimut
# orden=4 => gira + en elevaciion
# orden=12 => gira - en elevacion
# orden=16 => blanco centrado
# Ordenes del panel de control manual (Mant):
# ------------------------------------------
# orden=16 => pasa a modo manual, no mueve mas los motores a pedido de las camaras
# Si esta en modo manual:
# ----------------------
# orden=16 => pasa a modo automatico, mueve mas los motores a pedido de las camaras
# orden=0 => motores detenidos, zorrino, limpiador y laser apagados
# orden=1 => gira + en azimut
# orden=3 => gira - en azimut
# orden=4 => gira + en elevaciion
# orden=12 => gira - en elevacion
# orden=32 => enciende limpia optica
# orden=64 => enciende zorrino
# orden=128 => enciende puntero laser
# orden=224 => apaga las 3 salidas de servicio
# orden=96 on/off modo lento

def set_motores(orden,origen):
    global pulsremazi
    global pulsremele
    global dirremazi
    global dirremele
    global medazi
    global medele
    global modo_lento

    if set_motores.manual==True:
        modo="modo manual"
        if origen<>"Mant":              # esta en modo manual, se controla desde panel de control web
            accion="No hace nada"
            # print modo, origen, orden, accion, medazi, medele
            return 2                    # en modo manual descarta ordenes del buscador y colimador
        else:
            if orden==32:               # orden limpia optica
                GPIO.output(LIMPIA, True)   # lo enciende
                accion="Enciende limpiador"

            elif orden==64:             # orden zorrino
                GPIO.output(ZORRO, True)   # lo enciende
                accion="Enciende zorrino"

            elif orden==128:            # orden puntero laser
                GPIO.output(LASER, True)   # lo enciende
                accion="Enciende laser"

            elif (orden & 3)==3:
                pulsremazi=False        # mueve azimut
                dirremazi=False         # define direccion azimut
                accion="mueve azimut +"

            elif (orden & 1)==1:
                pulsremazi=False        # mueve azimut
                dirremazi=True          # define direccion azimut
                accion="mueve azimut -"

            elif (orden & 12)==12:      #define pulsos en elevacion
                dirremele=False
                pulsremele=False        # mueve elevacion
                accion="mueve elevacion -"

            elif (orden & 4)==4:        # define direccion elevacion
                dirremele=True
                pulsremele=False        # mueve elevacion
                accion="mueve elevacion +"

            elif orden==16:
                set_motores.manual=False # Pasa a modo automatico
                accion="pasa a modo automatico"

            elif orden==224:            #apaga las 3 salidas
                GPIO.output(LIMPIA, False)  # apaga limpia optica
                GPIO.output(ZORRO, False)  # apaga zorrino
                GPIO.output(LASER, False)  # apaga puntero laser
                accion="Apaga las 3 salidas"

            elif orden==96:
                modo_lento= not modo_lento
                accion="cambia velocidad"
            
            if orden==0:                # test modo automatico
                pulsremazi=True         # detiene los motores
                pulsremele=True
                accion="Detiene los motores"

        print modo, origen, orden, accion, medazi, medele
        return 1
#........................................
    else:                               # esta en modo automatico, las camaras mueven los motores
        modo="modo automatico"
        if origen=="Mant":              # Analiza si llego mensaje del panel de control para pasar a manual
            if (orden & 16)==16:        # mensaje del panel de control, pasa a manual
                set_motores.manual=True
                accion="pasa a modo manual"
                pulsremazi=True         # detiene los motores
                pulsremele=True
                print modo, origen, orden, accion, medazi, medele
                return 1
            else:
                accion="No hace nada"
                print modo, origen, orden, accion, medazi, medele
                return 1                # Cualquier orden del panel de control que no sea pasar a manual
                                        # estando en modo automatico, la descarta.
        elif origen=="Busca":           # Analiza si llego mensaje del buscador y si esta centrado
            if (orden & 16)==16:        # mensaje del buscador, ve si esta centrado
                cent="Centrado"
                set_motores.centrado=True
            else:
                cent="No centr"
                set_motores.centrado=False
        else:
            if (orden & 16)==16:        # mensaje del colimador, ve si esta centrado
                cent="Centrado"
            else:
                cent="No centr"

            if set_motores.centrado==False:  # mensaje del colimador, si buscador "No centrado", no da bola
                accion="No da bola"
                print modo, origen, orden, accion, cent, medazi, medele  # imprime que orden recibio y de que maquina
                return 1

#...........................................movimientos del motor
        if (orden & 15)==0:
            pulsremazi=True
            pulsremele=True
            dirremazi=False
            dirremele=False
            accion="Detenida"
        else:
#..............................define direccion azimut
            if (orden & 2)==2:
                dirremazi=False #True
            else:
                dirremazi=True #False

                          #define pulsos en azimut
            if (orden & 1)==1:
                pulsremazi=False  # mueve azimut
                if dirremazi==True:
                    accion="azimut +"
                else:
                    accion="azimut -"
            else:
                pulsremazi=True   # azimut detenido
#..............................define direccion elevacion
            if (orden & 8)==8:
                dirremele=False
            else:
                dirremele=True
                          #define pulsos en elevacion
            if (orden & 4)==4:
                pulsremele=False  # mueve elevacion
                if dirremele==False:
                    accion="elevacion +"
                else:
                    accion="elevacion -"
            else:
                pulsremele=True   #elevacion detenida
#..................................
        print modo, origen, orden, accion, cent, medazi, medele  #imprime que orden recibio y de que maquina
        return 1        # devuelve un 1 porque algo hay que devolver, sino da error, pero ese 1 no significa nada.
#------------------------------------------------------------------
# Main
# Recordatorio de la funcion de cada pin en pantalla
print "Entrada Pin 35 Sube Azimut"
print "Entrada Pin 37 Baja Azimut"
print "Entrada Pin 31 Sube Elevacion"
print "Entrada Pin 33 Baja Elevacion"
print "Entradas 24 y 26 fines de carrera elevacion"
print "Ctrl C para terminar"
set_motores.centrado=False
#el control de motores arranca en modo manual, o sea responde al comando
# del panel de control webs.
set_motores.manual=True

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)            #selecciona numero de pines del conector
GPIO.setup(PULSOS_AZI, GPIO.OUT)    #define pin salida  pulsos azimut
GPIO.setup(DIR_AZI, GPIO.OUT)       #define pin salida direccion azimut
GPIO.setup(PULSOS_ELE, GPIO.OUT)    #define pin salida  pulsos elevacion
GPIO.setup(DIR_ELE, GPIO.OUT)       #define pin direccion elevacion
GPIO.setup(LIMPIA, GPIO.OUT)        #define pin salida  limpia optica
GPIO.setup(ZORRO, GPIO.OUT)         #define pin salida  zorrino
GPIO.setup(LASER, GPIO.OUT)         #define pin salida  puntero laser

# define entradas con resistencia de pull up
GPIO.setup(PULAZDER,GPIO.IN, pull_up_down=GPIO.PUD_UP)      # pulsador azimut
GPIO.setup(PULAZIZQ,GPIO.IN, pull_up_down=GPIO.PUD_UP)      # pulsador azimut
GPIO.setup(PULELEARR,GPIO.IN, pull_up_down=GPIO.PUD_UP)     # pulsador elevacion
GPIO.setup(PULELEABA,GPIO.IN, pull_up_down=GPIO.PUD_UP)     # pulsador elevacion
GPIO.setup(FINELEABA,GPIO.IN, pull_up_down=GPIO.PUD_UP)     # fin de carrera elevacion y cero del medidor de elevacion
GPIO.setup(FINELEARR,GPIO.IN, pull_up_down=GPIO.PUD_UP)     # fin de carrera elevacion
GPIO.setup(HOME,GPIO.IN, pull_up_down=GPIO.PUD_UP)          # cero del medidor de azimut

#Definimos el thread y lo lanzamos
threadObj = threading.Thread(target=genera_pulsos)
threadObj.setDaemon(True)
threadObj.start()

# Abrimos el servidor para que acepte peticiones.
server = SimpleXMLRPCServer((ip_address, 8000)) 
print "Listening on port 8000..."                    # se queda escuchando a clientes en el puerto 8000

# Registramos la funcion que hemos definido.
server.register_function(set_motores, "set_motores")
server.serve_forever()
#end of main loop
