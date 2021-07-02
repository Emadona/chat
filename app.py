from werkzeug.security import check_password_hash
from werkzeug.security import generate_password_hash
from os import name
from datetime import datetime
import string
import random
from flask import Flask , json , request
from flask_socketio import SocketIO , join_room,leave_room
from flask_restful import Api , Resource
from flask_sqlalchemy import SQLAlchemy
app = Flask(__name__)
app.secret_key = "fdsgvdfrhg"
app.config['SECRET_KEY'] = '5791628bb0b13ce0c676dfde280ba245'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
db = SQLAlchemy(app)
api = Api(app)
socketio = SocketIO(app)
import default
image = default.image
class User(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(), unique=True)
    image_file = db.Column(db.String(),default = image )
    password = db.Column(db.String())
    email = db.Column(db.String())
    api_key = db.Column(db.String())
    isonline = db.Column(db.Boolean(),default = False)
    lastseen = db.Column(db.DateTime)
    device = db.Column(db.String())
    def serialize(self):
        return {
            "id" : str(self.id),
            'api_key' : self.api_key,
            'name' : self.name,
            "image_file" : self.image_file,
            'password' : self.password,
            'email' : self.email,
            'isonline' : self.isonline,
            'lastseen' : str(self.lastseen)
        }


    def __repr__(self):
        return '<name {}>'.format(self.name)

class Friend(db.Model):
    id = db.Column(db.Integer,primary_key = True)
    name = db.Column(db.String)
    chatfriendId = db.Column(db.String)
    chatId = db.Column(db.String)
    userId = db.Column(db.Integer,db.ForeignKey('user.id'),
        nullable=False)
    user = db.relationship('User',
        backref=db.backref('friends', lazy=True))

    
    def serialize(self):
        return{
        "name": self.name,
        'chatfriendId' : str(self.chatfriendId),
        "chatId":self.chatId,
        # 'lastseen' : self.lastseen
        }

class Message (db.Model):

    id = db.Column(db.Integer,primary_key=True)
    sender = db.Column(db.String)
    targetId = db.Column(db.String)
    text = db.Column(db.String)
    created_at = db.Column(db.DateTime)
    unread = db.Column(db.Boolean(),default = True,nullable=True)
    islike = db.Column(db.Boolean(),default = False,nullable=True)

    def serialize(self):
        return{
            "id" : self.id,
            "senderChatID" : self.sender,
            'receiverChatID':self.targetId,
            "content" : self.text,
            "created_at" : str(self.created_at),
            "unread" : self.unread,
            "islike" : self.islike,
        }

def savemessage(data):
    message = Message(
        sender = data['senderChatID'],
        targetId = data['receiverChatID'],
        text = data['content'],
        created_at = datetime.utcnow(),
        unread = False,
        islike = False
    )
    db.session.add(message)
    db.session.commit()



class Login(Resource):
    
    def post(self):
        result = ""
        json_data = request.get_json(force=True)
        header = request.headers["Authorization"]

        if not header:
            result = self.username_and_password_signin(json_data)
        else:
            user = User.query.filter_by(api_key=header).first()
            if user:
                result = User.serialize(user)
            else:
                result = self.username_and_password_signin(json_data)

        return {"status": 'success', 'data': result}, 201

    def username_and_password_signin(self, json_data):
        if not json_data:
            return {'message': 'No input data provided'}, 400

        user = User.query.filter_by(email=json_data['email']).first()
        if not user:
            return {'message': 'Email does not exist'}, 400

        if check_password_hash( user.password,json_data['password']) == False:
            return {'message': 'Password incorrect'}, 400

        return User.serialize(user)

    def generate_key(self):
        return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(50))
api.add_resource(Login, '/login')

class Register(Resource):
    def post(self):
        json_data = request.get_json(force=True)

        if not json_data:
            return {'message': 'No input data provided'}, 400
        user = User.query.filter_by(name=json_data['name']).first()
        if user:
            return {'message': 'Username not available'}, 400

        user = User.query.filter_by(email=json_data['email']).first()
        if user:
            return {'message': 'Email address already exists'}, 400
        api_key = self.generate_key()

        user = User.query.filter_by(api_key=api_key).first()
        if user:
            return {'message': 'API key already exists'}, 400

        hash_pass = generate_password_hash(json_data['password'])
        user = User(
             api_key = api_key,
            name = json_data['name'],
            email = json_data['email'],
            password = hash_pass,
        )
        db.session.add(user)
        db.session.commit()

        result = User.serialize(user)

        return { "status": 'success', 'data': result }, 201

    def generate_key(self):
        return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(50))
api.add_resource(Register, '/register')


class CreateFriendship(Resource):
    def post(self):
        header = request.headers["Authorization"]
        json_data = request.data
        json_data = json.loads(json_data.decode('utf-8'))
        if not header:
            return {"message" : "No headr"},400
        
        user = User.query.filter_by(api_key=header).first()
        if not user:
            return {'message' : 'please inter a validate user'},400

        if not json_data:
            return {'message' : "no input provider"} ,400
        user2 = User.query.filter_by(email=json_data['name']).first()
        if not user2.name:
            return {'message' : "this name does'nt exist"},400

        chatId = self.generate_key()
        friend1 = Friend(
            name = user2.name,
            chatId = chatId,
            chatfriendId = user2.id,
        )
        friend2 = Friend(
            name = user.name,
            chatId = chatId,
            chatfriendId = user.id,
        )
        user.friends.append(friend1)
        user2.friends.append(friend2)
        db.session.commit()
        friends = Friend.query.filter_by(userId=user.id).all()
        results=[]
        for freind in friends:
            results.append(Friend.serialize(freind))

        return {'status': 'success', 'data' : results},200

    def generate_key(self):
        return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(50))
    
    
    def get(self):
        header = request.headers['Authorization']
        if not header:
            return {'message' : 'not header found'}
        user = User.query.filter_by(api_key=header).first()
        if not user:
            return {'message' : "not user found"},400
        friends = Friend.query.filter_by(userId=user.id).all()
        results=[]
        for freind in friends:
            results.append(Friend.serialize(freind))
        return {'status': 'success', 'data' : results},200

api.add_resource(CreateFriendship, '/create')

class Search(Resource):
    def post(self):
        header = request.headers["Authorization"]
        result = ''
        json_data = request.get_json(force=True)
        if not header:
            return {"Messege" : "No api key!"}, 400
        
        user = User.query.filter_by(api_key=header).first()
        if not user:
            return {"Messege" :  'User does not exist'}, 400
        user2 = User.query.filter_by(email=json_data['email']).first()
        if not user2:
            return {'message': 'This User does not exist'}, 400
        if user2:
            

            result = {
                
                'name' : user2.name,
                'email':user2.email,
                'chatfriendId' : user2.id,
                }
        return {"status": 'success', 'data': result}, 201
api.add_resource(Search, '/search')

class viewMessages(Resource):
    def get(self):
        result = []
        #["Authorization"]
        header = request.headers

        if not header["Authorization"]:
            return {"Messege" : "No api key!"}, 400
    
        user = User.query.filter_by(api_key = header["Authorization"]).first()

        if not user:
            return {'message': 'This User does not exist'}, 400

        chats = Message.query.filter_by(sender = header['chat_id']).all()
        chats2 = Message.query.filter_by(targetId = header['chat_id']).all()
        results = []
        for chat in chats:
            results.append(Message.serialize(chat))
        for chat2 in chats2:
            results.append(Message.serialize(chat2))
  
        return {'data' : results} , 200
        
api.add_resource(viewMessages, '/view')

class uploadimageprofile(Resource):
    def post(self):
        header = request.headers["Authorization"]
        json_data = request.get_json(force=True)
        if not header:
            return {"Messege" : "No api key!"}, 400
        print(1)
        user = User.query.filter_by(api_key=header).first()
        if not user:
            print('not user')
            return {"Messege" :  'User does not exist'}, 400
        user.image_file = json_data['image']
        db.session.commit()
        return {'state' : 'secssus','data' : user.image_file},200

api.add_resource(uploadimageprofile, '/upload')


@socketio.on('connect')
def handle_connect():
    print('connect '+request.sid)

@socketio.on('disconnect')
def handle_disconnect():
    print("disconnect" + request.sid)
    user = User.query.filter_by(device = request.sid).first()
    user.isonline = False
    user.lastseen = datetime.utcnow()
    db.session.commit()
    friendfirst =user.friends
    if friendfirst:
        for friend in friendfirst:
            socketio.emit('receive_friendonline',{'name':user.name,'isonline':user.isonline,
            'lastseen':str(user.lastseen),
            },to=str(friend.chatfriendId))

def generate_key():
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(50))


@socketio.on('message')
def handle_signin(*data):
    
    join_room(data[0])
    print(data)
    user = User.query.filter_by(api_key=data[1]).first()
    if not user:
        return False
    user.isonline =True
    user.device = request.sid
    db.session.commit()
    friendfirst =user.friends
    if friendfirst:
        for friend in friendfirst:
            socketio.emit('receive_friendonline',{'name':user.name,'isonline':user.isonline,
            },to=str(friend.chatfriendId))
    friends = user.friends
    results=[]
    for freind in friends:
        fr = User.query.filter_by(name = freind.name).first()
        results.append({
            'name':fr.name,
            'chatfriendId' : str(fr.id),
            'chatId' : freind.chatId,
            'isonline' : fr.isonline,
            "lastseen":str(fr.lastseen),
            'image_file' : fr.image_file,
            'typing' : False
        })
    socketio.emit('receive_friends',results, to=data[0])
    

    chats = Message.query.filter_by(sender = data[0]).all()
    chats2 = Message.query.filter_by(targetId = data[0]).all()
    result = []
    for chat in chats:
        result.append(Message.serialize(chat))
    for chat2 in chats2:
        result.append(Message.serialize(chat2))

    socketio.emit('receive_all_messages',result, to=data[0])


@socketio.on('create_friends')
def handle_create(data):
    print(data)
    jsondata = json.loads(data)

    user = User.query.filter_by(api_key=jsondata['api_key']).first()
    if not user:
        return False
    user2 = User.query.filter_by(email = jsondata['friend_email']).first()
    if not user2:
        return False
    chatId = generate_key()
    friend1 = Friend(
        name = user2.name,
        chatId = chatId,
        chatfriendId = user2.id
    )
    friend2 = Friend(
        name = user.name,
        chatId = chatId,
        chatfriendId = user.id
    )
    user.friends.append(friend1)
    user2.friends.append(friend2)
    db.session.commit()


    results = {
        'name': user.name,
        'chatfriendId' : str(user.id),
        'chatId' : chatId,
        'isonline' : user.isonline,
        "lastseen":str(user.lastseen),
        'image_file' : user.image_file,
        'typing' : False
    }
    result = {
        'name': user2.name,
        'chatfriendId' : str(user2.id),
        'chatId' : chatId,
        'isonline' : user2.isonline,
        "lastseen":str(user2.lastseen),
        'image_file' : user2.image_file,
        'typing' : False
    }


    socketio.emit('receive_friend',results, to=str(user2.id))
    socketio.emit('receive_friend',result, to=str(user.id))


@socketio.on('messages')
def handle_send_message_event(msg):
    print('data '+msg)

    jsondata = json.loads(msg)
    jsondata['created_at'] = str(datetime.utcnow())
    savemessage(jsondata)
    socketio.emit('receive_message',jsondata, to=jsondata['receiverChatID'])
    socketio.emit('receive_message',jsondata, to=jsondata['senderChatID'])


@socketio.on('typing')
def handle_send_typing_event(msg):
    print('data '+msg)

    jsondata = json.loads(msg)
    
    savemessage(jsondata)
    socketio.emit('receive_typing',jsondata, to=jsondata['receiverChatID'])



if __name__ == '__main__':
    socketio.run(app,debug=True,host='0.0.0.0',port=5000)
