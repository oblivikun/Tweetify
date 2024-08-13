import sqlite3
import secrets
import string
import re
import requests
from urllib.parse import urlparse
from io import BytesIO
from captcha.image import ImageCaptcha 
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import *

app = Flask(__name__)
app.secret_key = "sdfnisaJADh9h8%$(9u9KD" # change this

used_captchas = []

limiter = Limiter(get_remote_address, app=app)

def check_image_url(url):
    allowed_extensions = ["jpg", "png", "gif", "jpeg", "jfif", "tiff", "bmp", "tiffy", "pif", "wpeg", "webp"]
    if not url.startswith("https://") and not url.startswith("http://"):
        return False
    parsed_url = urlparse(url)
    path = parsed_url.path
    for ext in allowed_extensions:
        if path.endswith(f".{ext}"):
            break
    else:
        return False
    try:
        response = requests.head(url)
        response.raise_for_status()
        content_type = response.headers.get("Content-Type")
        if content_type and content_type.startswith("image/"):
            return True
        return False
    except requests.exceptions.RequestException:
        return False

@app.route("/api/get_captcha")
@limiter.limit("25/minute")
def generate_captcha():
    while True:
        correct_captcha = "".join(secrets.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(6))
        if correct_captcha not in used_captchas and 'I' not in correct_captcha and 'l' not in correct_captcha:
            break
    
    session['correct_captcha'] = correct_captcha
    
    image = ImageCaptcha(width=300, height=50)
    captcha_image = image.generate_image(correct_captcha)
    
    buffer = BytesIO()
    captcha_image.save(buffer, format='PNG')
    buffer.seek(0)
    return send_file(buffer, mimetype='image/png')

# credits to heinrich-xiao for get_captcha function code. The /api/get_captcha thing wasn't created by me it was created by heinrich-xiao and modified by me.

@app.route("/signup", methods=["GET", "POST"])
@limiter.limit("5 per day")
def signup():
    if "user" in session:
        return "Already logged in."
    else:
        if request.form.get("username") and request.form.get("password") and request.form.get("captcha"):
            conn = sqlite3.connect("data.db")
            cursor = conn.cursor()
           
            if not re.match("^[A-Za-z0-9_-]*$", request.form.get("username")):
                return "Username contains invalid characters. Only latin alphabet characters and numbers are allowed."
            if len(request.form.get("username")) > 20 or len(request.form.get("username")) < 3:
                return "Invalid username length. Please make your username less than 20 characters and more than 3 characters."
            if request.form.get("password") == "":
                return "Password cannot be empty."
            if len(request.form.get("password")) > 1000:
                return "Password cannot be more than 1000 characters long."
            if len(request.form.get("password")) < 8:
                return "Password too short. Please make password 8 characters long or more."
            if request.form.get("captcha").lower() != session.get("correct_captcha").lower():
                return "Captcha is incorrect."

            cursor.execute("select * from accounts where username=?", (request.form.get("username"),),)
            if cursor.fetchone() == None:
                cursor.execute("insert into accounts values (?, ?, 'Empty Bio')", (request.form.get("username"), request.form.get("password"),),)
            else:
                return 'User already exists'

            conn.commit()
            conn.close()

            session["user"] = request.form.get("username")
            return redirect("/")
        return render_template("signup.html")

@app.route("/sendmsg/<comid>", methods=["POST"])
def sendmsg(comid):
    # message, imageurl
    if not request.form.get("message"):
        return "Expected params: message"
    
    if request.form.get("imageurl"):
        if not check_image_url(request.form.get("imageurl")):
            imageurl = ""
            return "URL does not contain a real image."
        else:
            imageurl = request.form.get("imageurl")
    else:
        imageurl = ""

    if "user" not in session:
        return "Please log in before sending this message."
    if not request.form.get("message"):
        return "expected param: message"
    if request.form.get("message") == "" or len(request.form.get("message")) <= 1 or len(request.form.get("message")) > 360:
        return "Please have a longer message."

    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()

    cursor.execute("insert into messages (communityid, username, message, imageurl, ipaddress) values (?, ?, ?, ?, ?)", (comid, session.get("user"), request.form.get("message"), imageurl, request.remote_addr,)) # add imageurl

    conn.commit()
    conn.close()

    return redirect(f"/community/{comid}")

@app.route("/community/<comid>")
def community(comid):
    messages = []
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()

    cursor.execute("select name from communities where id=?", (comid,))
    name = cursor.fetchone()[0]
    cursor.execute("select desc from communities where id=?", (comid,))
    desc = cursor.fetchone()[0]
    cursor.execute("select username, message, imageurl from messages where communityid=? order by messageid desc", (comid,))
    for row in cursor.fetchall():
        #print(row)
        messages.append(row)

    conn.close()
    return render_template("community.html", loggedIn="user" in session, name=name, comid=comid, desc=desc, messages=messages)

@app.route("/communities/create", methods=["GET", "POST"])
@limiter.limit("7 per day")
def createcom():
    if "user" not in session:
        return "Not logged in. Please log in or create an account."
    if request.method == "POST":
        if request.form.get("captchain").lower() != session.get("correct_captcha").lower():
            return "Captcha was not correct"
        if len(request.form.get("comname")) < 3:
            return "Make your community name longer."
        if len(request.form.get("comname")) > 30:
            return "Why is your community name so long?"
        if len(request.form.get("desc")) > 150:
            return "Description can't be longer than 150 characters."
        if not re.match("^[a-zA-Z0-9\s,.]+$", request.form.get("comname")):
            return "Only whitespaces, letters a-z and A-Z and commas and dots are allowed for community name."

        # anti-spam thingy

        iteration = 0
        conn = sqlite3.connect("data.db")
        cursor = conn.cursor()

        recentcoms = []
        cursor.execute("select owner from communities order by id desc")
        for row in cursor.fetchall():
            if iteration != 4:
                recentcoms.append(row[0])
            else:
                break
            iteration = iteration + 1

        try:
            if (recentcoms[0], recentcoms[1], recentcoms[2], recentcoms[3],) == (session.get("user"),session.get("user"),session.get("user"), session.get("user"),):
                return "You have been creating too many communities today. Calm down."
        except Exception as e:
            print(e)

        iteration = 0
        recentcoms = []

        conn.close()

        # end anti spam thingy

        conn = sqlite3.connect("data.db")
        cursor = conn.cursor()

        cursor.execute("insert into communities (owner, name, desc) values (?, ?, ?)", (session.get("user"), request.form.get("comname"), request.form.get("desc"),),)

        conn.commit()
        conn.close()

        return redirect("/")
    return render_template("createcom.html", loggedIn="user" in session)

@app.route("/login", methods=["GET", "POST"])
@limiter.limit("5/minute")
def login():
    if "user" in session:
        return "Already signed in."
    else:
        if request.form.get("username") and request.form.get("password") and request.form.get("captcha"):
            conn = sqlite3.connect("data.db")
            cursor = conn.cursor()

            if not re.match("^[A-Za-z0-9_-]*$", request.form.get("username")):
                return "Username contains invalid characters. Only latin alphabet characters and numbers are allowed."
            if len(request.form.get("password")) > 1000:
                return "Password cannot be more than 1000 characters long."
            if len(request.form.get("password")) < 8:
                return "Password cannot be less than 8 characters long."
            if request.form.get("password") == "":
                return "Password cannot be empty."
            if len(request.form.get("username")) > 20 or len(request.form.get("username")) < 3:
                return "Invalid username length. Please make your username less than 20 characters and more than 3 characters."
            if request.form.get("captcha").lower() != session.get("correct_captcha").lower():
                return "Captcha is incorrect."
            
            cursor.execute("select * from accounts where username=? and password=?", (request.form.get("username"), request.form.get("password"),),)
            if cursor.fetchone():
                session["user"] = request.form.get("username")
            else:
                return "Invalid account credentials."

            conn.commit()
            conn.close()
            return redirect("/")   
    return render_template("login.html", loggedIn="user" in session)

@app.route("/")
@limiter.limit("15/minute")
def main():
    if not request.args.get("listmany"):
        maxcoms = 10
    else:
        if not re.match("^[0-9]*$", request.args.get("listmany")):
            return "Listmany must be an integer."
        maxcoms = int(request.args.get("listmany"))

    iterations = 1 
    amountrows = 0
    rows = []

    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()

    cursor.execute("select * from communities")

    for aa in cursor.fetchall():
        amountrows = amountrows + 1

    if request.args.get("listmany"):
        if int(request.args.get("listmany")) > amountrows:
            return "Amount of communities requested to view is bigger than that of given communities."
    
    if not request.args.get("searchq"):
        cursor.execute("select * from communities order by id desc")
    else:
        cursor.execute("select * from communities where lower(name) like ? order by id desc", ('%' + request.args.get("searchq").lower() + '%',))
    for row in cursor.fetchall():
        rows.append(row)
        if iterations == maxcoms:
            print("Finished")
            break
        else:
            iterations = iterations + 1 
    
    iterations = 0

    conn.close()
    return render_template("index.html", loggedIn="user" in session, rows=rows, amountrows=amountrows)

@app.route("/settings")
@limiter.limit("5/minute")
def settings():
    return render_template("settings.html", loggedIn="user" in session) 

@app.route("/api/engaged_dms", methods=["GET"])
def engaged_dms():
    if "user" not in session:
        return "You are not logged in."
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()

    cursor.execute("select sender from dms where receiver=? union select receiver from dms where sender=? ", (session.get("user"), session.get("user"),),)
    engaged_dms = cursor.fetchall()

    conn.commit()
    conn.close()

    return jsonify({"resp" : engaged_dms}) 

@app.route("/dm/<username>")
@limiter.limit("10/minute")
def dm(username):
    if "user" not in session:
        return "You are not logged in."
    elif session.get("user") == username:
        return "What are you doing? You can't DM yourself."
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()

    cursor.execute("select * from accounts where username=?",(username,))
    if not cursor.fetchone():
        return "Requested user does not exist."

    cursor.execute("select sender, message from dms where (sender=? and receiver=?) or (sender=? and receiver=?)", (session.get("user"), username, username, session.get("user"),),)
    messages = cursor.fetchall()
    
    conn.close()

    return render_template("dm.html", username=username, messages=messages, loggedIn="user" in session)

@app.route("/submitdm/<username>", methods=["POST"])
@limiter.limit("10/minute")
def submit_dm(username):
    if "user" not in session:
        return "You are not logged in."
    elif session.get("user") == username:
        return "What are you doing? You can't DM yourself."

    if len(request.form.get("message")) <= 1:
        return "Why is your message under 1 character long?"
    elif len(request.form.get("message")) > 360:
        return "Message must be less than 360 characters."
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()

    cursor.execute("insert into dms values (?, ?, ?, ?)", (session.get("user"), username, request.form.get("message"), request.headers.get("X-Forwarded-For"),),)

    conn.commit()
    conn.close()
    return redirect(f"/dm/{username}")

@app.route("/change_password", methods=["POST"])
@limiter.limit("10 per day")
def changepwd():
    if not "user" in session:
        return "Not logged in."
    if not request.form.get("currentpwd") and request.form.get("newpwd"):
        return "Expected params: currentpwd, newpwd"
    if len(request.form.get("newpwd")) > 1000 or len(request.form.get("newpwd")) < 8:
        return "Password must be no more than 1000 characters and no less than 8 characters."
    if request.form.get("newpwd") == request.form.get("currentpwd"):
        return "New password is the same as the old password."

    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()

    cursor.execute("select * from accounts where username=? and password=?",(session.get("user"),request.form.get("currentpwd"),),)
    if not cursor.fetchone():
        return "Current password is incorrect."

    cursor.execute("update accounts set password=? where username=?", (request.form.get("newpwd"), session.get("user"),),)

    conn.commit()
    conn.close()

    return redirect("/")

@app.route("/edit_bio", methods=["GET", "POST"])
@limiter.limit("4/minute")
def editbio():
    if not "user" in session:
        return "Not logged in."

    if request.method == "POST":
        if not request.form.get("newbio"):
            return "Expected \"newbio\" parameter."

        if len(request.form.get("newbio")) > 350:
            return "Your bio was too long. Please choose a shorter bio."
        if len(request.form.get("newbio")) < 4:
            return "Bio must be of at least 4 characters long. Please choose a longer bio."

        conn = sqlite3.connect("data.db")
        cursor = conn.cursor()

        cursor.execute("update accounts set bio=? where username=?", (request.form.get("newbio"), session.get("user"),),)

        conn.commit()
        conn.close()
        return redirect(f"/user/{session.get('user')}")

    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()

    cursor.execute("select bio from accounts where username=?", (session.get("user"),),)
    current_bio = cursor.fetchone()[0] 

    conn.close()

    return render_template("bioedit.html", loggedIn="user" in session, current_bio=current_bio) 

@app.route("/user/<username>")
@limiter.limit("5/minute")
def profile(username):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
   
    cursor.execute("select * from accounts where username=?", (username,),)
    if not cursor.fetchone():
        return "User doesn't exist. Please enter a valid username."
    
    cursor.execute("select bio from accounts where username=?", (username,),)
    #print(cursor.fetchone()[0])
    bio = cursor.fetchone()[0]

    conn.close()
    return render_template("profile.html", username=username, bio=bio, loggedIn='user' in session, username1=session.get("user"))

@app.route("/logout")
@limiter.limit("5/minute")
def logout():
    if "user" in session:
        session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run("0.0.0.0")

