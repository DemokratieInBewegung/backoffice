from flask import Blueprint

mauticor = Blueprint('mautic', __name__)

from . import views  # noqa
