#Copyright @Arslan-MD
#Updates Channel t.me/arslanmd
from flask import Flask, request, jsonify
from datetime import datetime
import cloudscraper
import json
from bs4 import BeautifulSoup
import logging
import os
import gzip
from io import BytesIO
import brotli
from telegram import Bot  # Telegram import

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Telegram setup
TELEGRAM_TOKEN = "8714715312:AAFJQ1mZCgI_dnJCL3kIT-GG-MqzUoWTVBg"
TELEGRAM_CHAT_ID = "-1003099447280"
telegram_bot = Bot(token=TELEGRAM_TOKEN)

class IVASSMSClient:
    def __init__(self):
        self.scraper = cloudscraper.create_scraper()
        self.base_url = "https://www.ivasms.com"
        self.logged_in = False
        self.csrf_token = None
        
        self.scraper.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        })

    # (All methods remain same: decompress_response, load_cookies, login_with_cookies, check_otps, get_sms_details, get_otp_message, get_all_otp_messages)

    def forward_to_telegram(self, otp_messages):
        for msg in otp_messages:
            text = f"📩 OTP Received:\nNumber: {msg['phone_number']}\nRange: {msg['range']}\nMessage: {msg['otp_message']}"
            try:
                telegram_bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text)
            except Exception as e:
                logger.error(f"Failed to send Telegram message: {e}")

app = Flask(__name__)
client = IVASSMSClient()

with app.app_context():
    if not client.login_with_cookies():
        logger.error("Failed to initialize client with cookies")

@app.route('/')
def welcome():
    return jsonify({
        'message': 'Welcome to the IVAS SMS API',
        'status': 'API is alive',
        'endpoints': {
            '/sms': 'Get OTP messages for a specific date (format: DD/MM/YYYY) with optional limit. Example: /sms?date=01/05/2025&limit=10'
        }
    })

@app.route('/sms')
def get_sms():
    date_str = request.args.get('date')
    limit = request.args.get('limit')
    
    if not date_str:
        return jsonify({'error': 'Date parameter is required in DD/MM/YYYY format'}), 400
    
    try:
        parsed_date = datetime.strptime(date_str, '%d/%m/%Y') 
        from_date = date_str
        to_date = request.args.get('to_date', '')
        if to_date:
            datetime.strptime(to_date, '%d/%m/%Y')  
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use DD/MM/YYYY'}), 400

    if limit:
        try:
            limit = int(limit)
            if limit <= 0:
                return jsonify({'error': 'Limit must be a positive integer'}), 400
        except ValueError:
            return jsonify({'error': 'Limit must be a valid integer'}), 400
    else:
        limit = None

    if not client.logged_in:
        return jsonify({'error': 'Client not authenticated'}), 401
    
    result = client.check_otps(from_date=from_date, to_date=to_date)
    if not result:
        return jsonify({'error': 'Failed to fetch OTP data'}), 500

    otp_messages = client.get_all_otp_messages(result.get('sms_details', []), from_date=from_date, to_date=to_date, limit=limit)
    
    # Forward OTPs to Telegram
    client.forward_to_telegram(otp_messages)
    
    return jsonify({
        'status': 'success',
        'from_date': from_date,
        'to_date': to_date or 'Not specified',
        'limit': limit if limit is not None else 'Not specified',
        'sms_stats': {
            'count_sms': result['count_sms'],
            'paid_sms': result['paid_sms'],
            'unpaid_sms': result['unpaid_sms'],
            'revenue': result['revenue']
        },
        'otp_messages': otp_messages
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
