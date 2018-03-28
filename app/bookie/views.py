from flask import (flash, redirect, render_template, request)
from flask_wtf import Form
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms.fields import SubmitField

from ..models import GlobalState
from collections import defaultdict
from . import bookie
import json
import time
import csv
import os

# IMPORTED FROM https://raw.githubusercontent.com/plzTeam/web-snippets/master/plz-suche/data/zuordnung_plz_ort.csv
plz_to_state = {}
with open(
        os.path.join(os.path.dirname(os.path.abspath(__file__)),
            'zuordnung_plz_ort.csv')) as r:
    for entry in csv.DictReader(r, delimiter=","):
        plz_to_state[entry['plz']] = entry['bundesland']



class CSVForm(Form):
    fbox_export = FileField(validators=[
        FileRequired(),
        FileAllowed(['csv'], 'Nur CSV files aus der Fundraising Box, bitte!')])
    submit = SubmitField()


@bookie.route('/verteilung', methods=['GET', 'POST'])
def verteilung():
    form = CSVForm()
    results = defaultdict(lambda: {'spenden': 0 , 'bewegerin': 0, 'abrechnung': 0, 'mitgliedsbeitrag': 0,
                           'paypal': 0, 'stripe_credit_card': 0, 'fbox': 0})
    specials = []
    total = {'mitgliedsbeitrag' : 0, 'spenden' : 0, 'paypal': 0, 'fbox':0, 'stripe_credit_card': 0, 'abrechnung':0, 'bewegerin': 0, 'each': 0}

    if form.validate_on_submit():
        inpt = form.fbox_export.data
        for entry in csv.DictReader([l.decode('utf8') for l in inpt.stream], delimiter=';'):
            
            state = entry['Bundesland Auswahl']
            if not state:
                state = plz_to_state.get(entry['post_code'], '')
            buland = results[state]
            
            key = 'spenden'
            if entry['source_name'] == 'Mitglied werden' \
                or entry['source'] == 'Mitgliedsbeitrag':
                key = 'mitgliedsbeitrag'
            elif entry['source_name'] == 'BewegerIn werden':
                key = 'bewegerin'
            elif entry['type'] == 'Abrechnungsformular':
                key = 'abrechnung'
            elif entry['public_message'] \
                and entry['public_message'] not in ["Überweisung", "Will monatlich überweisen",
                                                    'Überweisung auf das Bundeskonto', 'Überweisung auf Bankkonto',
                                                    'Überweisung direkt auf das Bundeskonto'] \
                and entry['donation_info'] not in ['Überweisung Bundeskonto', 'Überweisung Bundeskonto'] \
                and not entry['public_message'].startswith('Zusammenfassung der Überweisungen '):
                entry['bundesland'] = state
                specials.append(entry)
                continue

            amount = float(entry['amount'])

            buland[key] += amount
            
            if entry['type'] not in ['Überweisung', 'Abrechnungsformular']:
                buland['fbox'] += amount * 0.005
                
                
            if entry['type'] == 'paypal':
                buland['paypal'] += (amount * 0.015) + 0.35
            elif entry['type'] == 'stripe_credit_card':
                buland['stripe_credit_card'] += (amount * 0.015) + 0.35

        for key, vals in results.items():
            each = (vals['mitgliedsbeitrag'] + vals['spenden'] + vals['bewegerin'] - vals['paypal'] - vals['stripe_credit_card'] - vals['fbox']) / 2.0
            vals['each'] = each
            for name, val in vals.items():
                total[name] += val


    return render_template('bookie/verteilung.html',
        form=form, specials=specials, results=results, total=total)
