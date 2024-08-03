import os
import uuid
from bson import ObjectId
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user,current_user
from pymongo import MongoClient,DESCENDING
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.secret_key = "secret_key"

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

client = MongoClient("mongodb+srv://MihaiCiurea:MihaiCiureaParola@cluster0.awcgm1r.mongodb.net/?retryWrites=true&w=majority")
db = client.DataBaseApp

# Definirea structurii colecției în baza de date
collection = db.DataBaseColectionApp

# Directorul pentru stocarea fișierelor ----- de scris 
UPLOAD_FOLDER = 'uploads'

app.config['UPLOAD_FOLDER'] = os.path.join(basedir,'static',UPLOAD_FOLDER)

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])
# ---------------------------------------------pana aici
users_collection = db['users']
posts_collection = db['posts']
messages_collection = db['messages']
notification_collection = db['notifications']
class User(UserMixin):
    def __init__(self, user_id, email,name):
        self.id = str(user_id)
        self.email = email
        self.name = name

@login_manager.user_loader
def load_user(user_id):
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    if user:
        return User(user_id=user_id, email=user['email'],name=user['name'])
    return None

@app.template_filter('get_user_name')
def get_user_name(user_id):
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    return user['name'] if user else 'Unknown User'

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('show_posts'))
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('show_posts'))
    if request.method == 'POST':
        email = request.form['email']
        existing_user = users_collection.find_one({'email': email})
        if existing_user:
            flash('Acest email exista deja!','danger')
        else:
            password = request.form['password']
            confirm_password = request.form['confirm_password']
            if password != confirm_password:
                flash('Parola nu coincide!','danger')
            else:
                hashed_password = generate_password_hash(password)
                name = request.form['name']
                users_collection.insert_one({'email': email, 'password': hashed_password, 'name': name})
                flash('Înregistrare reușită!','success')
                return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('show_posts'))
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = users_collection.find_one({'email': email})
        if user and check_password_hash(user['password'], password):
            user_obj = User(email=email,user_id=str(user['_id']),name=user['name'])
            print(str(user['_id']))
            login_user(user_obj)
            print(current_user.id)
            flash('Autentificare reușită!','success')
            return redirect(url_for('show_posts'))
        else:
            flash('E-mail/parolă invalidă!','danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Deconectare reușită!','success')
    return redirect(url_for('index'))

# Pagina de încărcare a fișierelor
@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        if 'images' not in request.files:
            return redirect(request.url)
        
        images = request.files.getlist('images')
        image_filenames = []
        
        for file in images:
            if file.filename == '':
                continue
            
            unique_filename = str(uuid.uuid4()) + os.path.splitext(file.filename)[-1]
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(file_path)
            
            image_filenames.append(unique_filename)
        
        title = request.form.get('title')
        description = request.form.get('description')
        post_data = {
            'images': image_filenames,
            'title': title,
            'description': description,
            'user_id': current_user.id,
            'posted_at': datetime.now()
        }
        posts_collection.insert_one(post_data)

        return redirect(url_for('show_posts'))

    return render_template('upload.html')

# Pagina pentru afișarea postărilor
@app.route('/posts')
@login_required
def show_posts():
    search_query = request.args.get('q', '')
    if search_query:
        posts = posts_collection.find({'title': {'$regex': search_query, '$options': 'i'}})  # Case-insensitive search
    else:
        posts = posts_collection.find()
    print(posts)
    return render_template('posts.html', posts=posts,search_query=search_query)

@app.route('/profile')
@login_required
def profile_view():
    posts = posts_collection.find({'user_id': current_user.id})
    return render_template('profile.html', posts=posts)

# Ruta pentru ștergerea unei postări
@app.route('/delete_post/<post_id>')
@login_required
def delete_post(post_id):
    post = posts_collection.find_one({'_id': ObjectId(post_id), 'user_id': current_user.id})
    if post:
        for image_filename in post['images']:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
            if os.path.exists(image_path):
                os.remove(image_path)
        
        posts_collection.delete_one({'_id': ObjectId(post_id)})
        
        return redirect(url_for('profile_view'))
    else:
        flash('Mesajul nu a fost găsit sau nu aveți autorizația de a-l șterge.', 'danger')
        return redirect(url_for('profile_view'))


@app.route('/chat/<receiver>')
@login_required
def chat(receiver):
    return render_template('chat.html', receiver=receiver)

def get_username(user_id):
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    if user:
        return user['name']
    return None

@app.route('/get_messages/<receiver>')
@login_required
def get_messages(receiver):
    sender = current_user.id
    sender_name = get_username(sender)
    receiver_name = get_username(receiver)

    sent_messages = list(messages_collection.find({'sender': sender, 'receiver': receiver}))

    received_messages = list(messages_collection.find({'sender': receiver, 'receiver': sender}))
    
    messages_combined = sorted(sent_messages + received_messages, key=lambda x: x['timestamp'])

    for message in messages_combined:
        message['_id'] = str(message['_id'])
        message['sender'] = sender_name if message['sender'] == sender else receiver_name
        message['receiver'] = sender_name if message['sender'] == sender else receiver_name
    return jsonify(messages_combined)

# Send message
@app.route('/send_message', methods=['POST'])
@login_required
def send_message():
    sender = current_user.id
    receiver = request.json['receiver']
    message = request.json['message']
    timestamp = datetime.now()

    messages_collection.insert_one({'sender': sender, 'receiver': receiver, 'message': message, 'timestamp': timestamp})
    notification_collection.insert_one({'sender': sender, 'receiver': receiver, 'message': message, 'timestamp': timestamp, 'seen': False})

    return jsonify({'success': True})


@app.route('/get_notifications')
@login_required
def get_notifications():
    receiver = current_user.id

    notifications = list(notification_collection.find({'receiver': receiver}).sort('timestamp', DESCENDING))

    # Create a dictionary to store the latest notification for each sender
    latest_notifications = {}

    for notification in notifications:
        sender = notification['sender']
        notification['_id'] = str(notification['_id'])
        notification['sender_name'] = get_username(sender)

        # Check if this sender already has a notification in the latest_notifications dictionary
        if sender not in latest_notifications:
            latest_notifications[sender] = notification
        else:
            # If the sender already has a notification, compare timestamps to determine the latest one
            if notification['timestamp'] > latest_notifications[sender]['timestamp']:
                latest_notifications[sender] = notification

    # Convert the dictionary values (latest notifications) to a list
    latest_notifications_list = list(latest_notifications.values())

    return jsonify(latest_notifications_list)

@app.route('/mark/<notification_id>/<sender_id>')
@login_required
def mark(notification_id, sender_id):
    notification_collection.update_one({'_id': ObjectId(notification_id)}, {'$set': {'seen': True}})
    return redirect(url_for('chat', receiver=sender_id))
    


if __name__ == '__main__':
    app.run(debug=True)
