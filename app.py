from flask import Flask, request, jsonify, render_template, send_file, Blueprint, render_template, abort, g, redirect, url_for
import requests
from wikidataintegrator import wdi_core
import json
import re
import logging
from werkzeug.routing import BaseConverter
from jinja2 import TemplateNotFound
from SPARQLWrapper import SPARQLWrapper, JSON
from rdflib import Graph

from backend.routes.aop_app import aop_app


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = Flask(__name__)
app.register_blueprint(aop_app)


class RegexConverter(BaseConverter):
    """Converter for regular expression routes.

    References
    ----------
    Scholia views.py
    https://stackoverflow.com/questions/5870188

    """

    def __init__(self, url_map, *items):
        """Set up regular expression matcher."""
        super(RegexConverter, self).__init__(url_map)
        self.regex = items[0]


def get_aop_graph():
    """Get or create the AOP RDF graph"""
    if not hasattr(g, 'aop_graph'):
        g.aop_graph = Graph()
        # Load your AOP data here if needed
        # g.aop_graph.parse("path_to_aop_data.ttl", format="turtle")
    return g.aop_graph

@app.route('/')
def index():
    """Main AOP Network Builder application"""
    return render_template('services/AOPapp.html', 
                         title='AOP Network Builder',
                         mie_query='',
                         qid='',
                         qid_wd='')

@app.route('/aop')
def aop_redirect():
    """Redirect old AOP route to main page"""
    return redirect(url_for('index'))

@app.route('/aop/<mie_query>')
def aop_with_mie(mie_query):
    """AOP app with specific MIE query"""
    return render_template('services/AOPapp.html',
                         title=f'AOP Network Builder - {mie_query}',
                         mie_query=mie_query,
                         qid='',
                         qid_wd='')

@app.route('/aop/<qid>/<qid_wd>')
def aop_with_ids(qid, qid_wd):
    """AOP app with specific IDs"""
    return render_template('services/AOPapp.html',
                         title=f'AOP Network Builder - {qid}',
                         mie_query='',
                         qid=qid,
                         qid_wd=qid_wd)


@app.route("/services/AOPapp")
def aop_app():
    return render_template("services/AOPapp.html")


@app.route('/workflow/<workflow>')
def show(workflow):
    try:
        return render_template(
            f"case_studies/{workflow}/workflows/{workflow}_workflow.html"
        )
    except TemplateNotFound:
        abort(404)


# Register the blueprint

################################################################################
@app.route("/aop_standalone")
def aop_standalone():
    """
    Standalone AOP Network Builder - doesn't require template data
    """
    return render_template("aop_app.html", 
                         title="AOP Network Builder - Standalone",
                         mie_query="",
                         qid="",
                         qid_wd="")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
