from flask import Blueprint, request
from datetime import datetime
from ..config import fb, db
from firebase_admin import auth

bp = Blueprint('user', __name__, url_prefix='')

@bp.route('/users', methods=['POST'])
def registration():
    data = request.json

    # check if email is already taken
    # send error msg if so
    found_email = auth.get_user_by_email(data['email'])
    if found_email:
        return {'message': 'Email already in use'}, 403

    new_user = auth.create_user(
    email=data['email'],
    email_verified=False,
    password=data['hashed_password'],
    display_name=data['username'])

    sketchbook_data = {
        u'owner_id': u'{new_user.id}',
        u'title': f"{new_user.username}'s sketchbook",
        u'timestamp': datetime.now()
    }

    update_time, sketchbook_ref = db.collection(u'sketchbooks').add(sketchbook_data)

    return {
        'currentUserId': new_user.id,
    }


@bp.route('/users', methods=['PUT'])
def userUpdate(current_user):
    data = request.json

    user = auth.update_user(
        uid = current_user.id,
        photo_url=data['avatarUrl'])

    return {'message': 'avatar updated'}


@bp.route('/users/login', methods=['POST'])
def login():
    data = request.json
    userEmail = data['email']
    userPassword = data['password']

    user = auth.sign_in_with_email_and_password(userEmail, userPassword)

    if user:
        return {
            'token': user.idToken,
            'currentUserId': user.id,
        }
    else:
        return {'message': 'Invalid user credentials'}, 401
