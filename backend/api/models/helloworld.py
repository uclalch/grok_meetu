from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

# Base recommendation models
class HelloWorldItem(BaseModel):
    """Individual recommendation"""
    say: str
