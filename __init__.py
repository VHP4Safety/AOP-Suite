# backend/__init__.py

"""
Initialize the backend package.
This allows absolute imports like:
    from backend.model.aop_data_model import ...
    from backend.query.aopwikirdf import ...
"""

# Optional: expose key submodules at the package level
# This allows:
#   from backend import aop_data_model
# instead of:
#   from backend.model import aop_data_model

from backend.query import aopwikirdf, pubchem, qsprpred, bgee
from backend.service import aop_network_service
from backend.routes import aop_app

__all__ = [
    "aopwikirdf",
    "pubchem",
    "qsprpred",
    "aop_network_service",
    "aop_app",
    "bgee",
]
