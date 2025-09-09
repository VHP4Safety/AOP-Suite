from flask import Flask, render_template, jsonify, request, redirect, url_for
import logging

from backend.routes.aop_app import aop_app
from backend.service import aop_network_service


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = Flask(__name__)
app.register_blueprint(aop_app)


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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
