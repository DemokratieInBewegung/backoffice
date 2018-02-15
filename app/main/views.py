from flask import render_template
from ..models import EditableHTML

from . import main


@main.route('/')
def index():
    editable_html_obj = EditableHTML.get_editable_html('index')
    return render_template('main/index.html',
                           editable_html_obj=editable_html_obj)

@main.route('/stools/<tool>')
def stools(tool):
    return render_template('static_tools/{}.html'.format(tool))


