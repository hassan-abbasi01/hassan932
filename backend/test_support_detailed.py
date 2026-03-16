import requests
import json
import traceback

API_URL = 'http://localhost:5001'

print("\n" + "="*60)
print("DETAILED SUPPORT ENDPOINT TEST")
print("="*60)

# Login
print("\n1. Admin login...")
try:
    response = requests.post(f'{API_URL}/api/admin/login', 
                            json={'email': 'admin@snipx.com', 'password': 'admin123'})
    print(f"Login status: {response.status_code}")
    
    if response.status_code == 200:
        token = response.json().get('token')
        headers = {'Authorization': f'Bearer {token}'}
        
        print("\n2. Testing /api/support/all endpoint...")
        try:
            resp = requests.get(f'{API_URL}/api/support/all', headers=headers)
            print(f"Status: {resp.status_code}")
            print(f"Response Headers: {resp.headers}")
            print(f"Response Text: {resp.text[:500]}")
            
            if resp.status_code == 200:
                data = resp.json()
                print(f"\n✅ SUCCESS!")
                print(f"Tickets returned: {len(data.get('tickets', []))}")
                print(json.dumps(data, indent=2, default=str))
            else:
                print(f"❌ FAILED")
                
        except Exception as e:
            print(f"Exception: {e}")
            traceback.print_exc()
    else:
        print("Login failed!")
        
except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()

print("\n" + "="*60 + "\n")
