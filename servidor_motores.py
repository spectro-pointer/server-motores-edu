
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

import RPi.GPIO as GPIO
import time
import threading
import xmlrpclib
from SimpleXMLRPCServer import SimpleXMLRPCServer

# Inicializa variables globales
pulsremazi=True
pulsremele=True
dirremazi=False
dirremele=False

# esta es una modificacion el 14/05/2016

#------------------------------------------------------
# esta funcion es un thread separado que genera pulsos para los motores de acuerdo
# a la variable pulsrem

def genera_pulsos():
	parado=False
	state=True
	try:
		while True: # do forever
		#.......................azimut
			if(GPIO.input(11) and GPIO.input(12) and pulsremazi):  # si los dos switch abiertos
		        	GPIO.output(40, False)  # la salida va a 0v
		      	else:
		          	GPIO.output(40, state)  #cualquiera de los dos switch genera pulsos en la salida
		       #...............direccion azimut
			if (not GPIO.input(12)):
    				GPIO.output(38, False)  # gira para un lado fijado por el pulsador

			elif (not GPIO.input(11)):
    				GPIO.output(38, True)   # o para el otro fijado por el otro pulsador

			elif (not dirremazi):
    				GPIO.output(38, False)  #gira a la derecha por remoto
			else:
    				GPIO.output(38, True)   #gira a la izquierda por remoto

		#........................elevacion
                        parado=False
			if (not GPIO.input(29)):       # Primero evalua direccion de movimiento y fines de carrera
    				GPIO.output(36, True)  # gira para arriba fijado por el pulsador
			        if (not GPIO.input(15)):
				   parado=True		#piso fin de carrera, detiene el motor

			elif (not GPIO.input(18)):
    				GPIO.output(36, False) # o para abajo fijado por el otro pulsador
			        if (not GPIO.input(13)):
				   parado=True		#piso fin de carrera, detiene el motor

			elif (not dirremele):
    				GPIO.output(36, True)  # gira para arriba por orden remota
			        if (not GPIO.input(15)):
				   parado=True		#piso fin de carrera, detiene el motor
			else:
    				GPIO.output(36, False) # gira para abajo por orden remota
			        if (not GPIO.input(13)):
				   parado=True		#piso fin de carrera, detiene el motor
			#----------------------------
		      	if(GPIO.input(18) and GPIO.input(29) and pulsremele):  # si los dos switch abiertos
		               	GPIO.output(37, False)  # la salida va a 0v
		      	else:
				if (not parado):	#si se piso algun fin de carrera no mueve elevacion
					GPIO.output(37, state)  #cualquiera de los dos switch genera pulsos en la salida
                       #----------------------------
			state = not state
		        #if (GPIO.input(8)):  #entrada 8 cerrada a masa para alta velocidad
			time.sleep(0.005)  # 0.001 con 1600 pulsos por vuelta funciona bien hasta 0.0001 , o sea 100 useg funciona

	except KeyboardInterrupt:
		GPIO.cleanup()
#		exit
#-------------------------------------------------
# SERVIDOR:
# Definimos la funcion que va a atender los llamados desde el cliente para saber si mueve el motor.
# Cada cliente envia la orden y el nombre del cliente, "Busca" y "Coli" por ejemplo, en el parametro
# orden viene el valor que dice si se mueve o no y en que direccion
# orden=0 => todo detenido
# orden=1 => gira + en azimut
# orden=3 => gira - en azimut
# orden=4 => gira + en elevaciion
# orden=12 => gira - en elevacion
# orden=16 => blanco centrado

def set_motores(orden,origen):
	""" Funcion que recibe mensajes desde los clientes y mueve
	los motores de azimut y elevacion en consecuencia """
	global pulsremazi
	global pulsremele
	global dirremazi
	global dirremele


# Analiza si llego mensaje del buscador y si esta centrado
	if origen=="Busca":
		if (orden & 16)==16:    #mensaje del buscador, ve si esta centrado
			cent="Centrado"
			set_motores.centrado=True
		else:
			cent="No centr"
			set_motores.centrado=False
	else:
		accion="No da bola"
		if (orden & 16)==16:    #mensaje del buscador, ve si esta centrado
			cent="Centrado"
		else:
			cent="No centr"
                if set_motores.centrado==False:  #mensaje del colimador, si buscador "No centrado", no da bola
		        print origen, orden, cent, accion  #imprime que orden recibio y de que maquina
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
			dirremazi=True
		else:
			dirremazi=False

					  #define pulsos en azimut
		if (orden & 1)==1:
			pulsremazi=False  # mueve azimut
			if dirremazi==True:
				accion="azimut +"
			else:
				accion="azimut -"
		else:
			pulsremazi=True   # azimut detenido
#..............................define direccion azimut
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
			pulsremele=True	  #elevacion detenida
#..................................
        print origen, orden, cent, accion  #imprime que orden recibio y de que maquina
        return 1		# devuelve un 1 porque algo hay que devolver, sino da error, pero ese 1 no significa nada.
#------------------------------------------------------------------
# Recordatorio de la funcion de cada pin en pantalla
print "Entrada Pin 11 Sube Azimut"
print "Entrada Pin 12 Baja Azimut"
print "Entrada Pin 18 Sube Elevacion"
print "Entrada Pin 29 Baja Elevacion"
print "Entrada Pin 8 Cambia la velocidad"
print "Ctrl C para terminar"
set_motores.centrado=False

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)  #selecciona numero de pines del conector
GPIO.setup(40, GPIO.OUT)  #define pin 40 como salida
GPIO.setup(38, GPIO.OUT)   #define pin 38 como salida
GPIO.setup(37, GPIO.OUT)  #define pin 37 como salida
GPIO.setup(36, GPIO.OUT)  #define pin 36 como salida

# define entradas 11, 12, 18 ,29,8, 13 y 15 con resistencia de pull up
GPIO.setup(11,GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(12,GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(18,GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(29,GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(8,GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(13,GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(15,GPIO.IN, pull_up_down=GPIO.PUD_UP)

#Definimos el thread y lo lanzamos
threadObj = threading.Thread(target=genera_pulsos)
threadObj.setDaemon(True)
threadObj.start()

# Abrimos el servidor para que acepte peticiones.
server = SimpleXMLRPCServer(("192.168.0.101", 8000)) # aca poner la IP correcta de esta RPI
print "Listening on port 8000..."                    # se queda escuchando a clientes en el puerto 8000

# Registramos la funcion que hemos definido.
server.register_function(set_motores, "set_motores")
server.serve_forever()
#end of main loop
