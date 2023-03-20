import pytest
from pytest_testconfig import config
import re
import os.path
from os import path
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibm_watson import SpeechToTextV1
from ibm_watson import ApiException
import json
from ibm_watson.websocket import RecognizeCallback, AudioSource

class TestClass:

    def test_token_format(self):
        #test token inputs
        try:
            token = config['bot']['token']
            matched = bool(re.match("^[0-9]{8,10}:[a-zA-Z0-9_-]{35}$", token))
            assert matched == True
        except:
            raise Exception("The Telegram bot token format is incorrect")

    def test_userids_format(self):
        #test the userids in the config file are valid.
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

        try:
            for x in main_users:
                assert int(x) > 0
                assert str.isdecimal(x) == True
                assert len(x) <= 10
                assert len(x) >= 6
        except:
            raise Exception("the userid " + x + " is not valid")

    def test_ibmwatson_call(self):
        #test that the api key and api url provided for ibm_watson are a valid format
        api_key=config['ibm_watson']['api_key']
        api_url=config['ibm_watson']['api_url']
        # Setup Service
        authenticator=IAMAuthenticator(api_key)
        stt=SpeechToTextV1(authenticator=authenticator)
        stt.set_service_url(api_url)
        # Send a request to the Ibm_Watson Server and verify it is a valid request considering the API key and API Url.
        try:
            response = stt.list_models()
            assert response.get_status_code() == 200
        except:
            raise Exception("The status code is " + str(response.get_status_code()))

    def test_video_dir_valid(self):
        #test that the video directory provided exists and is valid
        try:
            video_dir = config['video_directory']['video_dir']
            assert path.exists(video_dir) == True
        except:
            raise Exception("The path to the videos doesn't exist!")

    def test_survey_messages_en_valid(self):
        #test that the english messages in the config file are valid
        survey_section_list = list(config['dataset_survey_messages_en'])

        x = 0
        while x < len(survey_section_list):
            survey_message = config['dataset_survey_messages_en'][survey_section_list[x]]
            try:
                assert len(survey_message) < 250
                x+=1
            except:
                raise Exception(survey_message)

        def test_survey_messages_es_valid(self):
            #test that the spanish messages in the config file are valid
            survey_section_list = list(config['dataset_survey_messages_es'])

            x = 0
            while x < len(survey_section_list):
                survey_message = config['dataset_survey_messages_es'][survey_section_list[x]]
                try:
                    assert len(survey_message) < 250
                    x+=1
                except:
                    raise Exception(survey_message)
