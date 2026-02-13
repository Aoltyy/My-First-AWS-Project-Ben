from flask import Flask, request, render_template_string, redirect, session
import boto3
import os
from boto3.dynamodb.conditions import Key

app = Flask(__name__)


app.secret_key = os.environ.get('SECRET_KEY', 'change_this_to_random_secret_string')

# --- AWS CONFIGURATION ---

REGION = 'us-east-1'

# DynamoDB & S3 Connections
dynamodb = boto3.resource('dynamodb', region_name=REGION)
s3 = boto3.client('s3', region_name=REGION)

# Resource Names
METADATA_TABLE = 'ImageMetadata'
USERS_TABLE = 'Users'
BUCKET_NAME = 'bucket'

LOGIN_HTML = """
<html>
<head><title>ScribeServ Login</title>
<style>body{font-family:sans-serif; padding:50px;} input{margin:10px 0; display:block;}</style>
</head>
<body>
    <h2>ScribeServ Login</h2>
    <form method="post" action="/login">
        User: <input type="text" name="username" required>
        Pass: <input type="password" name="password" required>
        <input type="submit" value="Login">
    </form>
</body>
</html>
"""

DASHBOARD_HTML = """
<html>
<head><title>ScribeServ Dashboard</title>
<style>
    body{font-family:sans-serif; padding:20px;} 
    table{width:100%; border-collapse:collapse; margin-top: 20px;} 
    td,th{border:1px solid #ddd; padding:8px; text-align: left;}
    th{background-color: #f2f2f2;}
</style>
</head>
<body>
    <h2>Welcome, {{ user }}</h2>
    <a href="/logout">Logout</a>
    
    <h3>1. Upload Image</h3>
    <form method="post" action="/upload" enctype="multipart/form-data">
        <input type="file" name="file" required>
        <input type="submit" value="Upload">
    </form>
    
    <h3>2. Image Gallery</h3>
    <table>
        <tr>
            <th>Filename</th>
            <th>Upload Time</th>
            <th>Action</th>
        </tr>
        {% for image in images %}
        <tr>
            <td>{{ image.metadata }}</td>
            <td>{{ image.UploadTime }}</td>
            <td><a href="{{ image.url }}" target="_blank">View Image</a></td>
        </tr>
        {% endfor %}
    </table>
</body>
</html>
"""

# --- ROUTES ---

@app.route('/', methods=['GET'])
def home():
    if 'user' in session:
        try:
            table = dynamodb.Table(METADATA_TABLE)
            # Scan the table to get all image records
            response = table.scan()
            items = response.get('Items', [])
            
            # Generate presigned URLs for each image
            for item in items:
                item['url'] = s3.generate_presigned_url(
                    'get_object', 
                    Params={'Bucket': item['Bucket'], 'Key': item['metadata']}, 
                    ExpiresIn=3600 # Link valid for 1 hour
                )
            return render_template_string(DASHBOARD_HTML, user=session['user'], images=items)
        except Exception as e:
            print(f"Error fetching images: {e}")
            return render_template_string(DASHBOARD_HTML, user=session['user'], images=[])
    
    return render_template_string(LOGIN_HTML)

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    
    table = dynamodb.Table(USERS_TABLE)
    try:
        response = table.get_item(Key={'Username': username})
        if 'Item' in response and response['Item']['Password'] == password:
            session['user'] = username
            return redirect('/')
    except Exception as e:
        print(f"Login error: {e}")
        
    return "Login Failed - Please check your credentials."

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    if file.filename != '':
        try:
        
            s3.upload_fileobj(file, BUCKET_NAME, file.filename)
        except Exception as e:
            return f"Upload Failed: {e}"
    return redirect('/')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)