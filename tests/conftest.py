import sys
import os

# Make backend modules importable from the tests package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
