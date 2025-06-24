from flask import Flask
from google_drive_tools import main

app = Flask(__name__)

@app.route("/run-drive", methods=["GET"])
def call_drive():
    # result = google_drive_tools.main()
    # return result if result else "No output from drive_func"
    return "No output from drive_func"

@app.route("/", methods=["GET"])
def home():
    return "Cloud Run is working! Use /run-main or /run-drive to trigger."
