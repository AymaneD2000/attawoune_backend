
import requests
import json
import sys

BASE_URL = "http://lk40s80skcocogs4kkogcgc4.62.171.157.196.sslip.io"
API_URL = f"{BASE_URL}/api"

def print_result(name, success, details=None):
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} - {name}")
    if details:
        print(f"   {details}")

def test_backend_connectivity():
    print(f"\n--- Testing Backend Connection: {BASE_URL} ---")
    try:
        # Test root URL (might just return 404 or welcome page, but connection should work)
        response = requests.get(BASE_URL, timeout=10)
        # We know it returns 400 Bad Request if Host header issues, but we fixed ALLOWED_HOSTS.
        # If it works now, it should return 200 or 404.
        
        # Actually, let's test the admin page which we know exists
        admin_url = f"{BASE_URL}/admin/login/"
        response = requests.get(admin_url, timeout=10)
        
        if response.status_code == 200:
            print_result("Backend Connectivity", True, f"Status: {response.status_code}")
            return True
        else:
            print_result("Backend Connectivity", False, f"Status: {response.status_code}")
            return False
            
    except Exception as e:
        print_result("Backend Connectivity", False, f"Error: {str(e)}")
        return False

def test_authentication():
    print("\n--- Testing Authentication ---")
    login_url = f"{API_URL}/auth/token/"
    credentials = {
        "username": "admin",
        "password": "Admin@2025!"
    }
    
    try:
        response = requests.post(login_url, json=credentials, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            access_token = data.get("access")
            refresh_token = data.get("refresh")
            
            if access_token and refresh_token:
                print_result("Login (Get Token)", True)
                return access_token
            else:
                print_result("Login (Get Token)", False, "Missing tokens in response")
                return None
        else:
            print_result("Login (Get Token)", False, f"Status: {response.status_code}, Body: {response.text}")
            return None
            
    except Exception as e:
        print_result("Login (Get Token)", False, f"Error: {str(e)}")
        return None

def test_teachers_endpoint(access_token):
    print("\n--- Testing Teachers Endpoint ---")
    teachers_url = f"{API_URL}/teachers/teachers/"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    try:
        response = requests.get(teachers_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            count = data.get("count", 0)
            results = data.get("results", [])
            
            print_result("Fetch Teachers List", True, f"Found {count} teachers")
            
            if len(results) > 0:
                teacher_id = results[0]["id"]
                # Test teacher details
                detail_url = f"{teachers_url}{teacher_id}/"
                detail_response = requests.get(detail_url, headers=headers, timeout=10)
                
                if detail_response.status_code == 200:
                    print_result("Fetch Teacher Details", True, f"ID: {teacher_id}")
                else:
                    print_result("Fetch Teacher Details", False, f"Status: {detail_response.status_code}")
            
            return True
        else:
            print_result("Fetch Teachers List", False, f"Status: {response.status_code}, Body: {response.text}")
            return False
            
    except Exception as e:
        print_result("Fetch Teachers List", False, f"Error: {str(e)}")
        return False

def main():
    if test_backend_connectivity():
        token = test_authentication()
        if token:
            test_teachers_endpoint(token)
        else:
            print("\n❌ Skipping authenticated tests due to login failure.")
    else:
        print("\n❌ Skipping remaining tests due to connectivity failure.")

if __name__ == "__main__":
    main()
