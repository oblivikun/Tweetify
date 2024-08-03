from flask import *

app = Flask(__name__)

@app.route("/")
def main():
    return "this is a test"

if __name__ == "__main__":
    app.run("0.0.0.0")

