import requests
from mkdocstrings.handlers.base import BaseHandler

class CustomPythonHandler(BaseHandler):
    def get_source(self):
        # Override the method to disable SSL verification
        response = requests.get(self.get_source(), verify=False)
        return response.text
