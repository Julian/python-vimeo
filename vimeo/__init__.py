#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Python module to interact with Vimeo through its API (version 2)
"""

import logging
import time
import urlparse
from urllib import urlencode

import oauth2

# by default expects to find your key and secret in settings.py (django)
# change this if they're someplace else (expecting strings for both)
try:
    from settings import VIMEO_KEY, VIMEO_SECRET
except ImportError:
    VIMEO_KEY, VIMEO_SECRET = None, None

# oAuth URLs
REQUEST_TOKEN_URL = "http://vimeo.com/oauth/request_token"
ACCESS_TOKEN_URL = "http://vimeo.com/oauth/access_token"
AUTHORIZATION_URL = "http://vimeo.com/oauth/authorize"
# Vimeo API request URLs
API_REST_URL = "http://vimeo.com/api/rest/v2/"
API_V2_CALL_URL = "http://vimeo.com/api/v2/"

# Logging setup
LOG = False
if LOG:
    STAT_LOG_FILENAME = "logs/stats.log"
    logging.basicConfig(filename=STAT_LOG_FILENAME, level=logging.DEBUG)

class VimeoAPIError(Exception):
    pass

class VimeoClient(object):
    """
    For a list of available API methods, see the Vimeo Advanced API
    documentation, including what parameters are available for each method.

    In addition, each method can take an additional parameter:

        process (default: True):
            If False, returns a tuple with the response headers and unprocessed
            response content to do your own parsing on. Respects the object's
            default_response_format attribute or the "format" parameter.

    For three legged authentication, use the get_request_token,
    get_authentication_url, set_verifier, and get_access_token methods.

    If you already have an authorization token and secret, pass it in to the
    initializer.

    By default, this client will cache API requests for 120 seconds. To
    override this setting, pass in a different cache_timeout parameter (in
    seconds), or to disable caching, set cache_timeout to 0.
    """

    _CLIENT_HEADERS = {"User-agent" : "python-vimeo"}

    def __init__(self, key=VIMEO_KEY, secret=VIMEO_SECRET, format="xml",
                 token=None, token_secret=None, verifier=None,
                 cache_timeout=120):

        # memoizing
        self._cache = {}
        self._timeouts = {}
        self.cache_timeout = cache_timeout

        self.default_response_format = format

        self.key = key
        self.secret = secret
        self.consumer = oauth2.Consumer(self.key, self.secret)

        # any request made with the .client attr below is automatically
        # signed, so this won't be needed unless you want to make a manual
        # request for whatever reason
        self.signature_method = oauth2.SignatureMethod_HMAC_SHA1()

        if token and token_secret:
            self.token = oauth2.Token(token, token_secret)
        else:
            self.token = None

        self.client = oauth2.Client(self.consumer, self.token)

    def __getattr__(self, name):
        """
        Makes virtual methods call the API if they start with "vimeo_", which
        is the parent namespace of all of the API methods.

        Also allows leaving off the vimeo_ for convenience when calling a
        method, but if it's a newly added group of methods you may need to use
        the full syntax.
        """
        # anything on this list can have its methods called without adding
        # vimeo_ to the beginning (so videos_getInfo works, for example)
        KNOWN_API_GROUPS = ("activity", "albums", "channels", "contacts",
                            "groups", "oauth", "people", "test", "videos")

        if not name.startswith("vimeo"):
            # convenience method?
            if any(name.startswith(prefix) for prefix in KNOWN_API_GROUPS):
                return getattr(self, "vimeo_" + name)
            # otherwise, this probably isn't an API method
            raise AttributeError(
                "No attribute found with the name {0}.".format(name))

        if LOG:
            logging.info(name)

        # memoize cleanup
        call_time = time.time()
        # no iteritems, we're changing the dict
        for k, v in self._timeouts.items():
            if call_time - v > self.cache_timeout:
                try:
                    del self._cache[k]
                except KeyError:
                    pass
                del self._timeouts[k]

        def _do_vimeo_call(**params):
            # change these before we memoize
            params.setdefault("format", self.default_response_format)

            # memoize
            key = (name, frozenset(params.items()))
            self._timeouts.setdefault(key, call_time)
            if key in self._cache:
                return self._cache[key]

            # we want to change these after we memoize, before we call the API
            process = params.pop("process", True)
            params["method"] = name.replace("_", ".")

            request_uri = "{api_url}?&{params}".format(api_url=API_REST_URL,
                                                      params=urlencode(params))
            response_headers, response_content = self.client.request(
                                                uri=request_uri,
                                                headers=self._CLIENT_HEADERS)

            # call the appropriate process method if process is True (default)
            # and we have an appropriate processor method
            process_function = "_process_{0}".format(params["format"])
            if process:
                try:
                    return self._cache.setdefault(key,
                             getattr(self, process_function)(response_content))
                except AttributeError:
                    pass
            return self._cache.setdefault(key,
                                          self._no_processing(response_headers,
                                                             response_content))
        return _do_vimeo_call

    def __repr__(self):
        tokened = "T" if self.token else "Unt"
        return "<{0}okened Vimeo API Client ({1})>".format(tokened,
                                         self.default_response_format.upper())

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
        # import chain taken from lxml docs
        try:
            from lxml import etree
        except ImportError:
            try:
                import xml.etree.cElementTree as etree
            except ImportError:
                try:
                    import xml.etree.ElementTree as etree
                except ImportError:
                    try:
                        import cElementTree as etree
                    except ImportError:
                        try:
                            import elementtree.ElementTree as etree
                        except ImportError:
                            raise ImportError("ElementTree not found.")
        return etree.fromstring(response)

    def _process_json(self, response):
        import json
        response = json.loads(response)

        status = response.pop("stat")
        generated_in = response.pop("generated_in")

        if LOG:
            logging.info(status)
            logging.info(generated_in)

        if status == "fail":
            raise VimeoAPIError(response["err"]["msg"])
        # response should only have the content we want now in a nested dict
        if len(response) is not 1:
            # uh oh... this shouldn't have happened, hopefully the caller can
            # deal with it
            if LOG:
                logging.error(response.keys())
            return response
        _, content = response.popitem()
        return content

    def _no_processing(self, response_headers, response_content):
        return response_headers, response_content

    def flush_cache(self):
        """
        Manually clear the response cache.
        """
        self._cache = {}
        self._timeouts = {}

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

    #### uploading convenience POSTer
    def start_upload(self, *args, **kwargs):
        from convenience import VimeoUploader

        quota = self.vimeo_videos_upload_getQuota(format="json")
        ticket = self.vimeo_videos_upload_getTicket(format="json")
        return VimeoUploader(vimeo_client=self, ticket=ticket, quota=quota,
                             *args, **kwargs)
