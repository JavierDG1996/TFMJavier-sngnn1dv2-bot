from ibm_watson import SpeechToTextV1
from ibm_watson.websocket import RecognizeCallback, AudioSource
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
import os
from configparser import ConfigParser

#Setup config file
file = 'config.ini'
config = ConfigParser()
config.read(file)

class voice_to_text():

    def __init__(self, input_file):
        self.input_file = input_file

    #Validate text is a valid number input, between 0 - 100
    def text_to_integer(text_number, confidence, number_words={}):
        if not number_words:
            number_units=["zero", "one", "two", "three", "four", "five", "six", "seven", "eight","nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen","sixteen", "seventeen", "eighteen", "nineteen"]
            number_tens=["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
            number_scales=["hundred", "thousand", "million", "billion", "trillion"]
            number_words["and"]=(1, 0)
            for idx, word in enumerate(number_units): number_words[word]=(1, idx)
            for idx, word in enumerate(number_tens): number_words[word]=(1, idx * 10)
            for idx, word in enumerate(number_scales): number_words[word]=(10 ** (idx * 3 or 2), 0)

        current=result=0

        #if word is illegal add to a list
        for word in text_number.split():
            if word not in number_words:
                print("Illegal word: " + word)
                exception_word_list.append(word)
                exception_confidence_list.append(confidence)
                illegal_word = "Illegal Word"
                return illegal_word
            else:
                scale, increment=number_words[word]
                current=current*scale+increment
                if scale>100:
                    result+=current
                    current=0
                return result+current

    #Setup IBM watson service
    def connect_to_ibm_watson():
        api_key=config['ibm_watson']['api_key']
        api_url=config['ibm_watson']['api_url']
        authentication_connect = IAMAuthenticator(api_key)
        speech_to_text_service = SpeechToTextV1(authenticator=authentication_connect)
        speech_to_text_service.set_service_url(api_url)
        return speech_to_text_service

    #Function to send IBM Watson test audio file, and return the integer it is recognised as, aswell as the associated confidence
    def convert_voice_to_text(self):
        print(self.input_file)
        ibm_watson_connect = voice_to_text.connect_to_ibm_watson()
        with open(os.path.join(self.input_file), 'rb') as voice_file:
            try:
                ibm_watson_request = ibm_watson_connect.recognize(audio=voice_file, content_type='audio/wav', model='en-UK_NarrowbandModel', continuous=True).get_result()
                voice_text=ibm_watson_request['results'][0]['alternatives'][0]['transcript']
                confidence=ibm_watson_request['results'][0]['alternatives'][0]['confidence']
                voice_integer_number=str(voice_to_text.text_to_integer(voice_text, confidence))
                if voice_integer_number == "Illegal Word":
                    confidence="No Confidence"
                print(f'Voice Text: {voice_text}')
                print(f'Voice Number: {voice_integer_number}')
                print(f'Voice Confidence: {confidence}')
                return voice_integer_number, confidence
            except:
                pass

#Main method to run test
if __name__ == '__main__':
    #directory where test speech is kept
    audio_dir = os.path.normpath(os.getcwd()+os.sep+'test_speech')
    #creation of multiple lists
    audio_files = []
    voice_number_list = []
    voice_confidence_list = []
    high_voice_confidence_list = []
    low_voice_confidence_list = []
    exception_word_list = []
    exception_confidence_list = []
    overall_list = []
    #Iterate through test speech files and append to audio_files
    x = 0
    for dir, subdirs, files in os.walk(audio_dir):
        for file in files:
            if file.endswith('.wav') or file.endswith('.mp3'):
                audio_files.append(dir + "/" + file)
    #Iterate through audio_files
    #convert audio to text
    #If confidence is not 0, append data to appropriate lists
    for x in range(len(audio_files)):
        voice_instance = voice_to_text(audio_files[x])
        try:
            voice_number, voice_confidence = voice_instance.convert_voice_to_text()
            if voice_confidence != "No Confidence":
                #append integer
                voice_number_list.append(voice_number)
                #append confidence of ibm service's recongition of number
                voice_confidence_list.append(voice_confidence)
                overall_list.append(voice_confidence)
                print(voice_confidence_list)
            else:
                #append voice_confidence even if voice was not recognised as integer
                overall_list.append(voice_confidence)
        except:
            pass
    #Print various lists to be analysed
    print("The exception words are: " + str(exception_word_list))
    print("The exception confidences are: " + str(exception_confidence_list))
    print("The overall list of attempted recognitions: " + str(overall_list))
    high_voice_confidence_list = [x for x in voice_confidence_list if x >= 0.75]
    low_voice_confidence_list = [x for x in voice_confidence_list if x < 0.75]
    print("The entries with greater or equal to than 0.70 confidence are: " + str(high_voice_confidence_list))
    print("The entries with lower than 0.70 confidence are: " + str(low_voice_confidence_list))
    average_voice_confidence = sum(voice_confidence_list) / len(voice_confidence_list)
    print("The average voice confidence of the recogised recordings is: " + str(average_voice_confidence))
