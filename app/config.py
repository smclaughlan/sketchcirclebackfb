import os

import firebase_admin
from firebase_admin import credentials

abs_path = os.path.abspath("admin.json")
cred = credentials.Certificate(abs_path)
firebase_admin.initialize_app(cred)
