from flask import (flash, redirect, render_template, request,
                   url_for, session, current_app, jsonify)
from flask_login import (current_user, login_required, login_user,
                         logout_user)
from flask_cors import cross_origin

from pprint import pformat

from requests_oauthlib import OAuth2Session

from mautic import MauticOauth2Client, Contacts, Forms
from .. import cache
from . import mauticor
import json
import time

CACHED_KEY = '__MAUTIC_OAUTH_TOKEN'


def update_token_tempfile(token):
    current_app.cache.set(CACHED_KEY, json.dumps(token))


def get_oauth_token():
    token = json.loads(current_app.cache.get(CACHED_KEY))
    token['expires_in'] = token['expires_at'] - time.time()
    return token


def _get_mautic_client():
    return MauticOauth2Client(
            base_url=current_app.config.get("MAUTIC_BASE_URL"),
            client_id=current_app.config.get("MAUTIC_CLIENT_ID"),
            client_secret=current_app.config.get("MAUTIC_CLIENT_SECRET"),
            token=get_oauth_token(),
            token_updater=update_token_tempfile)


class Submissions(Forms):
    def get_submissions(self, form_id):
        response = self._client.session.get(
            '{url}/{form_id}/submissions'.format(
                url=self.endpoint_url, form_id=form_id
                )
            )
        return self.process_response(response)


@mauticor.route("/petition_info/proko.json", methods=["GET"])
@cross_origin()
@cache.cached(timeout=300)  # we cache for 5min
def get_proko_state():

    mautic = _get_mautic_client()
    forms = Submissions(client=mautic)
    resp = forms.get_submissions(9)  # PROKO is dealt with FORM nr 9

    return jsonify({
            "total": resp['total'],
            "latest": []
        })



@mauticor.route("/token")
@login_required
def show_token():
    return jsonify(get_oauth_token())


@mauticor.route("/")
@login_required
def index():
    """Step 1: User Authorization.

    Redirect the user/resource owner to the OAuth provider using an URL with a few key OAuth parameters.
    """
    mautic = OAuth2Session(current_app.config.get("MAUTIC_CLIENT_ID"),
                redirect_uri=current_app.config.get("MAUTIC_REDIRECT_URI"))
    authorization_url, state = mautic.authorization_url(
        current_app.config.get("MAUTIC_BASE_URL") +  'oauth/v2/authorize',
        grant_type='authorization_code')

    session['oauth_state'] = state
    return redirect(authorization_url)


# Step 2: User authorization, this happens on the provider.
@mauticor.route("/callback", methods=['GET'])
@login_required
def callback():
    """ Step 3: Retrieving an access token.

    The user has been redirected back from the provider to your registered
    callback URL. With this redirection comes an authorization code included
    in the redirect URL. We will use that to obtain an access token.
    """

    mautic = OAuth2Session(current_app.config.get("MAUTIC_CLIENT_ID"),
            redirect_uri=current_app.config.get("MAUTIC_REDIRECT_URI"),
            state=session['oauth_state'])
    token = mautic.fetch_token(current_app.config.get("MAUTIC_BASE_URL") + 'oauth/v2/token',
            client_secret=current_app.config.get("MAUTIC_CLIENT_SECRET"),
            authorization_response=request.url)

    update_token_tempfile(token)  

    return redirect(url_for('.get_proko_state'))