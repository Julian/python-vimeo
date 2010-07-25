#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
The MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

"""
Python module to interact with Vimeo through its API (version 2)
"""
import urlparse

import oauth2

# by default expects to find your key and secret in settings.py (django)
# change this if they're someplace else (expecting strings for both)
from settings import VIMEO_KEY, VIMEO_SECRET

# oAuth URLs
REQUEST_TOKEN_URL = 'http://vimeo.com/oauth/request_token'
ACCESS_TOKEN_URL = 'http://vimeo.com/oauth/access_token'
AUTHORIZATION_URL = 'http://vimeo.com/oauth/authorize'
# Vimeo API request URLs
API_REST_URL = 'http://vimeo.com/api/rest/v2/'
API_V2_CALL_URL = 'http://vimeo.com/api/v2/'

class VimeoAPIError(Exception):
    pass

class VimeoClient(object):
    """
    For a list of available API methods, see the Vimeo Advanced API
    documentation, including what parameters are available for each method.

    In addition, each method can take an additional parameter:

        process (default: True):
            If False, returns the unprocessed response along with the response
            headers for you to do your own parsing and processing. Respects the
            default_response_format attribute or the "format" parameter.

    For authentication steps, consult the oauth2 documentation and the Vimeo
    API documentation for the steps needed to get the right tokens. You will
    want to use this class' .client object (an oauth2.Client instance which is
    instantiated with a Consumer instance from your key and secret) to make
    your requests.

    If you already have an authorization token and secret, pass
    """
    def __init__(self, key=VIMEO_KEY, secret=VIMEO_SECRET, format="xml",
                 token=None, token_secret=None, verifier=None):

        self.default_response_format = format

        self.key = key
        self.secret = secret
        self.consumer = oauth2.Consumer(self.key, self.secret)

        # any request made with the .client attr below is automatically
        # signed, so this won't be needed unless you want to make a manual
        # request for some reason
        self.signature_method = oauth2.SignatureMethod_HMAC_SHA1()

        if token and token_secret:
            self.token = oauth2.Token(token, token_secret)
        else:
            self.token = None

        self.client = oauth2.Client(self.consumer, self.token)

    def __getattr__(self, name):
        # Only do virtual methods for method names that are part of the API
        if not name.startswith("vimeo"):
            raise AttributeError(
                "No attribute found with the name {0}.".format(name))

        def _do_vimeo_call(**params):
            from urllib import urlencode

            params['method'] = name.replace("_", ".")
            params.setdefault("format", self.default_response_format)

            request_uri = "{api_url}?&{params}".format(api_url=API_REST_URL,
                                                      params=urlencode(params))
            additional_headers = {"User-agent" : "python-vimeo"}

            response_headers, response_content = self.client.request(
                                                   uri=request_uri,
                                                   headers=additional_headers)

            # call the appropriate process method if process is True (default)
            # and we have an appropriate processor method
            process_function = "_process_{0}".format(params["format"])
            if params.get("process", True):
                try:
                    return getattr(self, process_function)(response_content)
                except AttributeError:
                    pass
            return self._no_processing(response_headers, response_content)
        return _do_vimeo_call

    # no @property.setter in 2.5 means manual property creation...
    def _get_default_response_format(self):
        """
        Defines the default response format. The Vimeo API default is xml.

        Other choices are json (recommended), jsonp, or php. See the API
        documentation for details.

        Processed formats:
            json:       returns as a python dict containing the requested info
            xml:        returns as an ElementTree

        Unprocessed formats:
            jsonp
            php

        Note: No additional verification is done to make sure that your format
        is one that is supported by the API.

        The global default for your client can also be overriden on a
        per-method basis by passing in a "format" parameter (per the API docs).
        """
        return self._default_response_format

    def _set_default_response_format(self, value):
        self._default_response_format = value.lower()

    default_response_format = property(_get_default_response_format, _set_default_response_format)

    def _process_xml(self, response):
        from xml.etree import ElementTree
        return ElementTree.fromstring(response)

    def _process_json(self, response):
        import json

        response = json.loads(response)

        if response["stat"] == "fail":
            raise VimeoAPIError(response["err"]["msg"])
        return response

    def _no_processing(self, response_headers, response_content):
        return response_headers, response_content

    #### 3-legged oAuth
    def _is_success(self, response_headers):
        if response_headers["status"] != "200":
            raise VimeoAPIError(
                    "Invalid response {0}".format(response_headers["status"]))
        return True

    def _get_new_token(self, request_url, *args, **kwargs):
        """
        Internal method that gets a new token from the request_url and sets it
        to self.token on success.
        """
        resp, content = self.client.request(request_url, *args, **kwargs)

        if self._is_success(resp):
            new_token = dict(urlparse.parse_qsl(content))
            self.token = oauth2.Token(new_token["oauth_token"],
                                      new_token["oauth_token_secret"])
            self.client = oauth2.Client(self.consumer, self.token)

    def get_request_token(self):
        """
        (oAuth Step 1)

        Gets a request token from the API.
        """
        self._get_new_token(REQUEST_TOKEN_URL)

    def get_authorization_url(self, permission="read"):
        """
        (oAuth Step 2a)

        Uses the request token received to build an authorization url which
        should be visited by the user to grant permission to their account.
        """
        if not self.token:
            self.get_request_token()
        return "{0}?oauth_token={1}&permission={2}".format(AUTHORIZATION_URL,
                                                           self.token.key,
                                                           permission)

    def set_verifier(self, verifier):
        """
        (oAuth Step 2b)

        Should be called with the user's verifier string that is displayed
        after granting permission at the authorization url.
        """
        if not self.token:
            raise VimeoAPIError("No request token present.")
        self.token.set_verifier(verifier)
        self.client = oauth2.Client(self.consumer, self.token)

    def get_access_token(self):
        """
        (oAuth Step 3)

        Gets an access token from the API. The instance should already have
        received a request token and used the get_authorization_url and
        set_verifier methods.

        Returns the new access token in addition to saving it to self.token, in
        case it needs to be saved in another location like a token database.
        """
        if not self.token:
            raise VimeoAPIError("No request token present.")
        self._get_new_token(ACCESS_TOKEN_URL)
        return self.token
