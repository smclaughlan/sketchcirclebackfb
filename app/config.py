import os

import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

abs_path = os.path.abspath("admin.json")
cred = credentials.Certificate(abs_path)
fb = firebase_admin.initialize_app(cred)
db = firestore.client()
