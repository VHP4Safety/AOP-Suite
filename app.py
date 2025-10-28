from flask import Flask, render_template, redirect, url_for, request, jsonify
import logging

from backend.routes.aop_suite import aop_app


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = Flask(__name__)
app.register_blueprint(aop_app)


@app.route('/')
def index():
    """Main AOP-Suite application"""
    return render_template('services/AOPapp.html', 
                         title='AOP-Suite',
                         mie_query='',
                         qid='',
                         qid_wd='')

@app.route('/aop')
def aop_redirect():
    """Redirect old AOP route to main page"""
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
