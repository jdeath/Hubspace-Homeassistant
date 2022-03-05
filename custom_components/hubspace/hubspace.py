import requests
import json
import re
import calendar
import datetime
import hashlib
import base64
import os
import asyncio

def getCodeVerifierAndChallenge():
    code_verifier = base64.urlsafe_b64encode(os.urandom(40)).decode('utf-8')
    code_verifier = re.sub('[^a-zA-Z0-9]+', '', code_verifier)
    code_challenge = hashlib.sha256(code_verifier.encode('utf-8')).digest()
    code_challenge = base64.urlsafe_b64encode(code_challenge).decode('utf-8')
    code_challenge = code_challenge.replace('=', '')
    return code_challenge,code_verifier

def getRefreshCode(userName,passWord):
    URL = "https://accounts.hubspaceconnect.com/auth/realms/thd/protocol/openid-connect/auth"
    
    # These are linked    
    #code_challenge = 'JDdBWmN__LJfqDHw9RxD-Ha_0Dj9fmnYIMiq2TGc8sc'
    #code_verifier = 'QUqzUOTYWzMMRdCsYIntMix_s5p9yBW0fTZStCzWrO0XbDDRX3~r86DYR8IBt64HukWdZm9ZJbA8UJr48cN_R9m85X.pWW5LiVKFoyTSkhQdha3tAFPQNjOjf0xqRtZk'
    [code_challenge,code_verifier] = getCodeVerifierAndChallenge()
    
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
        "username":     userName,
        "password":     passWord,
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


def getAuthTokenFromRefreshToken(refresh_token):
    auth_url = "https://accounts.hubspaceconnect.com/auth/realms/thd/protocol/openid-connect/token"

    auth_header = {
        "Content-Type": "application/x-www-form-urlencoded",
        "user-agent": "Dart/2.15 (dart:io)",
        "host":"accounts.hubspaceconnect.com",
    }

    auth_data = {        
        "grant_type":    "refresh_token",
        "refresh_token": refresh_token,
        "scope": "openid email offline_access profile",
        "client_id":     "hubspace_android",
    }

    headers = {}
    r = requests.post(auth_url, data=auth_data, headers=auth_header)
    r.close()
    token = r.json().get('id_token')
    return token

def getAccountId(refresh_token):

    token = getAuthTokenFromRefreshToken(refresh_token)
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

def getChildId(refresh_token,accountId,deviceName):
    
    token = getAuthTokenFromRefreshToken(refresh_token)
    
    auth_header = {
        "user-agent": "Dart/2.15 (dart:io)",
        "host": "semantics2.afero.net",
        "accept-encoding": "gzip",
        "authorization": "Bearer " + token,
    }

    auth_url = "https://api2.afero.net/v1/accounts/" + accountId + "/metadevices?expansions=state"

    auth_data = {}
    headers = {}
    r = requests.get(auth_url, data=auth_data, headers=auth_header)
    r.close()
    child = None

    for lis in r.json():
        for key,val in lis.items():
            if key == 'friendlyName' and val == deviceName:
                #print(key, val)
                child = lis.get('id')
                deviceId = lis.get('deviceId')

    return child


def getState(refresh_token,accountId,child,desiredStateName):

    state = None
    
    token = getAuthTokenFromRefreshToken(refresh_token)
    
    auth_header = {
        "user-agent": "Dart/2.15 (dart:io)",
        "host": "semantics2.afero.net",
        "accept-encoding": "gzip",
        "authorization": "Bearer " + token,
    }
    auth_url = "https://api2.afero.net/v1/accounts/" + accountId + "/metadevices/" + child + "/state"
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

def getPowerState(refresh_token,accountId,child):
    return getState(refresh_token,accountId,child,"power")

def setState(refresh_token,accountId,child,desiredStateName,state):

    
    token = getAuthTokenFromRefreshToken(refresh_token)
    
    
    auth_data = {}
    headers = {}
    
    date = datetime.datetime.utcnow()
    utc_time = calendar.timegm(date.utctimetuple()) * 1000
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
    
    auth_header = {
        "user-agent": "Dart/2.15 (dart:io)",
        "host": "semantics2.afero.net",
        "accept-encoding": "gzip",
        "authorization": "Bearer " + token,
        "content-type": "application/json; charset=utf-8",
    }


    auth_url = "https://api2.afero.net/v1/accounts/" + accountId + "/metadevices/" + child + "/state"
    r = requests.put(auth_url, json=payload, headers=auth_header)
    r.close()
    for lis in r.json().get('values'):
        for key,val in lis.items():
            if key == 'functionClass' and val == desiredStateName:
                state = lis.get('value')

    #print(desiredStateName + ": " + state)
    return state

def setPowerState(refresh_token,accountId,child,state):
    setState(refresh_token,accountId,child,"power",state)
    
 
async def getConclave(refresh_token,accountId):

    
    token = getAuthTokenFromRefreshToken(refresh_token)
    
    
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


    auth_url = "https://api2.afero.net/v1/accounts/" + accountId + "/conclaveAccess"
    r = requests.post(auth_url, json=payload, headers=auth_header)
    r.close()
    #print(json.dumps(r.json(), indent=4, sort_keys=True))
    host = r.json().get('conclave').get('host')
    port = r.json().get('conclave').get('port')
    token = r.json().get('tokens')[0].get('token')
    expiresTimestamp = r.json().get('tokens')[0].get('expiresTimestamp')
    
    # print(host)
    # print(port)
    # import websockets,ssl
    # header = {"login":{"channelId":"df69b232-c564-4121-bc22-c8b6540d3920","accessToken":token,"type":"android","version":"1.0.0","protocol":2,"trace":True}}
    
    # print(json.dumps(header))
    
    # context = ssl.SSLContext(ssl.PROTOCOL_TLS)
    # async with websockets.connect("wss://conclave-stream1.afero.net:443",ssl=context) as websocket:
        # await websocket.send('{}')
        # websocket.recv()
        # await websocket.send(json.dumps(header))
        # await websocket.recv()
    # import ssl
    # import websockets
    
    # context = ssl.SSLContext(ssl.PROTOCOL_TLS)
    # websockets.connect("wss://" + host + ":" + str(port),ssl=context)
    # websockets.send('{}')
    # websockets.send(json.dumps(header).encode())
    
    # data = websockets.recv()
    # print(data)
    # context = ssl.SSLContext(ssl.PROTOCOL_TLS)
    # s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # s_sock = context.wrap_socket(s, server_hostname=host)
    # s_sock.connect((host, port))
   
    # s_sock.send( '{}'.encode())
    # data = s_sock.recv(1024)
    # s_sock.send( json.dumps(header).encode())
    # while True:
        # data = s_sock.recv(1024)
        # if len(data) > 0 :
            # print (data.decode('unicode_escape'))

    # s_sock.close()
    
    ###############3
    # reader, writer = await asyncio.open_connection(host, port)
    
    # writer.write( '{}'.encode())
    # writer.write( json.dumps(header).encode())
    # await writer.drain()

    # while True:
        # data = await reader.read(1024)
        # print(f'Received: {data.decode()!r}')

    # print('Close the connection')
    # writer.close()
    # await writer.wait_closed()
    
# def test_auth_token(token):
    # header="Authorization: Bearer " + str(token)
    # conn = create_connection("ws://conclave-stream1.afero.net:443"+ '/'+ container.uuid, header)
    # result = conn.recv()
    # assert result is not None
    