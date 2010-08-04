"""
Module providing convenience classes and methods for some basic API procedures.

In general, this module is more rigid than the base module, in that it relies
on some current API behavior (e.g. hard-coding some parameters in the Uploader
class) where the base module chooses to remain ambigous. While this module
shouldn't completely break either until Vimeo seriously changes their API, keep
in mind that if something in this module doesn't work, it still might work the
"conventional" way using just the base module.
"""
from urllib import urlencode

import httplib2
import oauth2

from . import VimeoClient

class VimeoUploader(object):
    """
    A convenience uploader class to be used alongside a client.
    """
    def __init__(self, vimeo_client, ticket, **kwargs):
        self.vimeo_client = vimeo_client
        self.endpoint = ticket["endpoint"]
        self.ticket_id = ticket["id"]
        self.chunk_id = 0

        self.user = getattr(vimeo_client, "user", None)

        quota = kwargs.pop("quota", None)
        if quota:
            self.has_sd_quota = bool(quota["sd_quota"])
            self.has_hd_quota = bool(quota["hd_quota"])
            self.upload_space = quota["upload_space"]

    def _post_to_endpoint(self, file_data, **kwargs):
        params = {"ticket_id" : self.ticket_id,
                  "chunk_id" : self.chunk_id}

        method, consumer, token = (self.vimeo_client.signature_method,
                                   self.vimeo_client.consumer,
                                   self.vimeo_client.token)

        request = oauth2.Request.from_consumer_and_token(consumer=consumer,
                                                       token=token,
                                                       http_method="POST",
                                                       http_url=self.endpoint,
                                                       parameters=params)
        request.sign_request(method, consumer, token)

        # file data should be unsigned as per the API docs
        body = "{0}&file_data={1}".format(request.to_postdata(), file_data)
        headers = kwargs.get("headers",
                             dict(self.vimeo_client._CLIENT_HEADERS))
        headers.setdefault("Content-Type", "application/x-www-form-urlencoded")

        return httplib2.Http.request(self.vimeo_client.client, self.endpoint,
                                   method="POST", body=body, headers=headers,
                                   redirections=httplib2.DEFAULT_MAX_REDIRECTS,
                                   connection_type=None)

    def upload(self, file_data):
        _, content = self._post_to_endpoint(file_data)
        self.chunk_id += 1
        return content
