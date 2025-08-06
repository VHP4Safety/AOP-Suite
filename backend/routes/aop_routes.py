from flask import Blueprint, request
from backend.service import aop_network_service

aop_routes = Blueprint('aop_routes', __name__)

# ... existing routes ...

@aop_routes.route('/populate_compound_table', methods=['POST'])
def populate_compound_table():
    """Populate compound table using the compound data model"""
    return aop_network_service.populate_compound_table(request)