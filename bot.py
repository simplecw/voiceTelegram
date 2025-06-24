from flask import Flask

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "Cloud Run is working! Use /run-main or /run-drive to trigger."
