import sqlite3
import secrets
import string
import re
from io import BytesIO
from captcha.image import ImageCaptcha 
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import *

app = Flask(__name__)
app.secret_key = "sdfnisaJADh9h8%$(9u9KD" # change this

used_captchas = []

limiter = Limiter(get_remote_address, app=app)

@app.route("/api/get_captcha")
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

@app.route("/signup", methods=["GET", "POST"])
@limiter.limit("5/minute")
def signup():
    if "user" in session:
        return "Already logged in."
    else:
        if request.form.get("username") and request.form.get("password"):
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

@app.route("/login", methods=["GET", "POST"])
@limiter.limit("5/minute")
def login():
    if "user" in session:
        return "Already signed in."
    else:
        if request.form.get("username") and request.form.get("password"):
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
    return render_template("login.html")

@app.route("/")
@limiter.limit("15/minute")
def main():
    return render_template("index.html", loggedIn="user" in session)

@app.route("/edit_bio", methods=["GET", "POST"])
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

