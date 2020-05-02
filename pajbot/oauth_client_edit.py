from flask_oauthlib.client import OAuth, parse_response
from flask_oauthlib.client import OAuthRemoteApp
from flask_oauthlib.client import OAuthResponse
from flask_oauthlib.client import OAuthException

import logging
from json import loads as jsonify
from copy import copy
from oauthlib.common import add_params_to_uri
from flask import request, session
from flask_oauthlib.utils import to_bytes
import requests
import base64

log = logging.getLogger(__name__)


class OAuthEdited(OAuth):
    def remote_app(self, name, register=True, **kwargs):
        """Registers a new remote application.

        :param name: the name of the remote application
        :param register: whether the remote app will be registered

        Find more parameters from :class:`OAuthRemoteApp`.
        """
        remote = OAuthRemoteAppEdited(self, name, **kwargs)
        if register:
            assert name not in self.remote_apps
            self.remote_apps[name] = remote
        return remote


class OAuthRemoteAppEdited(OAuthRemoteApp):
    def request(
        self,
        url,
        data=None,
        headers=None,
        format="urlencoded",
        method="GET",
        content_type=None,
        token=None,
        discord=False,
    ):
        """
        Sends a request to the remote server with OAuth tokens attached.

        :param data: the data to be sent to the server.
        :param headers: an optional dictionary of headers.
        :param format: the format for the `data`. Can be `urlencoded` for
                       URL encoded data or `json` for JSON.
        :param method: the HTTP request method to use.
        :param content_type: an optional content type. If a content type
                             is provided, the data is passed as it, and
                             the `format` is ignored.
        :param token: an optional token to pass, if it is None, token will
                      be generated by tokengetter.
        """

        headers = dict(headers or {})
        if token is None:
            token = self.get_request_token()

        client = self.make_client(token)
        url = self.expand_url(url)
        if method == "GET":
            assert format == "urlencoded"
            if data:
                url = add_params_to_uri(url, data)
                data = None
        else:
            if content_type is None:
                data, content_type = OAuth.encode_request_data(data, format)
            if content_type is not None:
                headers["Content-Type"] = content_type

        if self.request_token_url:
            # oauth1
            uri, headers, body = client.sign(url, http_method=method, body=data, headers=headers)
        else:
            # oauth2
            uri, headers, body = client.add_token(url, http_method=method, body=data, headers=headers)

        if hasattr(self, "pre_request"):
            # This is designed for some rubbish services like weibo.
            # Since they don't follow the standards, we need to
            # change the uri, headers, or body.
            uri, headers, body = self.pre_request(uri, headers, body)

        if body:
            data = to_bytes(body, self.encoding)
        else:
            data = None
        if discord:
            response = requests.request(method, uri, headers=headers, data=to_bytes(body, self.encoding))
            if response.status_code not in (200, 201):
                raise OAuthException("Invalid response from %s" % self.name, type="invalid_response", data=data)
            return jsonify(response.text.encode("utf8"))

        resp, content = self.http_request(uri, headers, data=to_bytes(body, self.encoding), method=method)
        return OAuthResponse(resp, content, self.content_type)

    def handle_oauth2_response_discord(self, args):
        """Handles an oauth2 authorization response."""

        client = self.make_client()
        remote_args = {
            "client_id": self.consumer_key,
            "client_secret": self.consumer_secret,
            "code": args.get("code"),
            "redirect_uri": session.get("%s_oauthredir" % self.name),
            "scope": "identify",
        }
        log.debug("Prepare oauth2 remote args %r", remote_args)
        remote_args.update(self.access_token_params)
        headers = copy(self._access_token_headers)
        if self.access_token_method == "POST":
            headers.update({"Content-Type": "application/x-www-form-urlencoded"})
            body = client.prepare_request_body(**remote_args)
            response = requests.request(
                self.access_token_method,
                self.expand_url(self.access_token_url),
                headers=headers,
                data=to_bytes(body, self.encoding),
            )
            if response.status_code not in (200, 201):
                raise OAuthException(
                    "Invalid response from %s" % self.name, type="invalid_response", data=to_bytes(body, self.encoding)
                )
            return jsonify(response.text.encode("utf8"))
        elif self.access_token_method == "GET":
            qs = client.prepare_request_body(**remote_args)
            url = self.expand_url(self.access_token_url)
            url += ("?" in url and "&" or "?") + qs
            response = requests.request(self.access_token_method, url, headers=headers)
            if response.status_code not in (200, 201):
                raise OAuthException(
                    "Invalid response from %s" % self.name, type="invalid_response", data=to_bytes(body, self.encoding)
                )
            return jsonify(response.text.encode("utf8"))
        else:
            raise OAuthException("Unsupported access_token_method: %s" % self.access_token_method)

    def authorized_response(self, args=None, spotify=False, discord=False):
        """Handles authorization response smartly."""
        if args is None:
            args = request.args
        if spotify:
            data = self.handle_oauth2_response_spotify(args)
        elif discord:
            data = self.handle_oauth2_response_discord(args)
        else:
            if "oauth_verifier" in args:
                data = self.handle_oauth1_response(args)
            elif "code" in args:
                data = self.handle_oauth2_response(args)
            else:
                data = self.handle_unknown_response()

        # free request token
        session.pop("%s_oauthtok" % self.name, None)
        session.pop("%s_oauthredir" % self.name, None)
        return data

    def handle_oauth2_response_spotify(self, args):
        """Handles an oauth2 authorization response."""

        client = self.make_client()
        remote_args = {"code": args.get("code"), "redirect_uri": session.get("%s_oauthredir" % self.name)}
        log.debug("Prepare oauth2 remote args %r", remote_args)
        remote_args.update(self.access_token_params)
        data = f"{self._consumer_key}:{self._consumer_secret}"
        encoded = str(base64.b64encode(data.encode("utf-8")), "utf-8")
        headers = {"Authorization": f"Basic {encoded}"}
        if self.access_token_method == "POST":
            headers.update({"Content-Type": "application/x-www-form-urlencoded"})
            body = client.prepare_request_body(**remote_args)
            resp, content = self.http_request(
                self.expand_url(self.access_token_url),
                headers=headers,
                data=to_bytes(body, self.encoding),
                method=self.access_token_method,
            )
        elif self.access_token_method == "GET":
            qs = client.prepare_request_body(**remote_args)
            url = self.expand_url(self.access_token_url)
            url += ("?" in url and "&" or "?") + qs
            resp, content = self.http_request(url, headers=headers, method=self.access_token_method)
        else:
            raise OAuthException("Unsupported access_token_method: %s" % self.access_token_method)

        data = parse_response(resp, content, content_type=self.content_type)
        if resp.code not in (200, 201):
            raise OAuthException("Invalid response from %s" % self.name, type="invalid_response", data=data)
        return data
