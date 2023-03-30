import json
import enum
from datetime import datetime

class ChatState(enum.Enum):
    UNINITIALISED   = enum.auto()
    EXPECT_LANGUAGE = enum.auto()
    EXPECT_Q1       = enum.auto()
    EXPECT_Q2       = enum.auto()
    EXPECT_Q3       = enum.auto()

class UserInfo(object):
    def __init__(self, uid, uname):
        self.init_from_dictionary({'uid': uid, 'uname': uname})

    def init_from_dictionary(self, data):
        # Get the user identifier
        try:
            self.uid = data['uid']
        except Exception as ex:
            err = 'A user identifier "uid" must be provided.'
            print(err)
            raise Exception(err)
        # Get the user identifier
        try:
            self.uname = data['uname']
        except Exception as ex:
            err = 'A username "uname" must be provided.'
            print(err)
            raise Exception(err)
        # Get the language
        try:
            self.lang = data['lang']
        except Exception:
            self.lang = 'en'
        # Get the state of the "conversation"
        try:
            self.state = ChatState(data['state'])
        except Exception:
            self.state = ChatState.UNINITIALISED
        # Get the current sample, if any
        try:
            self.current_sample = data['current_sample']
        except:
            self.current_sample = -1
        # Get the input, if any
        try:
            self.input = data['input']
        except:
            self.input = dict()

    def add_q1_for_current_sequence(self, q1):
        try:
            self.input[self.current_sample][0] = q1
        except:
            self.input[self.current_sample] = [q1, 0, 0, 0]


    def add_q2_for_current_sequence(self, q2):
        try:
            #date_timestamp = datetime.now()
            #date_timestamp_format = date_timestamp.strftime("%d/%m/%Y - (%H:%M:%S)")
            self.input[self.current_sample][1] = q2
            #self.input[self.current_sample][2] = date_timestamp_format
        except Exception as e:
            print(e)
            raise e
            
    def add_q3_for_current_sequence(self, q3):
        try:
            date_timestamp = datetime.now()
            date_timestamp_format = date_timestamp.strftime("%d/%m/%Y - (%H:%M:%S)")
            self.input[self.current_sample][2] = q3
            self.input[self.current_sample][3] = date_timestamp_format
        except Exception as e:
            print(e)
            raise e

    def __len__(self):
        return len(self.input)

    def current_q1(self):
        return self.input[self.current_sample][0]

    def current_q2(self):
        return self.input[self.current_sample][1]
        
    def current_q3(self):
        return self.input[self.current_sample][2]

    def get_len_videos(self):
        return len(self.input)

    def __repr__(self):
        s = '<USER '
        s += str(self.uname) + ' ('
        s += 'UID ' + str(self.uid) + ') '
        s += 'LANG = ' + str(self.lang) + ', '
        s += 'STATE = ' + str(self.state) + ', '
        s += 'CURRENT_SAMPLE = ' + str(self.current_sample) + '\n'
        s += str('INPUT = [\n')
        for k in self.input:
            s += ' ' + str(k) + ' ' + str(self.input[k]) + ' '
        s += str(']\n')
        s += '>'
        return s

    def __str__(self):
        return self.__repr__()
