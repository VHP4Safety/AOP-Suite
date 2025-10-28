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

from backend.routes import aop_suite

__all__ = [

]
