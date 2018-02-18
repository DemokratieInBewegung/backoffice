from flask import (flash, redirect, render_template, request,
                   url_for, session, current_app, jsonify)
from flask_login import (current_user, login_required, login_user,
                         logout_user)
from flask_rq import get_queue

from pprint import pformat

from requests_oauthlib import OAuth2Session

from mautic import MauticOauth2Client, Contacts

from . import mauticor
import json


CACHED_KEY = '__MAUTIC_OAUTH_TOKEN'


def update_token_tempfile(token):
    current_app.cache.set(CACHED_KEY, json.dumps(token))


def get_oauth_token():
    return json.loads(current_app.cache.get(CACHED_KEY))


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

    # We use the session as a simple DB for this example.
    update_token_tempfile(token)  # store token in /tmp/mautic_creds.json

    return redirect(url_for('.menu'))

@mauticor.route("/petition_info/proko.js", methods=["GET"])
def get_proko_state():
    return """
    document.PROKO_STATE = {}
    """.format(json.dumps({
            total: 1234,
            latest: []
        }, ))


@mauticor.route("/menu", methods=["GET"])
@login_required
def menu():
    """"""
    return """
    <h1>Congratulations, you have obtained an OAuth 2 token!</h1>
    <h2>What would you like to do next?</h2>
    <ul>
        <li><a href="/mauticor/contacts"> Get contacts</a></li>
    </ul>

    <pre>
    %s
    </pre>
    """ % pformat(get_oauth_token(), indent=4)


@mauticor.route("/contacts", methods=["GET"])
@login_required
def contacts():
    """Fetching a protected resource using an OAuth 2 token.
    """
    mautic = MauticOauth2Client(base_url=current_app.config.get("MAUTIC_BASE_URL"),
                                client_id=current_app.config.get("MAUTIC_CLIENT_ID"),
                                client_secret=current_app.config.get("MAUTIC_CLIENT_SECRET"),
                                token=get_oauth_token(),
                                token_updater=update_token_tempfile)
    return jsonify(Contacts(client=mautic).get_list())

