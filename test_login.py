import requests


def main():
    url = "http://localhost:8001/api/v1/auth/token/"
    data = {
        "username": "comptable1",
        "password": "comptable1@attawoune",
    }
    response = requests.post(url, json=data, timeout=10)
    print("Status Code:", response.status_code)
    print("Response Body:", response.text)


if __name__ == "__main__":
    main()
