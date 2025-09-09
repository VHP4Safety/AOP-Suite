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

@app.route("/query_bgee_expression", methods=["POST"])
def query_bgee_expression():
    """Query Bgee for gene expression data"""
    try:
        result, status_code = aop_service.query_bgee_expression(request)
        return jsonify(result), status_code
    except Exception as e:
        logger.error(f"Error in query_bgee_expression route: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/query_bgee_anatomical", methods=["POST"])
def query_bgee_anatomical():
    """Query Bgee for anatomical expression data"""
    try:
        result, status_code = aop_service.query_bgee_anatomical(request)
        return jsonify(result), status_code
    except Exception as e:
        logger.error(f"Error in query_bgee_anatomical route: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/query_bgee_developmental", methods=["POST"])
def query_bgee_developmental():
    """Query Bgee for developmental expression data"""
    try:
        result, status_code = aop_service.query_bgee_developmental(request)
        return jsonify(result), status_code
    except Exception as e:
        logger.error(f"Error in query_bgee_developmental route: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/populate_gene_expression_table", methods=["POST"])
def populate_gene_expression_table():
    """Populate gene expression table from network elements"""
    try:
        result, status_code = aop_service.populate_gene_expression_table(request)
        return jsonify(result), status_code
    except Exception as e:
        logger.error(f"Error in populate_gene_expression_table route: {e}")
        return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
