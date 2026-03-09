import requests

url = 'http://localhost:8001/api/auth/token/'
data = {
    'username': 'comptable1',
    'password': 'comptable1@attawoune'
}
response = requests.post(url, json=data)
print("Status Code:", response.status_code)
print("Response Body:", response.json())
