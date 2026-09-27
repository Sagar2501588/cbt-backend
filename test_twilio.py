from twilio.rest import Client

sid = "ACbc4e58bd3c2e2f5a2cb18218ed958fa3"
token = "37a9e04fd8ec8c16750d95156bc8a5bc"

client = Client(sid, token)

try:
    account = client.api.accounts(sid).fetch()
    print(account.friendly_name)
except Exception as e:
    print(e)