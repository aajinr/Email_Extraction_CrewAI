import requests
from requests.auth import HTTPBasicAuth

url = ""
user = ""
password = ""

response = requests.get(url, auth=HTTPBasicAuth(user, password))

print("Status Code:", response.status_code)
print(response.text)
