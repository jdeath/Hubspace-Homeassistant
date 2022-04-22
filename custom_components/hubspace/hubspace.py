import requests
import json
import re
import calendar
import datetime
import hashlib
import base64
import os
import asyncio
import logging

_LOGGER = logging.getLogger(__name__)

class HubSpace:
    
    _refresh_token = None
    _password = None
    _username = None
    _accountId = None
    _last_token = None
    _last_token_time = None
    # Token lasts 120 seconds
    _token_duration = 118 * 1000
    
    def __init__(self, username,password):
        self._username = username
        self._password = password
        self._refresh_token = self.getRefreshCode()
        self._accountId = self.getAccountId()
    
    def getUTCTime(self):
        date = datetime.datetime.utcnow()
        utc_time = calendar.timegm(date.utctimetuple()) * 1000
        return utc_time
        
    def getCodeVerifierAndChallenge(self):
        code_verifier = base64.urlsafe_b64encode(os.urandom(40)).decode('utf-8')
        code_verifier = re.sub('[^a-zA-Z0-9]+', '', code_verifier)
        code_challenge = hashlib.sha256(code_verifier.encode('utf-8')).digest()
        code_challenge = base64.urlsafe_b64encode(code_challenge).decode('utf-8')
        code_challenge = code_challenge.replace('=', '')
        return code_challenge,code_verifier

    def getRefreshCode(self):
        
        URL = "https://accounts.hubspaceconnect.com/auth/realms/thd/protocol/openid-connect/auth"
        
        [code_challenge,code_verifier] = self.getCodeVerifierAndChallenge()
        
        # defining a params dict for the parameters to be sent to the API
        PARAMS = {'response_type':'code',
                'client_id':'hubspace_android',
                'redirect_uri':'hubspace-app://loginredirect',
                'code_challenge':code_challenge,
                'code_challenge_method':'S256',
                'scope':'openid offline_access',
                }
      
        # sending get request and saving the response as response object
        r = requests.get(url = URL, params = PARAMS)
        r.close()
        headers = r.headers

        session_code = re.search('session_code=(.+?)&', r.text).group(1)
        execution = re.search('execution=(.+?)&', r.text).group(1)
        tab_id = re.search('tab_id=(.+?)&', r.text).group(1)


        auth_url = "https://accounts.hubspaceconnect.com/auth/realms/thd/login-actions/authenticate?session_code="+ session_code + "&execution=" + execution + "&client_id=hubspace_android&tab_id=" + tab_id

        auth_header = {
            "Content-Type": "application/x-www-form-urlencoded",
            "user-agent": "Mozilla/5.0 (Linux; Android 7.1.1; Android SDK built for x86_64 Build/NYC) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36",
        }

        auth_data = {        
            "username":     self._username,
            "password":     self._password,
            "credentialId":"", 
        }

        headers = {}
        r = requests.post(auth_url, data=auth_data, headers=auth_header,cookies=r.cookies.get_dict(),allow_redirects = False)
        r.close()
        #print("first headers")
        #print(r.headers)
        location= r.headers.get('location')

        session_state = re.search('session_state=(.+?)&code', location).group(1)
        code = re.search('&code=(.+?)$', location).group(1)

        auth_url = "https://accounts.hubspaceconnect.com/auth/realms/thd/protocol/openid-connect/token"

        auth_header = {
            "Content-Type": "application/x-www-form-urlencoded",
            "user-agent": "Dart/2.15 (dart:io)",
            "host":"accounts.hubspaceconnect.com",
        }

        auth_data = {        
            "grant_type":    "authorization_code",
            "code": code ,
            "redirect_uri" : "hubspace-app://loginredirect",
            "code_verifier": code_verifier,
            "client_id":     "hubspace_android",
        }

        headers = {}
        r = requests.post(auth_url, data=auth_data, headers=auth_header)
        r.close()
        refresh_token = r.json().get('refresh_token')
        #print(refresh_token)
        return refresh_token


    def getAuthTokenFromRefreshToken(self):
        
        utcTime = self.getUTCTime()
        
        if self._last_token is not None and ((utcTime - self._last_token_time ) < self._token_duration) :
            #_LOGGER.debug("Resuse Token")
            return self._last_token
        
        #_LOGGER.debug("Get New Token")
        auth_url = "https://accounts.hubspaceconnect.com/auth/realms/thd/protocol/openid-connect/token"
        
        auth_header = {
            "Content-Type": "application/x-www-form-urlencoded",
            "user-agent": "Dart/2.15 (dart:io)",
            "host":"accounts.hubspaceconnect.com",
        }

        auth_data = {        
            "grant_type":    "refresh_token",
            "refresh_token": self._refresh_token,
            "scope": "openid email offline_access profile",
            "client_id":     "hubspace_android",
        }

        headers = {}
        r = requests.post(auth_url, data=auth_data, headers=auth_header)
        r.close()
        token = r.json().get('id_token')
        self._last_token = token
        self._last_token_time = utcTime
        
        return token

    def getAccountId(self):

        token = self.getAuthTokenFromRefreshToken()
        auth_url = "https://api2.afero.net/v1/users/me"

        auth_header = {
            "user-agent": "Dart/2.15 (dart:io)",
            "host": "api2.afero.net",
            "accept-encoding": "gzip",
            "authorization": "Bearer " + token,
        }

        auth_data = {}
        headers = {}
        r = requests.get(auth_url, data=auth_data, headers=auth_header)
        r.close()
        accountId = r.json().get('accountAccess')[0].get('account').get('accountId')
        return accountId

    def getChildId(self,deviceName):
        
        token = self.getAuthTokenFromRefreshToken()
        
        auth_header = {
            "user-agent": "Dart/2.15 (dart:io)",
            "host": "semantics2.afero.net",
            "accept-encoding": "gzip",
            "authorization": "Bearer " + token,
        }

        auth_url = "https://api2.afero.net/v1/accounts/" + self._accountId + "/metadevices?expansions=state"

        auth_data = {}
        headers = {}
        r = requests.get(auth_url, data=auth_data, headers=auth_header)
        r.close()
        child = None
        model = None
        deviceId = None
        
        for lis in r.json():
            for key,val in lis.items():
                if key == 'friendlyName' and val == deviceName:
                    #print(key, val)
                    _LOGGER.debug('Printing Possible Error')
                    _LOGGER.debug(lis)
                    child = lis.get('id')
                    deviceId = lis.get('deviceId')
                    model = lis.get('description').get('device').get('model')
                    return child,model,deviceId
                    
        return child,model,deviceId


    def getState(self,child,desiredStateName):

        state = None
        
        token = self.getAuthTokenFromRefreshToken()
        
        auth_header = {
            "user-agent": "Dart/2.15 (dart:io)",
            "host": "semantics2.afero.net",
            "accept-encoding": "gzip",
            "authorization": "Bearer " + token,
        }
        auth_url = "https://api2.afero.net/v1/accounts/" + self._accountId + "/metadevices/" + child + "/state"
        auth_data = {}
        headers = {}

        r = requests.get(auth_url, data=auth_data, headers=auth_header)
        r.close()
        for lis in r.json().get('values'):
            for key,val in lis.items():
                if key == 'functionClass' and val == desiredStateName:
                    state = lis.get('value')

        #print(desiredStateName + ": " + state)
        return state
    
    def getStateInstance(self,child,desiredStateName,desiredFunctionInstance):

        state = None
        
        token = self.getAuthTokenFromRefreshToken()
        
        auth_header = {
            "user-agent": "Dart/2.15 (dart:io)",
            "host": "semantics2.afero.net",
            "accept-encoding": "gzip",
            "authorization": "Bearer " + token,
        }
        auth_url = "https://api2.afero.net/v1/accounts/" + self._accountId + "/metadevices/" + child + "/state"
        auth_data = {}
        headers = {}

        r = requests.get(auth_url, data=auth_data, headers=auth_header)
        r.close()
        for lis in r.json().get('values'):
            for key,val in lis.items():
                if key == 'functionClass' and val == desiredStateName and lis.get('functionInstance') == desiredFunctionInstance :
                    state = lis.get('value')

        #print(desiredStateName + ": " + state)
        return state
        
    def getDebugInfo(self,child):

        state = None
        
        token = self.getAuthTokenFromRefreshToken()
        
        auth_header = {
            "user-agent": "Dart/2.15 (dart:io)",
            "host": "semantics2.afero.net",
            "accept-encoding": "gzip",
            "authorization": "Bearer " + token,
        }
        auth_url = "https://api2.afero.net/v1/accounts/" + self._accountId + "/metadevices/" + child + "/state"
        auth_data = {}
        headers = {}

        r = requests.get(auth_url, data=auth_data, headers=auth_header)
        r.close()
        return r.json()
        
    def getPowerState(self,child):
        return self.getState(child,"power")

    def setState(self,child,desiredStateName,state,needPrimary=False):

        
        token = self.getAuthTokenFromRefreshToken()
        
        
        auth_data = {}
        headers = {}
        
        utc_time = self.getUTCTime()
        payload = {
            "metadeviceId": str(child),
            "values": [
                {
                    "functionClass": desiredStateName,
                    "lastUpdateTime": utc_time,
                    "value": state
                }
            ]
        }
        
        if needPrimary:
            payload["values"][0]["functionInstance"] = "primary"
        
        auth_header = {
            "user-agent": "Dart/2.15 (dart:io)",
            "host": "semantics2.afero.net",
            "accept-encoding": "gzip",
            "authorization": "Bearer " + token,
            "content-type": "application/json; charset=utf-8",
        }


        auth_url = "https://api2.afero.net/v1/accounts/" + self._accountId + "/metadevices/" + child + "/state"
        r = requests.put(auth_url, json=payload, headers=auth_header)
        r.close()
        for lis in r.json().get('values'):
            for key,val in lis.items():
                if key == 'functionClass' and val == desiredStateName:
                    state = lis.get('value')

        #print(desiredStateName + ": " + state)
        return state
        
    def setStateInstance(self,child,desiredStateName,desiredFunctionInstance,state):

        
        token = self.getAuthTokenFromRefreshToken()
        
        
        auth_data = {}
        headers = {}
        
        utc_time = self.getUTCTime()
        payload = {
            "metadeviceId": str(child),
            "values": [
                {
                    "functionClass": desiredStateName,
                    "functionInstance": desiredFunctionInstance,
                    "lastUpdateTime": utc_time,
                    "value": state
                }
            ]
        }
        
        
        auth_header = {
            "user-agent": "Dart/2.15 (dart:io)",
            "host": "semantics2.afero.net",
            "accept-encoding": "gzip",
            "authorization": "Bearer " + token,
            "content-type": "application/json; charset=utf-8",
        }


        auth_url = "https://api2.afero.net/v1/accounts/" + self._accountId + "/metadevices/" + child + "/state"
        r = requests.put(auth_url, json=payload, headers=auth_header)
        r.close()
        
        
    def setPowerState(self,child,state,needPrimary=False):
        self.setState(child,"power",state,needPrimary)
        
     
    async def getConclave(self):

        
        token = self.getAuthTokenFromRefreshToken()
        
        
        auth_data = {}
        headers = {}
        
        
        payload = {
            "softHub": 'false',
            "user": 'true'
        }
        
        auth_header = {
            "user-agent": "Dart/2.15 (dart:io)",
            "host": "api2.afero.net",
            "accept-encoding": "gzip",
            "authorization": "Bearer " + token,
            "content-type": "application/json; charset=utf-8",
        }


        auth_url = "https://api2.afero.net/v1/accounts/" + self._accountId    + "/conclaveAccess"
        r = requests.post(auth_url, json=payload, headers=auth_header)
        r.close()
        #print(json.dumps(r.json(), indent=4, sort_keys=True))
        host = r.json().get('conclave').get('host')
        port = r.json().get('conclave').get('port')
        token = r.json().get('tokens')[0].get('token')
        expiresTimestamp = r.json().get('tokens')[0].get('expiresTimestamp')
        
    def setRGB(self,child,r,g,b):
        # assume r,g,b 0-255
        state = {'color-rgb': { 'r': r, 'b': b, 'g': g}}
        self.setState(child,'color-rgb',state)
        self.setState(child,'color-mode','color')
        
    def getRGB(self,child):
        state = self.getState(child,'color-rgb')
        r = int(state.get('color-rgb').get('r'))
        g = int(state.get('color-rgb').get('g'))
        b = int(state.get('color-rgb').get('b'))
        return (r,g,b)
