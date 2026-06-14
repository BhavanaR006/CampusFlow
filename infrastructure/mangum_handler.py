"""
AWS Lambda Handler for CampusFlow
Wraps FastAPI with Mangum for Lambda + API Gateway
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from mangum import Mangum
from main import app

# Lambda handler
handler = Mangum(app, lifespan="off")
