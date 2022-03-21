""" Library for interacting with the Hubspace API. """
import requests
import re
import calendar
import datetime
import hashlib
import base64
import os
import logging

_LOGGER = logging.getLogger(__name__)

AUTH_SESSION_URL = (
    "https://accounts.hubspaceconnect.com/auth/realms/thd/protocol/openid-connect/auth"
)
AUTH_URL = (
    "https://accounts.hubspaceconnect.com/auth/realms/thd/login-actions/authenticate"
)
TOKEN_URL = (
    "https://accounts.hubspaceconnect.com/auth/realms/thd/protocol/openid-connect/token"
)
CLIENT_ID = "hubspace_android"
REDIRECT_URI = "hubspace-app://loginredirect"
USER_AGENT = "Dart/2.15 (dart:io)"
TOKEN_HEADER = {
    "Content-Type": "application/x-www-form-urlencoded",
    "user-agent": USER_AGENT,
    "host": "accounts.hubspaceconnect.com",
}
AFERO_HOST = "api2.afero.net"
AFERO_SEMANTICS_HOST = "semantics2.afero.net"
AFERO_API = "https://api2.afero.net/v1"


def get_code_verifier_and_challenge():
    code_verifier = base64.urlsafe_b64encode(os.urandom(40)).decode("utf-8")
    code_verifier = re.sub("[^a-zA-Z0-9]+", "", code_verifier)
    code_challenge = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    code_challenge = base64.urlsafe_b64encode(code_challenge).decode("utf-8")
    code_challenge = code_challenge.replace("=", "")
    return code_challenge, code_verifier


def get_auth_session():
    [code_challenge, code_verifier] = get_code_verifier_and_challenge()

    # defining a params dict for the parameters to be sent to the API
    auth_session_params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "scope": "openid offline_access",
    }

    # sending get request and saving the response as response object
    auth_session_response = requests.get(
        url=AUTH_SESSION_URL, params=auth_session_params
    )
    auth_session_response.close()

    session_code = re.search("session_code=(.+?)&", auth_session_response.text).group(1)
    execution = re.search("execution=(.+?)&", auth_session_response.text).group(1)
    tab_id = re.search("tab_id=(.+?)&", auth_session_response.text).group(1)
    auth_cookies = auth_session_response.cookies.get_dict()
    return [session_code, execution, tab_id, auth_cookies, code_verifier]


def get_refresh_token(username, password):
    [session_code, execution, tab_id, auth_cookies, code_verifier] = get_auth_session()

    auth_url = f"{AUTH_URL}?client_id={CLIENT_ID}&session_code={session_code}&execution={execution}&tab_id={tab_id}"
    auth_header = {
        "Content-Type": "application/x-www-form-urlencoded",
        "user-agent": "Mozilla/5.0 (Linux; Android 7.1.1; Android SDK built for x86_64 Build/NYC) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36",
    }
    auth_data = {
        "username": username,
        "password": password,
        "credentialId": "",
    }
    auth_response = requests.post(
        auth_url,
        data=auth_data,
        headers=auth_header,
        cookies=auth_cookies,
        allow_redirects=False,
    )
    auth_response.close()

    location = auth_response.headers.get("location")
    code = re.search("&code=(.+?)$", location).group(1)

    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "code_verifier": code_verifier,
        "client_id": CLIENT_ID,
    }
    token_response = requests.post(TOKEN_URL, data=token_data, headers=TOKEN_HEADER)
    token_response.close()
    return token_response.json().get("refresh_token")


def get_auth_token(refresh_token):
    token_data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "scope": "openid email offline_access profile",
        "client_id": CLIENT_ID,
    }
    token_response = requests.post(TOKEN_URL, data=token_data, headers=TOKEN_HEADER)
    token_response.close()
    return token_response.json().get("id_token")


def get_account_id(auth_token):
    account_url = f"{AFERO_API}/users/me"
    account_header = {
        "user-agent": USER_AGENT,
        "host": AFERO_HOST,
        "accept-encoding": "gzip",
        "authorization": f"Bearer {auth_token}",
    }
    account_data = {}
    account_response = requests.get(
        account_url, data=account_data, headers=account_header
    )
    account_response.close()
    return (
        account_response.json().get("accountAccess")[0].get("account").get("accountId")
    )


def get_children(auth_token, account_id):
    children_url = f"{AFERO_API}/accounts/{account_id}/metadevices?expansions=state"
    children_header = {
        "user-agent": USER_AGENT,
        "host": AFERO_SEMANTICS_HOST,
        "accept-encoding": "gzip",
        "authorization": f"Bearer {auth_token}",
    }
    children_data = {}
    children_response = requests.get(
        children_url, data=children_data, headers=children_header
    )
    children_response.close()

    return children_response.json()


def parse_state(
    device: dict,
    function_class: str or None = None,
    function_instance: str or None = None,
    default_value=None,
    value_parser=lambda x: x,
):
    try:
        for state_value in device["values"]:
            if (
                function_class is None or state_value["functionClass"] == function_class
            ) and (
                function_instance is None
                or state_value["functionInstance"] == function_instance
            ):
                return value_parser(state_value["value"])
    except (KeyError, NameError, AttributeError) as error:
        _LOGGER.warning(
            "Could not fetch '%s':'%s' for Hubspace device '%s': %s",
            function_class,
            function_instance,
            device.get("id", "unknown"),
            error,
        )
    return default_value


def get_state(
    refresh_token, account_id, child, function_class=None, function_instance=None
):
    auth_token = get_auth_token(refresh_token)
    state_url = f"{AFERO_API}/accounts/{account_id}/metadevices/{child}/state"
    state_header = {
        "user-agent": USER_AGENT,
        "host": AFERO_SEMANTICS_HOST,
        "accept-encoding": "gzip",
        "authorization": f"Bearer {auth_token}",
    }
    state_data = {}
    state_response = requests.get(state_url, data=state_data, headers=state_header)
    state_response.close()
    if function_class is None:
        return state_response.json()
    return parse_state(state_response.json(), function_class, function_instance)


def set_state(refresh_token, account_id, child, values=[]):
    auth_token = get_auth_token(refresh_token)
    date = datetime.datetime.utcnow()
    utc_time = calendar.timegm(date.utctimetuple()) * 1000
    state_payload = {
        "metadeviceId": str(child),
        "values": [value | {"lastUpdateTime": utc_time} for value in values],
    }
    state_url = f"{AFERO_API}/accounts/{account_id}/metadevices/{child}/state"
    state_header = {
        "user-agent": USER_AGENT,
        "host": AFERO_SEMANTICS_HOST,
        "accept-encoding": "gzip",
        "authorization": f"Bearer {auth_token}",
        "content-type": "application/json; charset=utf-8",
    }
    state_response = requests.put(state_url, json=state_payload, headers=state_header)
    state_response.close()
    return state_response.json()
