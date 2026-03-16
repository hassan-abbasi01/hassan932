import requests
import json

# Test admin API endpoints
API_URL = 'http://localhost:5001'

print("\n" + "="*60)
print("TESTING ADMIN API ENDPOINTS")
print("="*60)

# First login to get token
print("\n1. LOGIN AS ADMIN...")
login_data = {
    'email': 'admin@snipx.com',
    'password': 'admin123'
}

response = requests.post(f'{API_URL}/api/admin/login', json=login_data)
print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")

if response.status_code == 200:
    data = response.json()
    token = data.get('token')
    
    if token:
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        # Test dashboard stats
        print("\n2. GET DASHBOARD STATS...")
        response = requests.get(f'{API_URL}/api/admin/dashboard/stats', headers=headers)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        # Test get users
        print("\n3. GET USERS LIST...")
        response = requests.get(f'{API_URL}/api/admin/users?page=1&limit=20', headers=headers)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
else:
    print("❌ Login failed! Cannot test other endpoints.")

print("\n" + "="*60 + "\n")
