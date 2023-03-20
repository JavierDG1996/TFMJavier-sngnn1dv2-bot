import logging
import pickle
import random
import time
import sys, os
import threading
import telegram
import re
from telegram import Update
import numpy as np
import requests
from telegram.ext import CommandHandler, Filters, MessageHandler, Updater, CallbackContext
from ibm_watson import SpeechToTextV1
from ibm_watson.websocket import RecognizeCallback, AudioSource
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from re import search
from datetime import datetime
import shutil
from configparser import ConfigParser

from msg_tr import tr
from user import ChatState, UserInfo

#Setup Config file
file = 'config.ini'
config = ConfigParser()
config.read(file)

#Obtain userid data from config
admin_list_count = list(config['admin'])
admin_list = []
x = 0
while x < len(admin_list_count):
    admin_list.append(config['admin']['userid' + str(x + 1)])
    print(admin_list)
    x+= 1

admins = admin_list
admins.append(config['main_users']['userid1'])
main_users = admins

main_regular_ratio = 0.5
basic_regular_ratio = 0.5
initial_basic = 30
initial_main = 200

DEBUG = True

score_data = []
current_video_id = ''
############################################################################
def get_video_files():
    from os import listdir
    from os.path import isfile, join
    #obtain video directory from config
    mypath = config['video_directory']['video_dir']
    onlyfiles = [f for f in listdir(mypath) if isfile(join(mypath, f))]
    from os import walk
    f = []
    for (dirpath, dirnames, filenames) in walk(mypath):
        f.extend([mypath+x for x in filenames if x.endswith('.mp4')])
    return f

#Validates string representation of integer is:
#an integer between 0 - 100
#returns integer if valid
def text_to_integer(text_number, number_words={}):
    if not number_words:
        number_units=["zero", "one", "two", "three", "four", "five", "six", "seven", "eight","nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen","sixteen", "seventeen", "eighteen", "nineteen"]
        number_tens=["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
        number_scales=["hundred", "thousand", "million", "billion", "trillion"]
        number_words["and"]=(1, 0)
        for idx, word in enumerate(number_units): number_words[word]=(1, idx)
        for idx, word in enumerate(number_tens): number_words[word]=(1, idx * 10)
        for idx, word in enumerate(number_scales): number_words[word]=(10 ** (idx * 3 or 2), 0)

    current=result=0
    for word in text_number.split():
        if word not in number_words:
            raise Exception("Illegal word: " + word)

        scale, increment=number_words[word]
        current=current*scale+increment
        if scale>100:
            result+=current
            current=0
    return result+current

############################################################################

class MainClass(object):
    def __init__(self):
        super(MainClass).__init__()

        try:
            self.data = self.load_database()
        except:
            print('Can\'t load the database. Creating a new one.')
            self.data = dict()
            self.data['users'] = dict()
            self.data['files'] = dict()
            self.data['files']['regular'] = list()
            self.data['files']['main'] = list()
            self.data['files']['basic'] = list()
            self.scan_command()
            self.setmain(initial_main)
            self.setbasic(initial_basic)

        self.last_save = time.time()

        print('READ')
        print('READ')
        print('USERS:', self.data['users'])
        print('REGULAR:', self.data['files']['regular'])
        print('MAIN:', self.data['files']['main'])
        print('BASIC:', self.data['files']['basic'])
        print('READ')
        print('READ')

        #Obtain bot token from config
        token = config['bot']['token']
        self.updater = Updater(token, use_context=True) # REAL

        self.dispatcher = self.updater.dispatcher
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

        self.dispatcher.add_handler(CommandHandler('start',   self.start))
        self.dispatcher.add_handler(CommandHandler('flush',   self.flush_command))
        self.dispatcher.add_handler(CommandHandler('delete',  self.delete_command))
        self.dispatcher.add_handler(CommandHandler('ignore',  self.ignore_command))
        self.dispatcher.add_handler(CommandHandler('scan',    self.scan_command))
        self.dispatcher.add_handler(CommandHandler('setmain', self.setmain_command))
        self.dispatcher.add_handler(CommandHandler('print',   self.print_command))
        self.dispatcher.add_handler(CommandHandler('len',     self.len_command))
        self.dispatcher.add_handler(CommandHandler('count',   self.count_command))
        self.dispatcher.add_handler(CommandHandler('help',    self.help_command))
        self.dispatcher.add_handler(CommandHandler('backup',    self.user_backup_command))
        self.dispatcher.add_handler(CommandHandler('get',     self.get_command))
        self.dispatcher.add_handler(CommandHandler('restart', self.restart_command))
        #Este MessageHandler solo se activará y permitirá cambios o updates, llamando a text_echo, cuando lo digan los filtros. En este caso, solo permitirá cambios cuando aparezcan mensajes del usuario y que estos no empiecen por comandos.
        self.dispatcher.add_handler(MessageHandler(Filters.text & (~Filters.command), self.text_echo))
        self.dispatcher.add_handler(MessageHandler(Filters.voice & (~Filters.command), self.voice_echo))

        self.lang_kb = telegram.ReplyKeyboardMarkup(
            [[telegram.KeyboardButton('english')], [telegram.KeyboardButton('castellano')]],
            resize_keyboard=True, one_time_keyboard=True)

        self.main_kb = telegram.ReplyKeyboardMarkup(
            [
                #[telegram.KeyboardButton('unacceptable - undesirable'), telegram.KeyboardButton('undesirable - acceptable')],
                #[telegram.KeyboardButton('acceptable - good'), telegram.KeyboardButton('good - very good')],
                #[telegram.KeyboardButton('very good - perfect'), telegram.KeyboardButton('/start')],
                #
                #[telegram.KeyboardButton('/ignore'), telegram.KeyboardButton('/help')],
                #[telegram.KeyboardButton('unacceptable'), telegram.KeyboardButton('undesirable')],
                #[telegram.KeyboardButton('acceptable'), telegram.KeyboardButton('good')],
                #[telegram.KeyboardButton('very good'), telegram.KeyboardButton('perfect')],
                #
                [telegram.KeyboardButton('unacceptable - undesirable'), telegram.KeyboardButton('undesirable - acceptable')],
                [telegram.KeyboardButton('acceptable - good'), telegram.KeyboardButton('good - desirable')],
                [telegram.KeyboardButton('desirable - perfect')],
                [telegram.KeyboardButton('/ignore'), telegram.KeyboardButton('/help'), telegram.KeyboardButton('/start')],

            ],
            resize_keyboard=True, one_time_keyboard=True)
        # first
        a_kb =  [telegram.KeyboardButton('0 unacceptable')] + [telegram.KeyboardButton(str(x)) for x in range(1, 20)] + [telegram.KeyboardButton('20 undesirable')]
        print('LEN A =', len(a_kb))
        a_kb = [ a_kb[0:6], a_kb[6:15], a_kb[15:] ]
        self.a_kb = telegram.ReplyKeyboardMarkup(a_kb, resize_keyboard=True, one_time_keyboard=True)
        # second
        b_kb =  [telegram.KeyboardButton('20 undesirable')] + [telegram.KeyboardButton(str(x)) for x in range(21, 40)] + [telegram.KeyboardButton('40 acceptable')]
        print('LEN B =', len(b_kb))
        b_kb = [ b_kb[0:6], b_kb[6:15], b_kb[15:] ]
        self.b_kb = telegram.ReplyKeyboardMarkup(b_kb, resize_keyboard=True, one_time_keyboard=True)
        # third
        c_kb =  [telegram.KeyboardButton('40 acceptable')] + [telegram.KeyboardButton(str(x)) for x in range(41, 60)] + [telegram.KeyboardButton('60 good')]
        c_kb = [ c_kb[0:6], c_kb[6:15], c_kb[15:] ]
        self.c_kb = telegram.ReplyKeyboardMarkup(c_kb, resize_keyboard=True, one_time_keyboard=True)
        # forth
        #d_kb =  [telegram.KeyboardButton('60 good')] + [telegram.KeyboardButton(str(x)) for x in range(61, 80)] + [telegram.KeyboardButton('80 very good')]
        d_kb =  [telegram.KeyboardButton('60 good')] + [telegram.KeyboardButton(str(x)) for x in range(61, 80)] + [telegram.KeyboardButton('80 desirable')]
        d_kb = [ d_kb[0:6], d_kb[6:15], d_kb[15:] ]
        self.d_kb = telegram.ReplyKeyboardMarkup(d_kb, resize_keyboard=True, one_time_keyboard=True)
        # fifth
        #e_kb =  [telegram.KeyboardButton('80 very good')] + [telegram.KeyboardButton(str(x)) for x in range(81, 100)] + [telegram.KeyboardButton('100 perfect')]
        e_kb =  [telegram.KeyboardButton('80 desirable')] + [telegram.KeyboardButton(str(x)) for x in range(81, 100)] + [telegram.KeyboardButton('100 perfect')]
        e_kb = [ e_kb[0:6], e_kb[6:15], e_kb[15:] ]
        self.e_kb = telegram.ReplyKeyboardMarkup(e_kb, resize_keyboard=True, one_time_keyboard=True)

    def idle(self):
        self.updater.start_polling()

    def scan_command(self, u=None, c=None):
        if u is not None:
            user = self.get_user_data(u)
            if user.uid not in admins:
                return

        all_files = get_video_files()
        new_files = list( set(all_files) - set(self.data['files']['regular']) )
        self.data['files']['regular'] += new_files
        random.shuffle(self.data['files']['regular'])
        if u is not None:
            self.reply(u, c, str(len(self.data['files']['regular'])))

    def len_command(self, u, c):
        user = self.get_user_data(u)
        if user.state == ChatState.EXPECT_LANGUAGE:
            self.reply(u, c, tr('lang', user), kb=self.lang_kb)
        else:
            l = len(user)
            self.reply(u, c, str(l))

    def help_command(self, u, c):
        user = self.get_user_data(u)
        if user.state == ChatState.EXPECT_LANGUAGE:
            self.reply(u, c, tr('lang', user), kb=self.lang_kb)
        else:
            self.reply(u, c, tr('help', user))

    def restart_command(self, u, c):
        user = self.get_user_data(u)
        if user.state == ChatState.EXPECT_LANGUAGE:
            self.reply(u, c, tr('lang', user), kb=self.lang_kb)
        else:
            if user.uid not in admins:
                return
                threading.Thread(target=self.shutdown).start()

    def shutdown(self):
        self.updater.stop()
        self.updater.is_idle = False
        time.sleep(1)
        self.flush_database()
        time.sleep(1)
        # os.exit(0)
        os.system('kill -9 %d' % os.getpid())

    def get_command(self, u, c):
        user = self.get_user_data(u)
        if user.uid not in admins:
            return

        from zipfile import ZipFile
        self.flush_database()
        with ZipFile('doc.zip','w') as zip:
            for f in ['bot.db']:
                zip.write(f)
        c.bot.send_document(chat_id=u.message.chat_id, document=open('doc.zip', 'rb'))

    def count_command(self, u, c):
        user = self.get_user_data(u)
        if user.uid not in admins:
            self.reply(u, c, tr('access', user))
            return

        l = len(user)
        total = 0
        for k, v in self.data['users'].items():
            total += len(v.input)
        self.reply(u, c, str(total)+' ('+str(l)+')')

    def print_command(self, u=None, c=None):
        if u is not None:
            user = self.get_user_data(u)
            if user.uid not in admins:
                return

        ret = ''
        for k, v in self.data['users'].items():
            ret += str(k) + ' ' + str(self.data['users'][k].uname) + ' ' + str(len(v.input)) + '\n'
        self.reply(u, c, ret)

    def setmain_command(self, u, c):
        user = self.get_user_data(u)
        if user.uid not in admins:
            self.reply(u, c, tr('access', user))
            return

        text = u.message.text.split()
        if len(text) != 2:
            self.reply(u, c, tr('syntax', user))

        text = text[1]

        try:
            set_size = int(text)
            self.setmain(set_size)
        except Exception as e:
            s = str(e)
            self.reply(u, c, s)
        self.reply(u, c, tr('done', user))

    def setmain(self, set_size):
        print('SET MAIN', set_size)
        random.shuffle(self.data['files']['regular'])
        for i in self.data['files']['regular']:
            if i not in self.data['files']['main']:
                if len(self.data['files']['main']) >= set_size:
                    break
                else:
                    self.data['files']['main'].append(i)

    def setbasic(self, set_size):
        print('SET BASIC')
        self.data['files']['basic'] = self.data['files']['main'][0:set_size]

    def load_database(self):
        with open('bot.db', 'rb') as fd:
            return pickle.load(fd)

    def flush_database(self):
        print('Flushing')
        with open('bot.db', 'wb') as fd:
            pickle.dump(self.data, fd)

    def check_flush(self):
        delta_seconds = time.time() - self.last_save
        if delta_seconds > 3600:
            self.last_save = time.time()
            self.flush_database()

    def get_user_data(self, src):
        print('-------DEF GET USER DATA----------------')
        uname = None
        print('Que tipo esssssssssssss = ', str(type(src))) ###VAMOS POR ACAAAAA
        if type(src) == telegram.update.Update:
            uid   = src['message']['chat']['id']
            uname = src['message']['chat']['username']
            if uname is None:
                uname = src['message']['chat']['first_name'] + ' ' + src['message']['chat']['last_name']
        elif type(src) == int:
            uid = src
        else:
            raise(str(type(src)))

        try:
            ret = self.data['users'][uid]
            if ret.uname is None:
                ret.uname = uname
        except Exception:
            ret = UserInfo(uid, uname)
            self.data['users'][uid] = ret
        print('-------TERMINA GET USER DATA----------------')
        return ret

    def reply(self, u, c, text, kb=None):
        print('-------DEF REPLY----------------')
        user = self.get_user_data(u)
        print('UID', user.uid)
        print('TEXTO A ENVIAR= ', text)
        if str(user.uid) in config['admin']['userid2']:
            print('IGNORE KEYBOARD BY UID')
            kb = None
        ret = c.bot.send_message(chat_id=u.effective_chat.id, text=text, reply_markup=kb)
        print('-------TERMINA REPLY----------------')

    def set_keyboard(self, u, c, kb):
        print('-------DEF SET KEYBOARD----------------')
        print('Tipo de la u = ', type(u))
        #user = self.get_user_data(u)
        user = u
        print('UID', user.uid)
        if str(user.uid) in config['admin']['userid2']:
            print('Llega a ser un admin')
            print('IGNORE KEYBOARD BY UID')
            return
        print('Llega a ser un no admin')
        #ret = c.bot.send_message(chat_id=u.effective_chat.id, text='got it', reply_markup=kb)
        #ret = c.bot.send_message(chat_id=user.uid, text='got it', reply_markup=kb)
        ret = c.bot.send_message(chat_id=user.uid, text=tr('choose_value', user), reply_markup=kb)
        print('-------TERMINA SET KEYBOARD----------------')

    def start(self, u, c):
        print('-----------------------START comenzar-----------------------------')
        print('información update = ',u)
        print('información context = ',c)
        user = self.get_user_data(u)
        print('información conseguida de update = ', user)
        print('tipo de user = ', type(user))
        user.lang = ''
        user.current_sample = -1
        user.q1 = -1
        user.q2 = -1
        user.state = ChatState.EXPECT_LANGUAGE
        print('---------------START sigue------------------')

        self.reply(u, c, tr('lang', user), kb=self.lang_kb)
        print('--------------------START termina----------------------------')

    def flush_command(self, u, c):
        user = self.get_user_data(u)
        if user.uid in admins:
            self.flush_database()
            self.reply(u, c, tr('done', user))

    def delete_command(self, u, c):
        user = self.get_user_data(u)
        if user.state == ChatState.EXPECT_LANGUAGE:
            self.reply(u, c, tr('lang', user), kb=self.lang_kb)
        else:
            sid = u.message.text.split()[1]
            try:
                if sid.endswith('D'):
                    del user.input['videos/'+sid[:-1]+'.mp4'+'D']
                else:
                    del user.input['videos/'+sid+'.mp4']
                self.reply(u, c, tr('donestill', user))
            except:
                self.reply(u, c, tr('cannotdelete', user))
            self.check_flush()

    def ignore_command(self, u, c):
        print('----------DEF IGNORE_COMMAND---------')
        user = self.get_user_data(u)
        if user.state == ChatState.EXPECT_LANGUAGE:
            self.reply(u, c, tr('lang', user), kb=self.lang_kb)
        else:
            sid = user.current_sample
            try:
                del user.input[sid]
            except:
                pass
            self.reply(u, c, tr('done', user))
            self.send_new_sample(u, c, user)
            self.send_q1_question(u, c, user)
            user.state = ChatState.EXPECT_Q1
            self.check_flush()
        print('----------TERMINA IGNORE_COMMAND---------')

    #Method to send user a message containing their scoring data
    def user_backup_command(self, u, c):
        #retrieve user data
        user = self.get_user_data(u)
        if user.state == ChatState.EXPECT_LANGUAGE:
            self.reply(u, c, tr('lang', user), kb=self.lang_kb)
        else:
            #create user backup file by copying saved user _data_file.txt into a _backup_data_file file.
            user_file = str(user.uid)+"_data_file.txt"
            backup_user_file = str(user.uid)+"_backup_data_file.txt"
            #check that user has inputed scores before sending file.
            if os.path.isfile(user_file):
                shutil.copyfile(user_file, backup_user_file)
                self.reply(u, c, tr('backup', user))
                c.bot.send_document(chat_id=u.message.chat_id, document=open(str(user.uid)+'_backup_data_file.txt', 'rb'))
                os.remove(str(user.uid)+"_backup_data_file.txt")
            else:
                self.reply(u, c, tr('cannot_backup', user))

    #creates file with user's scoring data
    def file_score_user(self, userid, score_list):
        print('----------DEF FILE_SCORE_USER---------')
        #conditional check if user has any score data
        if score_list == []:
            print("NOT FOUND")
        #If score data exists, file created named as specific user's userid + _data_file.txt
        else:
            #if no file exists, one is created and the user's score_list is written in
            user_file = str(userid)+"_data_file.txt"
            if not os.path.isfile(user_file):
                with open(user_file, 'w+') as file:
                    file.write("%s" % score_list)
                    file.write("\n")
                    file.close()
            else:
                #if file exists, the score_list data is written into it
                with open(user_file, 'a') as file:
                    file.write("%s" % score_list)
                    file.write("\n")
                    file.close()
        print('----------TERMINA FILE_SCORE_USER---------')

    def text_echo(self, u, c):
        print('-------------------------COMIENZA LLAMADA A TEXT_ECHO-------------------------')
        user = self.get_user_data(u)
        if user.state == ChatState.UNINITIALISED:
            print('--------------TEXT_ECHO STATE UNINITIALISED----------------')
            self.start(u, c)
        elif user.state == ChatState.EXPECT_LANGUAGE:
            print('------------TEXT_ECHO STATE EXPECT_LANGUAGE---------------')
            if self.process_language(u, c, user):
                self.send_new_sample(u, c, user)
                self.send_q1_question(u, c, user)
                user.state = ChatState.EXPECT_Q1
            else:
                self.reply(u, c, tr('lang', user), kb=self.lang_kb)
        elif user.state == ChatState.EXPECT_Q1:
            print('----------------TEXT_ECHO STATE EXPECT_Q1----------------')
            #appends to array to store user survey information. (To be added to the user specific backup file)
            if(len(score_data)==0):
                date_timestamp = datetime.now()
                date_timestamp_format = date_timestamp.strftime("%d/%m/%Y - (%H:%M:%S)")
                video_id = str(user.current_sample.split('/')[1].split('.')[0])
                print(video_id)
                score_data.append(date_timestamp_format)
                score_data.append(video_id)
                score_data.append(user.uid)
            try:
                print('El dia de mi muerte')
                text_return_q1=self.text_process(u)
                print('El dia de mi muerte x2')
                print('TEXT RETURN = ', text_return_q1)
                if self.process_q1(text_return_q1, c, user):
                    print('bagunsaaaa')
                    score_data.append('Q1: '+text_return_q1)
                    self.send_q1_confirmation(u, c, user)
                    self.send_q2_question(u, c, user)
                    user.state = ChatState.EXPECT_Q2
                else:
                    print('not process_q1')
            except:
                self.reply(u, c, tr('notvalid', user))
                print('holiiiii1')
        elif user.state == ChatState.EXPECT_Q2:
            print('----------------TEXT_ECHO STATE EXPECT_Q2----------------')
            try:
                text_return_q2=self.text_process(u)
                if self.process_q2(text_return_q2, c, user):
                    score_data.append('Q2: '+text_return_q2)
                    self.send_q2_confirmation(u, c, user)
                    self.send_new_sample(u, c, user)
                    self.send_q1_question(u, c, user)
                    user.state = ChatState.EXPECT_Q1
                else:
                    print('not process_q1')
            except:
                self.reply(u, c, tr('notvalid', user))
                print('holiiiii2')
        else:
            c.bot.send_message(chat_id=u.effective_chat.id, text="It seems that the chat is not initialised. We'll restart...")
            self.start(u, c)

        if(len(score_data)==5):
            self.file_score_user(user.uid, score_data)
            score_data.clear()
        self.check_flush()
        print('-------------------------TERMINA LLAMADA A TEXT_ECHO-------------------------')

    #Voice handling method. Parameters are the user information and the bot's context data.
    #starts survey and calls methods based on the ChatState.
    def voice_echo(self, u, c):
        #create variable to hold user chat information
        user = self.get_user_data(u)
        #initialise chat if it has yet to be started. Requires any user keyboard input to start
        if user.state == ChatState.UNINITIALISED:
            self.start(u, c)
        #confirm user language has been entered and saves it, else asks for language.
        elif user.state == ChatState.EXPECT_LANGUAGE:
            #Start survey and send a video clip and asks user for q1 score
            if self.process_language(u, c, user):
                self.send_new_sample(u, c, user)
                self.send_q1_question(u, c, user)
                user.state = ChatState.EXPECT_Q1
            else:
                self.reply(u, c, tr('lang', user), kb=self.lang_kb)
        #If Q1 response sent by user
        elif user.state == ChatState.EXPECT_Q1:
            #appends to array to store user survey information. (To be added to the user specific backup file)
            if(len(score_data)==0):
                date_timestamp = datetime.now()
                date_timestamp_format = date_timestamp.strftime("%d/%m/%Y - (%H:%M:%S)")
                video_id = str(user.current_sample.split('/')[1].split('.')[0])
                print(video_id)
                score_data.append(date_timestamp_format)
                score_data.append(video_id)
                score_data.append(user.uid)
            #calls voice_process method to convert voice to text. The response is sent to process_q1 to validate score
            #Q1 confirmation message sent, and user is asked for Q2 score
            try:
                voice_return_q1=self.voice_process(u)
                if self.process_q1(voice_return_q1, c, user):
                    score_data.append('Q1: '+voice_return_q1)
                    self.send_q1_confirmation(u, c, user)
                    self.send_q2_question(u, c, user)
                    user.state = ChatState.EXPECT_Q2
                else:
                    print('not process_q1')
            except:
                self.reply(u, c, tr('notvalid', user))
                print('holiiiii3')
        elif user.state == ChatState.EXPECT_Q2:
            #calls voice_process method to convert voice to text. The response is sent to process_qw to validate score
            #Q2 confirmation message sent, and user is sent new video clip and asked for Q1 score
            try:
                voice_return_q2=self.voice_process(u)
                if self.process_q2(voice_return_q2, c, user):
                    score_data.append('Q2: '+voice_return_q2)
                    self.send_q2_confirmation(u, c, user)
                    self.send_new_sample(u, c, user)
                    self.send_q1_question(u, c, user)
                    user.state = ChatState.EXPECT_Q1
                else:
                    print('not process_q1')
            except:
                self.reply(u, c, tr('notvalid', user))
                print('holiiiii4')
        #if user's chatstate not in any of the enum values, the below message is sent.
        else:
            c.bot.send_message(chat_id=u.effective_chat.id, text="It seems that the chat is not initialised. We'll restart...")
            self.start(u, c)
        #Score_data is populated with backup data when 1 full score is given
        #score_data is sent to be saved, and score_data cleared to recieve next scoring backup data
        #(user id, timestamp, video ids, Q1 score, Q2 score)
        if(len(score_data)==5):
            self.file_score_user(user.uid, score_data)
            score_data.clear()
        self.check_flush()

    def process_language(self, u, c, user):
        print('------COMIENZA PROCESS_LANGUAGE-----')
        inp = u.message.text.lower().strip()
        if   len([x for x in ['english',   'ingles', 'inglés']                if inp.find(x)!=-1]) > 0:
            user.lang = 'en'
            print('------TERMINA PROCESS_LANGUAGE-----')
            return True
        elif len([x for x in [ 'spanish', 'espanol', 'español', 'castellano'] if inp.find(x)!=-1]) > 0 :
            user.lang = 'es'
            print('------TERMINA PROCESS_LANGUAGE-----')
            return True
        else:
            print('__'+inp+'__')
            print('------TERMINA PROCESS_LANGUAGE-----')
            return False

    def text_process(self, u):
        print('------COMIENZA TEXT_PROCESS-----')
        text = u.message.text.lower().strip()
        first = str(text.split()[0])
        print('------TERMINA TEXT_PROCESS-----')
        return first

    #Function to process voice and returns text conversion.
    def voice_process(self, u):
        #Voice grabbed from user's message to bot
        #Filepath assigned and local directory checked/created for voice files.
        voice = u.message.voice.file_id.strip()
        bot=telegram.Bot(token=config['bot']['token'])
        newfile=bot.getFile(voice)
        filepath=newfile.file_path.strip()
        filepath_request=requests.get(filepath, allow_redirects=True)
        voice_files=[]
        voice_directory='game_voice_notes'
        if not os.path.exists(voice_directory):
            os.makedirs(voice_directory)

        #Voice file directory parsed and voice_files list writes user's voice message to a file
        directory=os.path.normpath(os.getcwd()+os.sep+voice_directory+os.sep)
        for r, d, f in os.walk(directory):
            for file in f:
                if 'voice' in file:
                    voice_files.append(file)
        voice_file_number=len(voice_files)+1
        open(os.path.join(directory,'voice'+str(voice_file_number)+'.oga'), 'wb').write(filepath_request.content)

        #Assign api credentials required to access ibm_watson
        api_key=config['ibm_watson']['api_key']
        api_url=config['ibm_watson']['api_url']
        # Setup Service
        authenticator=IAMAuthenticator(api_key)
        stt=SpeechToTextV1(authenticator=authenticator)
        stt.set_service_url(api_url)

        #Read current voice file
        #Sends request to ibm_watson speechToText service containing voice file and the type of audio. Then Return result
        with open(os.path.join(directory, 'voice'+str(voice_file_number)+'.oga'), 'rb') as voice_file:
            ibm_request=stt.recognize(audio=voice_file, content_type='audio/ogg', model='en-UK_NarrowbandModel', continuous=True).get_result()

        #Assign results of ibm_request
        #Text transcript
        #Confidence of the service's conversion of speech to text
        voice_text=ibm_request['results'][0]['alternatives'][0]['transcript']
        confidence=ibm_request['results'][0]['alternatives'][0]['confidence']

        #Verification of text return as an integer between 0 - 100
        voice_integer_number=str(text_to_integer(voice_text))

        print(f'Voice Text: {voice_text}')
        print(f'Voice Number: {voice_integer_number}')
        print(f'Voice Confidence: {confidence}')

        #Return text score between 0-100
        return voice_integer_number

    def process_q1(self, first, c, user):
        print('FIRST = ', first)
        print('-------DEF PROCESS_Q1------')
        if first == 'unacceptable':
            print('Entra unacceptable')
            self.set_keyboard(user, c, self.a_kb)
            print('Adios unacceptable')
            return False
        elif first == 'undesirable':
            self.set_keyboard(user, c, self.b_kb)
            return False
        elif first == 'acceptable':
            self.set_keyboard(user, c, self.c_kb)
            return False
        elif first == 'good':
            self.set_keyboard(user, c, self.d_kb)
            return False
        elif first == 'desirable':
            self.set_keyboard(user, c, self.e_kb)
            return False
        #elif first == 'very':
            #try:
            #    print('trying')
            #    self.set_keyboard(user, c, self.e_kb)
            #    print('done')
            #except Exception as e:
            #    print(e)
            #return False

        if len(first) > 3:
            raise Exception('invalid input'+first)
        try:
            q1 = int(first)
            if q1 < 0 or q1 > 100:
                print('Invalid input 2', first)
                raise Exception('invalid input'+first)
            try:
                user.add_q1_for_current_sequence(q1)
            except Exception as e:
                print(e)
        except Exception:
            print('Invalid input 3', first)
            raise Exception('invalid input'+first)
        return True

    def process_q2(self, first, c, user):
        print('-------DEF PROCESS_Q2------')
        if first == 'unacceptable':
            self.set_keyboard(user, c, self.a_kb)
            return False
        elif first == 'undesirable':
            self.set_keyboard(user, c, self.b_kb)
            return False
        elif first == 'acceptable':
            self.set_keyboard(user, c, self.c_kb)
            return False
        elif first == 'good':
            self.set_keyboard(user, c, self.d_kb)
            return False
        elif first == 'desirable':
            self.set_keyboard(user, c, self.e_kb)
            return False

        if len(first) > 3:
            raise Exception('invalid input'+first)
        try:
            q2 = int(first)
            if q2 < 0 or q2 > 100 or q2 > user.current_q1():
                raise Exception('invalid input'+first)
            user.add_q2_for_current_sequence(q2)
        except Exception:
            print('Invalid input 3', first)
            raise Exception('invalid input'+first)
        return True

    def send_new_sample(self, u, c, user):
        print('Send new sample')
        if user.uid in main_users:
            # MAIN USER
            if DEBUG: self.reply(u, c, 'You are a main user')
            if random.random() < main_regular_ratio:
                # SUBSET SAMPLE
                if DEBUG: self.reply(u, c, 'I\'ll try with a main sample')
                if not self.send_new_sample_main(u, c, user):
                    if DEBUG: self.reply(u, c, 'It seems it did not work, sending a regular sample')
                    self.send_new_sample_regular(u, c, user, change=True)
            else:
                # REGULAR SAMPLE
                if DEBUG: self.reply(u, c, 'I\'ll try with a regular sample')
                if not self.send_new_sample_regular(u, c, user):
                    if DEBUG: self.reply(u, c, 'It seems it did not work, sending a main sample')
                    self.send_new_sample_main(u, c, user)
        else:
            # REGULAR USER
            if random.random() < basic_regular_ratio:
                # SUBSET SAMPLE
                if not self.send_new_sample_basic(u, c, user):
                    self.send_new_sample_regular(u, c, user, change=True)
            else:
                # REGULAR SAMPLE
                if not self.send_new_sample_regular(u, c, user):
                    self.send_new_sample_basic(u, c, user)

    def send_new_sample_main(self, u, c, user, change=False):
        found = False
        random.shuffle(self.data['files']['main'])
        for sample in self.data['files']['main']:
            if not sample in user.input:
                found = True
                break
        if found:
            if DEBUG: self.reply(u, c, 'Sending a main-first one')
            user.current_sample = sample
            c.bot.send_video(chat_id=u.message.chat_id, video=open(sample, 'rb'), supports_streaming=True)
            self.reply(u, c, 'ID: '+str(user.current_sample.split('/')[1].split('.')[0]), kb=self.main_kb)
            return True
        else:
            if DEBUG: self.reply(u, c, 'Trying to send a main-dup one')
            return self.send_new_sample_dup(u, c, user)

    def send_new_sample_basic(self, u, c, user, change=False):
        print('Send new sample BASIC')
        found = False
        random.shuffle(self.data['files']['basic'])
        for sample in self.data['files']['basic']:
            if not sample in user.input:
                found = True
                break
        if found:
            user.current_sample = sample
            c.bot.send_video(chat_id=u.message.chat_id, video=open(sample, 'rb'), supports_streaming=True)
            self.reply(u, c, 'ID: '+str(user.current_sample.split('/')[1].split('.')[0]), kb=self.main_kb)
        return found

    def send_new_sample_dup(self, u, c, user, change=False):
        print('Send new sample DUP')
        found = False
        random.shuffle(self.data['files']['main'])
        for sample in self.data['files']['main']:
            if not sample+'D' in user.input:
                found = True
                break

        if found:
            if DEBUG: self.reply(u, c, 'Sending a dup one!')
            user.current_sample = sample+'D'
            c.bot.send_video(chat_id=u.message.chat_id, video=open(sample, 'rb'), supports_streaming=True)
            self.reply(u, c, 'ID: '+str(user.current_sample.split('/')[1].split('.')[0])+'D', kb=self.main_kb)
            return True
        elif not change:
            return self.send_new_sample_regular(u, c, user, change=True)
        else:
            self.reply(u, c, 'You did all samples! Thank you! (this is probably an error).')
            return False

    def send_new_sample_regular(self, u, c, user, change=False):
        print('Send new sample REGULAR')
        random.shuffle(self.data['files']['regular'])
        found = False
        for sample in self.data['files']['regular']:
            if not sample in user.input:
                found = True
                break

        if found is True:
            user.current_sample = sample
            c.bot.send_video(chat_id=u.message.chat_id, video=open(sample, 'rb'), supports_streaming=True)
            self.reply(u, c, 'ID: '+str(user.current_sample.split('/')[1].split('.')[0]), kb=self.main_kb)
            return True
        else:
            if user.uid not in main_users or change:
                self.reply(u, c, 'You did all samples! Thank you! (this is probably an error).', kb=self.main_kb)
                return False
            else:
                return self.send_new_sample_main(u, c, user, change=True)
        raise Exception('132131frwejf8jd38')

    def send_q1_question(self, u, c, user):
        print('--------DEF SEND_Q1_QUESTION----------')
        self.reply(u, c, tr('q1question', user), kb=self.main_kb)
        print('--------TERMINA SEND_Q1_QUESTION----------')


    def send_q1_confirmation(self, u, c, user):
        print('--------DEF SEND_Q1_CONFIRMATION----------')
        self.reply(u, c, tr('q1confirmation', user))
        print('--------TERMINA SEND_Q1_CONFIRMATION----------')


    def send_q2_question(self, u, c, user):
        print('--------DEF SEND_Q2_QUESTION----------')
        self.reply(u, c, tr('q2question', user), kb=self.main_kb)
        print('--------TERMINA SEND_Q2_QUESTION----------')


    def send_q2_confirmation(self, u, c, user):
        print('--------DEF SEND_Q2_CONFIRMATION----------')
        self.reply(u, c, tr('q2confirmation', user))
        print('--------TERMINA SEND_Q2_CONFIRMATION----------')

if __name__ == '__main__':
    print('------------------MAIN Aquí empieza----------------------')
    main = MainClass()
    print('------------------MAIN Aquí sigue----------------------')
    main.idle()
    print('------------------MAIN Aquí termina----------------------')
