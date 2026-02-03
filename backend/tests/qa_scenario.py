import requests
import pandas as pd
import io
import time
import json

BASE_URL = "http://localhost:8000/api"

def print_pass(msg):
    print(f"✅ PASS: {msg}")

def print_fail(msg):
    print(f"❌ FAIL: {msg}")

def test_health():
    try:
        r = requests.get(f"{BASE_URL}/health")
        if r.status_code == 200:
            print_pass("Health check")
        else:
            print_fail(f"Health check status {r.status_code}")
    except Exception as e:
        print_fail(f"Health check exception: {e}")

def test_magic_upload():
    # Scenario: Upload CSV with missing headers, weird dates, messy numbers
    csv_content = """
    ColA, ColB, ColC, ColD
    Sugar, 10 pcs, 01/01/2026, 50
    Sugar, 5, 2026-01-02, 50
    Rice, 20 kg, 01-Jan-2026, 100
    """
    
    file = {'file': ('messy_data.csv', csv_content, 'text/csv')}
    
    print("\nTesting Magic Upload...")
    r = requests.post(f"{BASE_URL}/upload-sales", files=file)
    
    if r.status_code == 200:
        data = r.json()
        if data['success']:
            print_pass(f"Magic Upload accepted (Rows: {data['rows_processed']})")
            if data['store_id'] == 'STORE001':
                 print_pass("Default Store ID injected")
            else:
                 print_fail(f"Store ID mismatch: {data['store_id']}")
        else:
            print_fail(f"Upload failed: {data['errors']}")
            print(f"Full response: {json.dumps(data, indent=2)}")
    else:
        print_fail(f"API Error {r.status_code}: {r.text}")
        try:
             print(json.dumps(r.json(), indent=2))
        except:
             pass

def test_reorder_logic():
    # Check if reorder list was generated (Async might take a moment)
    print("\nWaiting for async pipeline...")
    time.sleep(2) 
    
    r = requests.get(f"{BASE_URL}/get-reorder-list?store_id=STORE001&horizon=7")
    if r.status_code == 200:
        data = r.json()
        items = data['items']
        print_pass(f"Reorder List retrieved ({len(items)} items)")
        
        # Validation Logic
        for item in items:
            # Reorder = Forecast + Buffer - Stock
            # If stock is known (it might be 0 default)
            print(f"  - {item['sku_name']}: Qty {item['reorder_qty']} (Reason: {item['reason']})")
            
            if item['reorder_qty'] < 0:
                print_fail("Negative reorder quantity found!")
            
    else:
        print_fail(f"Failed to get reorder list: {r.text}")

def main():
    print("🚀 Starting Extensive QA...")
    test_health()
    test_magic_upload()
    test_reorder_logic()

if __name__ == "__main__":
    main()
