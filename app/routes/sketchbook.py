from flask import Blueprint, request
from sqlalchemy import and_
from app.models import Follow, Goal, User, Sketchbook, Post, Datapoint, db
from ..util import token_required
from datetime import datetime
from ..config import fb, db

bp = Blueprint("sketchbook", __name__, "")

@bp.route("/sketchbooks")
def getBasicSketchbooks():
    # Get all the sketchbooks and sort them by timestamp.
    # sketchbooks = Sketchbook.query.order_by(Sketchbook.timestamp).all()
    sketchbooks = db.collection(u"sketchbooks").stream()
    sketchbooksDocs = list()
    for skb in sketchbooks:
        skbId = skb.id
        new_skb = skb.to_dict()
        new_skb['id'] = skbId
        sketchbooksDocs.append(new_skb)
    # TODO Is reversing necessary anymore?
    # sketchbooks.reverse()
    sketchbookList = list()
    for book in sketchbooksDocs:
        sketchbookDict = dict()
        sketchbookDict[book.id] = {"owner_id": book.owner_id,
                                   "sketchbook_id": book.id,
                                #    "avatar": book.sketchbooktouser.avatarurl,
                                   "title": book.title,
                                   "timestamp": str(book.timestamp)}
        sketchbookList.append(sketchbookDict)

    # follows = Follow.query.all()
    follows = db.collection(u"follows").stream()
    followDocs = list()
    for follow in follows:
        followId = follow.id
        new_follow = follow.to_dict()
        new_follow['id'] = followId
        followDocs.append(new_follow)

    followList = []
    for follow in followDocs:
        followSublist = [follow.follower_id, follow.sketchbook_id]
        followList.append(followSublist)
    returnDict = dict()
    returnDict['sketchbooks'] = sketchbookList
    returnDict['follows'] = followList

    return returnDict


@bp.route("/posts/<int:postId>", methods=["DELETE"])
def deletePost(current_user_id, post_id):
    db.collection(u'posts').document(f'{post_id}').delete()
    return {"message": "post deleted"}


@bp.route("/posts/<int:postId>", methods=["PUT"])
def updatePost(current_user, postId):
    data = request.json
    db.collection(u'posts').document(f'{postId}').set(data)
    return {"message": "post updated"}


@bp.route("/sketchbooks/<int:sk_id>/follow", methods=["POST"])
def addFollow(current_user_id, sk_id):
    new_follow = {
        sketchbook_id: sk_id,
        follower_id: current_user_id
    }
    update_time, follow_ref = db.collection(u'follows').add(new_follow)
    returnDict = {new_follow.sketchbook_id: True}
    return returnDict


@bp.route("/sketchbooks/<int:follow_id>/follow", methods=["DELETE"])
def deleteFollow(current_user, follow_id):
    db.collection(u'follows').document(f'{follow_id}').delete()
    return {"follow_id": follow_id}


@bp.route("/sketchbooks/<int:sk_id>")
def getSketchbookPosts(sk_id):
    # Get posts where sketchbook_id == sk_id
    posts = db.collection(u'posts').where(u'sketchbook_id', u'==', f'{sk_id}').stream()

    postsDict = dict()
    for post in posts:
        postId = post.id
        new_post = post.to_dict()
        skbId = new_post['sketchbook_id']
        new_post['id'] = postId
        if skbId not in postsDict.keys():
            postsDict[skbId] = {postId: None}
        postsDict[skbId][postId] = new_post

    # Get goals where sketchbook_id == sk_id
    goals = db.collection(u'posts').where(u'sketchbook_id', u'==', f'{sk_id}').stream()
    goalsDict = dict()
    datapointsDict = dict()
    for goal in goals:
        goalId = goal.id
        new_goal = goal.to_dict()
        new_goal['id'] = goalId
        if new_goal.sketchbook_id not in goalsDict.keys():
            goalsDict[new_goal.sketchbook_id] = {new_goal.id: None}
        goalsDict[new_goal.sketchbook_id][new_goal.id] = new_goal
        # Get datapoints for this goal by datapoint.goal_id == new_goal.id
        datapoints = db.collection(u'datapoints').where(u'goal_id', u'==', f'{new_goal.id}').stream()
        for datapoint in datapoints:
            datapointId = datapoint.id
            new_datapoint = datapoint.to_dict()
            new_datapoint['id'] = datapointId
            if new_datapoint.goal_id not in datapointsDict.keys():
                datapointsDict[new_datapoint.goal_id] = {new_datapoint.id: None}
            datapointsDict[new_datapoint.goal_id][new_datapoint.id] = new_datapoint

    returnDict = {
        'posts': postsDict,
        'goals': goalsDict,
        'datapoints': datapointsDict
    }
    return returnDict


@bp.route("/sketchbooks/<int:sk_id>", methods=["POST"])
def addPost(current_user, sk_id):
    data = request.json

    newPost = {
        'user_id': current_user.id,
        'sketchbook_id': sk_id,
        'body': data['msgBody'],
        'timestamp': datetime.now()
    }

    update_time, post_ref = db.collection(u'posts').add(newPost)
    return getSketchbookPosts(sk_id)


@bp.route("/goal", methods=["POST"])
def addGoal(current_user):
    data = request.json
    splitTargetDate = data['targetDate'].split('-')
    joinedTargetDate = ' '.join(splitTargetDate)

    datetimeOfTarget = datetime.strptime(
        joinedTargetDate, '%Y %m %d')

    userSketchbook = db.collection(u'sketchbooks').where(u'owner_id', u'==', f'{current_user.id}').stream()
    userSkbId = userSketchbook[0].id
    userSkb = userSketchbook[0].to_dict()
    userSkb['id'] userSkbId

    newGoal = {
        'owner_id': current_user.id,
        'sketchbook_id': userSketchbook.id,
        'title': data['title'],
        'description': data['description'],
        'target': data['target'],
        'targetdate': datetimeOfTarget,
        'timestamp': datetime.now()
    }
    update_time, goal_ref = db.collection(u'goals').add(newGoal)

    # Check for goals that have passed finished date, and delete them
    goalsForCurrUser = db.collection('goals').where(u'owner_id', u'==', f'{current_user.id}').stream()
    goalsList = list()
    for goal in goalsForCurrUser:
        goalId = goal.id
        new_goal = goal.to_dict()
        new_goal['id'] = goalId
        goalsList.append(new_goal)
    currDate = datetime.now()
    for goal in goalsList:
        if goal.targetdate < currDate:
            # Delete the datapoints too
            db.collection(u'datapoints').where(u'goal_id', u'==', f'{goal.id}').delete()
    db.collection(u'goals').where(u'targetdate', '<', currDate).delete()


    returnDict = {
        newGoal.sketchbook_id: {
            newGoal.id: {
                'id': newGoal.id,
                'owner_id': newGoal.owner_id,
                'sketchbook_id': newGoal.sketchbook_id,
                'title': newGoal.title,
                'description': newGoal.description,
                'target': newGoal.target,
                'targetdate': newGoal.targetdate,
                'timestamp': newGoal.timestamp
            }
        }
    }
    return returnDict


@bp.route("/goal/newdata", methods=["POST"])
def addDataPoint(current_user):
    data = request.json
    newDataPoint = {
        'goal_id': data['goal_id'],
        'value': data['value'],
        'timestamp': datetime.now()
    }
    db.collection(u'datapoints').add(newDataPoint)

    returnDict = {
        newDataPoint.goal_id: {
            newDataPoint.id: {
                'goal_id': newDataPoint.goal_id,
                'value': newDataPoint.value,
                'timestamp': newDataPoint.timestamp
            }
        }
    }
    return returnDict
