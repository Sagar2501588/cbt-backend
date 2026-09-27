from twilio.rest import Client

client = Client(
    "ACbc4e58bd3c2e2f5a2cb18218ed958fa3",
    "37a9e04fd8ec8c16750d95156bc8a5bc"
)

verification = client.verify.v2.services(
    "VA1ab8a28e9e39eb09dc40ab1a94426c95"
).verifications.create(
    to="+917980144216",   # তোমার নম্বর
    channel="sms"
)

print(verification.status)