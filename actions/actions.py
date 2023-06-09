import csv, importlib, json, os, typing
from pickle import NONE
import datetime as dt
import xml.etree.cElementTree as ET
import numpy as np

from EBDI.emotions_manager import emotions_manager
from EBDI.belief_manager import belief_manager
from EBDI.desires_manager import desires_manager
from EBDI.intents_manager import intents_manager 

from DDBB.SQL import database 

from os import listdir
from typing import Any, Text, Dict, List

from rasa_sdk import events
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, BotUttered, UserUttered, EventType

from rasa.shared.nlu.training_data.loading import load_data

if typing.TYPE_CHECKING:
    from rasa_sdk.trackers import DialogueStateTracker
    from rasa_sdk.dispatcher import Dispatcher
    from rasa_sdk.domain import Domain

# Variables globales
user_intent = ''
count = 0
Bi = ''
Be = ''
lang = 'es-ES'
polarity = 0
avatar = 'f'
inter1 = False

## Kinect
watch = False
watchResponse = ''

## Interface
interface = False
interfaceResponse = ''

## Database
routine_say = False
exercises = []

# Gestor EBDI
Emotions = emotions_manager()
Beliefs = belief_manager()
Desires = desires_manager()        
Intents = intents_manager()
context = Intents.get_context()

# DDBB
db = database()
db.connection()

# Memoria del Bot
slot_name = ''
slot_daytime = ''
slot_rol = ''
slot_avatar = ''
id_user = 0

# Methods
def __init__(self):
    self.agent_id = 'actions'

# Number of responses
def contador():    
    global count
    count = count + 1
    return []

# Last event that has been generated to capture the response that has been selected from the Domain file
def get_latest_event(events):    
    latest_actions = []
    for e in events:
        if e['event'] == 'bot':
            latest_actions.append(e)
    return latest_actions

# Time of day
def part_of_day(x):    
    if (x > 4) and (x <= 12 ):
        return 'morning'
    elif (x > 12) and (x <= 16):
        return'afternoon'
    elif (x > 16) and (x <= 24) :
        return 'evening'
    elif (x > 24) and (x <= 4):
        return'none'

# The day in spanish
def the_day(x):
    if x == "Monday":
        return 'lunes'
    if x == "Tuesday":
        return 'martes'
    if x == "Wednesday":
        return 'miercoles'
    if x == "Thursday":
        return 'jueves'
    if x == "Friday":
        return 'viernes'
    if x == "Saturday":
        return 'sabado'
    if x == "Sunday":
        return 'domingo'

## Estructura BOT
class ChatBot(Action):
    def name(self) -> Text:
        return "chatbot"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]: 
        # Acceso a variables globales
        global Bi
        global Be
        global lang
        global polarity
        global avatar
        global inter1
        global slot_name
        global slot_daytime
        global slot_rol
        global slot_avatar
        global id_user
        global db

        print("--------------------------------------------------------------------------------------------")

        inter1 = True
        ## Valores de entrada, si es un texto
        intent = tracker.latest_message['intent']
        text = tracker.latest_message['text']
        entities = tracker.latest_message['entities']
        metadata = tracker.latest_message['metadata']
        ## Slots
        ## Almacenado en memoria
        slot_name = tracker.get_slot('name')   
        slot_avatar = tracker.get_slot('avatar')   
        slot_rol = tracker.get_slot('rol')   
       
        Bi = intent['name']
        id_event = metadata['event']

        slot_daytime = part_of_day(int(f"{dt.datetime.now().strftime('%H')}"))          

        # Metadatas received
        for key, value in metadata.items():
            print(key, value)
            if 'id' in metadata:
                id_user = metadata['id'] 
                contenido = db.login(id_user)
                slot_name = contenido['name']                 
                slot_rol = contenido['rol']                 

        # Entities received
        for e in entities:
            print("entidad: {} = {}".format(e['entity'],e['value']))
            if e['entity'] == 'avatar':
                avatarVoice = e['value']
                if avatarVoice == 'Sonia':
                    avatar = 'f'
                else:
                    avatar = 'm'

        ## Voice input     
        if (id_event == 'say'):
            if 'emotion' in metadata:
                Be = metadata['emotion']            
            if 'language' in metadata:
                lang = metadata['language']
            if 'polarity' in metadata:
                polarity = metadata['polarity']            
            if Bi not in context:
                Bi = 'out_of_scope'
            user_event = [id_event,Bi,Be,text,slot_name,entities,lang,polarity] 
            print('EVENT: ' + str(user_event))
            EBDI.run(self, dispatcher, tracker, domain, user_event)                
                
        ## Entradas de conocimiento
        elif (id_event == 'know'):
            objInterest = None                    
            user_event = [id_event,text,objInterest,'']             
            print('EVENT: ' + str(user_event)) 
            if text in context:
                EBDI.run(self, dispatcher, tracker, domain, user_event)
            else:
                print('No se que hacer con este conocimiento.')
                
        ## Entrada de acciones a realizar
        elif (id_event == 'do'):
            print('Ahora lo hago')
        else:
            print('Comando no conocido')            

        ## comprobacion del diccionario de sinonimos de entidades
        synonyms_dict = Dictionary.get_synonym_mapper()
        for value, synonyms in synonyms_dict.items():
            ## print("Value:", value)
            ## print("Synonyms:", str(synonyms))
            Ricardo_synonyms = synonyms      
        
        return [SlotSet("daytime", slot_daytime),SlotSet("rol", slot_rol)]

## Estructura EBDI
class EBDI(Action):

    def name(self) -> Text:
        return "ebdi"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any],
            user_event) -> List[Dict[Text, Any]]:          
        ## Conjunto E B D I
        global Emotions
        global Beliefs
        global Desires
        global Intents 
        global inter1

        Beliefs.inter = inter1
        inter1 = False
        print(Beliefs.inter)
        # Establecen las nuevas creencias a partir del evento
        newBelief = Beliefs.new_belief(user_event)     
        
        Beliefs.del_belief(Emotions.estado)
        for e in Beliefs.emotionalBeliefs:
            Beliefs.del_belief(e)
        # Primera gestion del estado emocional
        E1 = Emotions.euf1(Intents,newBelief)
        print('PRIMARY EMOTION: ' + E1) 
        
        newBelief.append(['know',E1,True])        

        # BDI actualizacion        
        BDI.bdi(self,newBelief)             

        # Segunda gestion del estado emocional
        E2 = Emotions.euf2(Intents,Beliefs)
        print('SECONDARY EMOTION: ' + E2) 

        #if (inTime and E1 != E2):
        #   BDI.bdi(self,Beliefs.agent_beliefs)

        print('ACTIONS:') 
        p = Plan.plan(self, Intents.agent_intents)  
        if Intents.agent_intents:
            del Intents.agent_intents[0]
            
        for i in p:
            print('--->' + i)
            exec(i) 

        return []

# actualizacion Beliefs Desires Intents
class BDI:

    def bdi(self,newBelief):     
        ## Conjunto E B D I
        global Emotions
        global Beliefs
        global Desires
        global Intents 

        #B = brf_in(E,I,Bm) # se actualizan las creencias
        Beliefs.brf_in(Emotions,Intents,newBelief)
        print('BELIEFS:')
        for belief in Beliefs.agent_beliefs:
            print(" -", belief[0], belief[1], belief[2])

        #D = options(B,I) # se crean los deseos
        Desires.options(Beliefs,Intents)
        print('DESIRES:')
        for desire in Desires.agent_desires:
            print(" -", desire[0], desire[1], desire[2])     

        #I = filterI(E,B,D,I)
        Intents.filterI(Emotions,Beliefs,Desires.agent_desires)
        print('INTENTS:')
        for intent in Intents.agent_intents:
            print(" -", intent)

        # se estan manteniendo deseos, asi que esta linea los elimina, pero... ¿se pueden mantener deseos?
        Desires.agent_desires = [] 

        return []

class Plan:

    def plan(self, Intents):
        p = []    
        for intent in Intents:
            for idx, val in enumerate(intent):    
                # Seleccionamos la primera intencion y las acciones correspondientes        
                if val == 'a_say':  
                    resp = intent[idx+1]
                    s = "Say.run(self, dispatcher, tracker, domain,'{0}')".format(str(resp))
                    p.append((s))

                if val == 'a_nB':
                    user_event = ['say',intent[idx+1],'none','','','','']   
                    s = "EBDI.run(self, dispatcher, tracker, domain,{0})".format(user_event)
                    p.append((s))

                if val == 'a_dB':
                    s = "Beliefs.del_belief('{0}')".format(str(intent[idx+1]))
                    p.append(s)

                if val == 'a_fB':
                    s = "Beliefs.fulfill_belief('{0}')".format(str(intent[idx+1]))
                    p.append(s)

                if val == 'a_rB':
                    s = "Beliefs.reset_beliefs()"
                    p.append(s)

                # solicitud de camara
                if val == 'ki':
                    s = "Kinect.name('{0}')".format(str(intent[idx+1]))
                    p.append(s)
                # solicitud de interfaz
                if val == 'in':
                    s = "Interface.name('{0}')".format(str(intent[idx+1]))
                    p.append(s)
                # solicitud de base de datos
                if val == 'db':
                    s = "Database.name('{0}')".format(str(intent[idx+1]))
                    p.append(s)
        return p

## Acciones ##
class Say(Action):

    def name(self) -> Text:
        return "say"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any],
            resp) -> List[Dict[Text, Any]]:

        hours = str(f"{dt.datetime.now().strftime('%H:%M')}")
        day = the_day(str(f"{dt.datetime.now().strftime('%A')}"))

        dispatcher.utter_message(
            response = resp,           
            hours = hours,
            day = day,
            daytime = slot_daytime,
            name = slot_name,
            rol = slot_rol)

        contador()
        print("dispatcher: " + str(count))   
        tracker.get_slot('daytime')
        tracker.get_slot('rol')

        return []

## Generar los ficheros de salida
class To_Speech(Action):

    def name(self) -> Text:
        return "to_speech"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]
            ) -> List[Dict[Text, Any]]:
        global msg
        global count   
        global Emotions        

        print('----RESPONSES----')  
        tracker.get_slot('daytime') 
        tracker.get_slot('rol') 

        if count > 0:
            msg = get_latest_event(tracker.applied_events())        
            #print(json.dumps(msg[-count:], indent=4))
            responses = msg[-count:]  
            CSV().name(responses) 
        count = 0

        return []

class Kinect():
    def name(response):
        global watch
        global watchResponse
        watch = True
        watchResponse = response
        return "echo"

class Interface():
    def name(response):
        global interface
        global interfaceResponse
        interface = True
        interfaceResponse = response
        return "echo"

class Database():
    def name (response):
        global id_user
        global slot_name
        global slot_rol        
        if response == "login":
            contenido_user = getattr(db, response)(id_user)
            if contenido_user is not None:
                slot_name = contenido_user['name']
                slot_rol = contenido_user['rol']
        if response == "select_routine" :
            id_user = 101
            date = "2023-06-22"
            contenido_user = getattr(db, response)(id_user,date)
            if contenido_user is not None: 
                Database.routine(contenido_user)
            else:
                print("No hay datos para esta fecha")
        return "echo"

    def routine(contenido_user):
        global routine_say
        global exercises
        exercises = []
        routine_say = True        
        print(contenido_user)       
        e = contenido_user['ejercicios']
        e_array = [int(x) for x in e.split(",")]
        r = contenido_user['repeticiones']        
        r_array = [int(x) for x in r.split(",")]
        t = contenido_user['tiempos']        
        t_array = [int(x) for x in t.split(",")]
        select_exercise = "select_exercise"
        for i in range(len(e_array)):                   
            e_name = getattr(db, select_exercise)(e_array[i])
            if r_array[i] != 1:
                new_string = "{} con {} repeticiones de {} segundos.".format(
                e_name['name'],r_array[i],t_array[i])
            else:
                new_string = "{} con {} repetición de {} segundos.".format(
                e_name['name'],r_array[i],t_array[i])
            exercises.append(new_string)
        
## Salida de las respuestas csv
class CSV():
    def name(self,responses):
        global watch, watchResponse
        global interface, interfaceResponse
        global routine_say, exercises
        output_csv = open('speech.csv','w+',newline='')
        writer = csv.writer(output_csv, delimiter =',')
        writer.writerow(['action','response','emotion','language','animation','emotionAzure','video','length','avatar'])
        animation_tag = 'informar'  
        video = ''  
        length = 0
        for response in responses:
            if 'metadata' in response['metadata']:
                if 'subtext' in response['metadata']['metadata']:
                    animation_tag = str(response['metadata']['metadata']['subtext'])
                else:
                    animation_tag = 'informar'
                if 'img' in response['metadata']['metadata']:
                    video = str(response['metadata']['metadata']['img'])
                else:
                    video = ''
                if 'length' in response['metadata']['metadata']:
                    length = float(response['metadata']['metadata']['length'])
                else:
                    length = 0
            print(' -' + str(response['text']))
            writer.writerow(['say',str(response['text']), str(Emotions.estado),lang,animation_tag,str(Emotions.tag()),str(video),length,avatar])
        if(watch):
            writer.writerow(['watch',str(watchResponse)])
            watch = False
        elif(interface):
            writer.writerow(['interface',str(interfaceResponse)])
            interface = False
        elif(routine_say):
            for exercise in exercises:
                writer.writerow(['say',str(exercise), str(Emotions.estado),lang,animation_tag,str(Emotions.tag()),str(video),length,avatar])
            routine_say = False
        else:
            writer.writerow(['listen'])
        output_csv.close()

## Se ejecuta una sola vez al principio de una conversacion
class Dictionary:

    def get_synonym_mapper():
        result_dict = {}
        for nlu_md in os.listdir("data"):
            if nlu_md == 'nlu.md':
                path_md = "data/{0}".format(nlu_md)
                nlu_md_file = load_data(path_md)
                nlu_md_json = nlu_md_file.nlu_as_json()
                for item in json.loads(nlu_md_json)['rasa_nlu_data']['entity_synonyms']:
                    result_dict[item['value']] = item['synonyms']
        return result_dict


class You_are(Action):
    def name(self) -> Text:
        return "you_are"
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:        
        entities = tracker.latest_message['entities']
        slot_name = tracker.get_slot('name')
        print(entities)

        message = "Hola, encantado de conocerte!"

        for e in entities:
            if e['entity'] == 'name':
                name = e['value']
            if name == "ricardo":
                message = "Hey " + slot_name + ", que tal?"                
            if name == "amalia":
                message = "Hola Amalia, yo soy el sargento David Robertson, encantado"
        tag = "cheerful" 
        xml = XML()
        XML.name(xml,message,tag)
        dispatcher.utter_message(text=message)
        return []

class Info_fecha(Action):

    def name(self) -> Text:
        return "info_fecha"
    def run (self, dispatcher: CollectingDispatcher,
             tracker: Tracker,
             domain: Dict[Text,Any]) -> List[Dict[Text, Any]]:        
        entities = tracker.latest_message['entities']
        message = 'Lo siento, no he encontrado nada relacionado con esa fecha'
        for e in entities:
            if e['entity'] == 'fecha':
                fecha = e['value']
                if fecha == '1350':
                    message = "Antoine de le Puy, peregrino a santiago y alcanza a oir el sonido de una campana entre la niebla mientras desciende de la montania"
                if fecha == '1813':
                    message = "Tengo informacion sobre unos soldados que durante la guerra de independencia Española se encargaban de vigilar la frontera con Francia"
        dispatcher.utter_message(text=message)
        return []

class Buscar_informacion(Action):

    def name(self) -> Text:
        return "buscar_informacion"
    def run (self, dispatcher: CollectingDispatcher,
             tracker: Tracker,
             domain: Dict[Text,Any]) -> List[Dict[Text, Any]]:  
        print("Accediendo a informacion...")
        """ acceder a slot values, ahi se encuentra la fecha """
        slot_fecha = tracker.get_slot('fecha')
        print(slot_fecha)
        message = 'Error, informacion NO localizada'
        if slot_fecha == '1350':
            message = "Escuchad companieros el sonido de la campana! Roncesvalles ya esta al alcance y podremos..."
        if slot_fecha == '1813':
            message = "...A principios de octubre la nieve cayo en tal cantidad como no habia visto en Escocia. Casi perdimos..."
        dispatcher.utter_message(text=message)
        return []

class Aprendizaje(Action):

    def name(self) -> Text:
        return "aprendizaje"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:        
        entities = tracker.latest_message['entities']
        intent = tracker.latest_message['intent']
        text = tracker.latest_message['text']
        print(intent)
        print(entities)        
        print(text)
        message = "Comando de aprendizaje"
        dispatcher.utter_message(text=message)
        for e in entities:
            if e['entity'] == 'name':
                name = e['value']
            if name == "ricardo":
                message = "Hola Ricardo, estoy listo para aprender"
                '''a = tracker.'''
            if name != "ricardo":
                message = "Lo siento, no estas autorizado"     
        dispatcher.utter_message(text=message)
        return []
