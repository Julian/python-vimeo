#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2009 Marc Poulhiès
#
# Python module for Vimeo
# originaly part of 'plopifier'
#
# This is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Plopifier.  If not, see <http://www.gnu.org/licenses/>.


"""
Python module to interact with Vimeo through its API (version 2)
"""

import xml.etree.ElementTree as ET
import oauth.oauth as oauth

import urllib2

from urllib import urlencode

REQUEST_TOKEN_URL = 'http://vimeo.com/oauth/request_token'
ACCESS_TOKEN_URL = 'http://vimeo.com/oauth/access_token'
AUTHORIZATION_URL = 'http://vimeo.com/oauth/authorize'

API_REST_URL = 'http://vimeo.com/api/rest/v2/'
API_V2_CALL_URL = 'http://vimeo.com/api/v2/'

PORT = 80

HMAC_SHA1 = oauth.OAuthSignatureMethod_HMAC_SHA1()

DEBUG = True

class VimeoException(Exception):
    def __init__(self, msg):
        super(VimeoException, self).__init__(self)
        self.msg = msg
    
    def __str__(self):
        return self.msg

class VimeoOAuthClient(oauth.OAuthClient):
    """
    Class used for handling authenticated call to the API.
    """

    def __init__(self, key, secret,
                 server="vimeo.com", port=PORT, 
                 request_token_url=REQUEST_TOKEN_URL, 
                 access_token_url=ACCESS_TOKEN_URL, 
                 authorization_url=AUTHORIZATION_URL,
                 token=None,
                 token_secret=None,
                 verifier=None,
                 vimeo_config=None):
        """
        You need to give both key (consumer key) and secret (consumer secret).
        If you already have an access token (token+secret), you can use it
        by giving it through token and token_secret parameters.
        If not, then you need to call both get_request_token(), get_authorize_token_url() and 
        finally get_access_token().
        """

        self.opener = urllib2.build_opener()
        self.opener.addheaders = [('User-agent', 'python-vimeo')]

        self.key = key
        self.secret = secret
        self.server = server
        self.port = PORT
        self.request_token_url = request_token_url
        self.access_token_url = access_token_url
        self.authorization_url = authorization_url
        self.consumer = oauth.OAuthConsumer(self.key, self.secret)

        self.config = vimeo_config
        if self.config:
            try:
                token = self.config.get("auth", "token")
                token_secret = self.config.get("auth", "token_secret")
                verifier = self.config.get("auth", "verifier")
            except ConfigParser.NoSectionError, e:
                # not everything in config file. Simply skip
                pass

        if token and token_secret:
            self.token = oauth.OAuthToken(token, token_secret)
            self.token.set_verifier(verifier)
        else:
            self.token = None
        
    def __getattr__(self, name):
        def _do_vimeo_call(**parameters):
            parameters['method'] = name.replace("_", ".")
            oauth_request = oauth.OAuthRequest.from_consumer_and_token(self.consumer,
                                                                       token=self.token,
                                                                       http_method='GET',
                                                                       http_url=API_REST_URL,
                                                                       parameters=parameters)
            oauth_request.sign_request(HMAC_SHA1, self.consumer, self.token)
            return self.opener.open(oauth_request.to_url())
        return _do_vimeo_call

    def get_request_token(self):
        """
        Requests a request token and return it on success.
        """
        oauth_request = oauth.OAuthRequest.from_consumer_and_token(self.consumer, 
                                                                   http_url=self.request_token_url)
        oauth_request.sign_request(HMAC_SHA1, self.consumer, None)

        self.token = self._fetch_token(oauth_request)


    def get_authorize_token_url(self, permission='read'):
        """
        Returns a URL used to verify and authorize the application to access
        user's account. The pointed page should contain a simple 'password' that
        acts as the 'verifier' in oauth.
        """

        
        oauth_request = oauth.OAuthRequest.from_token_and_callback(token=self.token, 
                                                                   http_url=self.authorization_url)
        return oauth_request.to_url() + "&" + urlencode({"permission" : permission})


    def get_access_token(self, verifier):
        """
        Should be called after having received the 'verifier' from the authorization page.
        See 'get_authorize_token_url()' method.
        """

        self.token.set_verifier(verifier)
        oauth_request = oauth.OAuthRequest.from_consumer_and_token(self.consumer, 
                                                                   token=self.token, 
                                                                   verifier=verifier, 
                                                                   http_url=self.access_token_url)
        oauth_request.sign_request(HMAC_SHA1, self.consumer, self.token)
        self.token = self._fetch_token(oauth_request)
        return self.token

    def _fetch_token(self, oauth_request):
        """
        Sends a requests and interprets the result as a token string.
        """
        ans = self.opener.open(oauth_request.to_url()).read()
        return oauth.OAuthToken.from_string(ans)

    def _do_compute_vimeo_upload(self, endpoint, ticket_id):
        oauth_request = oauth.OAuthRequest.from_consumer_and_token(self.consumer,
                                                                   token=self.token,
                                                                   http_method='POST',
                                                                   http_url=endpoint,
                                                                   parameters={'ticket_id': ticket_id})
        oauth_request.sign_request(HMAC_SHA1, self.consumer, self.token)
        return oauth_request.parameters

    def do_upload(self, endpoint, ticket_id, filename, callback=None,use_progress=False):
        post_data = self._do_compute_vimeo_upload(endpoint, ticket_id)
        # make sure everything is string !
        post_data_l = [(k,str(v)) for (k,v) in post_data.items()]
        post_data_l.append(('file_data', (pycurl.FORM_FILE, filename)))
        self.curly.do_post_call(endpoint, post_data_l, use_progress, progress_callback=callback)

def _simple_request(url, format):
    if format != 'xml':
        raise VimeoException("Sorry, only 'xml' supported. '%s' was requested." %format)

    curly = curl.CurlyRequest()
    url = url %(format)
    ans = curly.do_request(url)

    if format == 'xml':
        return ET.fromstring(ans)

# TODO: class SimpleAPIRequester(object):
##
## User related call from the "Simple API".
## See : http://vimeo.com/api/docs/simple-api
##

def _user_request(user, info, format):
    url = API_V2_CALL_URL + '%s/%s.%%s' %(user,info)
    return _simple_request(url, format)

def user_info(user, format="xml"):
    """
    User info for the specified user
    """
    return _user_request(user, inspect.stack()[0][3][5:], format)


def user_videos(user, format="xml"):
    """
    Videos created by user
    """
    return _user_request(user, inspect.stack()[0][3][5:], format)

def user_likes(user, format="xml"):
    """
    Videos the user likes
    """
    return _user_request(user, inspect.stack()[0][3][5:], format)

def user_appears_in(user, format="xml"):
    """
    Videos that the user appears in
    """
    return _user_request(user, inspect.stack()[0][3][5:], format)

def user_all_videos(user, format="xml"):
    """
    Videos that the user appears in and created
    """
    return _user_request(user, inspect.stack()[0][3][5:], format)

def user_subscriptions(user, format="xml"):
    """
    Videos the user is subscribed to
    """
    return _user_request(user, inspect.stack()[0][3][5:], format)

def user_albums(user, format="xml"):
    """
    Albums the user has created
    """
    return _user_request(user, inspect.stack()[0][3][5:], format)

def user_channels(user, format="xml"):
    """
    Channels the user has created and subscribed to
    """
    return _user_request(user, inspect.stack()[0][3][5:], format)

def user_groups(user, format="xml"):
    """
    Groups the user has created and joined
    """
    return _user_request(user, inspect.stack()[0][3][5:], format)

def user_contacts_videos(user, format="xml"):
    """
    Videos that the user's contacts created
    """
    return _user_request(user, inspect.stack()[0][3][5:], format)

def user_contacts_like(user, format="xml"):
    """
    Videos that the user's contacts like
    """
    return _user_request(user, inspect.stack()[0][3][5:], format)


##
## get a specific video
##
def video_request(video, format):
    url = API_V2_CALL_URL + 'video/%s.%%s' %(video)
    return _simple_request(url)

