import requests
import json

API_URL = 'http://localhost:5001'

print("\n" + "="*60)
print("TEST SUPPORT ENDPOINTS")
print("="*60)

# Get admin token
print("\n1. LOGIN AS ADMIN...")
login_data = {
    'email': 'admin@snipx.com',
    'password': 'admin123'
}
response = requests.post(f'{API_URL}/api/admin/login', json=login_data)
print(f"Status: {response.status_code}")

if response.status_code == 200:
    token = response.json().get('token')
    headers = {'Authorization': f'Bearer {token}'}
    
    # Try different endpoints
    endpoints = [
        '/api/support/all',
        '/api/admin/support/tickets',
        '/api/support/tickets',
    ]
    
    print("\n2. TESTING SUPPORT ENDPOINTS...")
    for endpoint in endpoints:
        print(f"\nTrying: {endpoint}")
        resp = requests.get(f'{API_URL}{endpoint}', headers=headers)
        print(f"  Status: {resp.status_code}")
        if resp.status_code == 200:
            print(f"  ✅ WORKS!")
            print(f"  Response: {json.dumps(resp.json(), indent=2)[:200]}")
        else:
            print(f"  ❌ FAILED: {resp.text[:100]}")

print("\n" + "="*60 + "\n")
