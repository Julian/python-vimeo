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

import oauth2

# by default expects to find your key and secret in settings.py (django)
# change this if they're someplace else (expecting strings for both)
from settings import VIMEO_KEY, VIMEO_SECRET

DEBUG = False

# oAuth URLs
REQUEST_TOKEN_URL = 'http://vimeo.com/oauth/request_token'
ACCESS_TOKEN_URL = 'http://vimeo.com/oauth/access_token'
AUTHORIZATION_URL = 'http://vimeo.com/oauth/authorize'
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
            If False, returns unprocessed response (in the format given, or 
            the default) for you to do your own parsing and processing.

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
        self.signature_method = oauth2.SignatureMethod_HMAC_SHA1()

        if token and token_secret:
            self.token = oauth2.Token(token, token_secret)
        else:
            self.token = None

        self.client = oauth2.Client(self.consumer, self.token)

    def __getattr__(self, name):
        def _do_vimeo_call(**parameters):
            from urllib import urlencode

            parameters['method'] = name.replace("_", ".")
            parameters.setdefault("format", self.default_response_format)

            request_uri = "{api_url}?&{params}".format(api_url=API_REST_URL,
                                                       params=urlencode(parameters))
            response_headers, response_content = self.client.request(uri=request_uri, 
                                                   headers={'User-agent' : 'python-vimeo'})

            # call the appropriate process method
            if parameters.get("process", True):
                return getattr(self, "_process_{response_format}".format(response_format=parameters["format"]))(response_content)
            return request
        return _do_vimeo_call

    # no @property.setter in 2.5 means manual property creation...
    def _get_default_response_format(self):
        """
        Defines the default response format. By default, xml. 
        
        Other choices are json (recommended), jsonp, or php. See the API
        documentation for details. 
        
        Note: this method doesn't verify that the format is one of the available
        API formats, so be sure that the format that is being set is supported.

        This can be also be overriden by passing a "format" parameter to your method.
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

    def _process_jsonp(self, response):
        raise NotImplementedError("JSONP response parser not yet implemented.")

    def _process_php(self, response):
        raise NotImplementedError("PHP response parser not yet implemented.")
