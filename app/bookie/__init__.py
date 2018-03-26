from flask import Blueprint

bookie = Blueprint('bookie', __name__)

from . import views  # noqa
