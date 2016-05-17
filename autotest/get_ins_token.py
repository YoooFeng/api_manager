import requests
import sys

#client_id = input("Client ID: ").strip()
client_id = '7fbdb00ff4314c0598f509d36f0aa864'.strip()

#client_secret = input("Client Secret: ").strip()
client_secret = '82cf562a8b6549d7936d88f1685c2fea'.strip()

#redirect_uri = input("Redirect URI: ").strip()
redirect_uri = 'https://www.instagram.com'.strip()

scope = ["basic"]

res = requests.get('https://api.instagram.com/oauth/authorize/?client_id=7fbdb00ff4314c0598f509d36f0aa864&redirect_uri=https://www.instagram.com&response_type=token')

print res