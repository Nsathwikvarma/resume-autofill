import urllib.request
import urllib.parse
import json

url = "http://localhost:5000/api/extract-resume"
boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'

# Read file
with open('dummy.txt', 'rb') as f:
    file_bytes = f.read()

# Build multipart/form-data body
body = (
    f"--{boundary}\r\n"
    f"Content-Disposition: form-data; name=\"resume\"; filename=\"dummy.txt\"\r\n"
    f"Content-Type: text/plain\r\n\r\n"
).encode('utf-8') + file_bytes + f"\r\n--{boundary}--\r\n".encode('utf-8')

req = urllib.request.Request(url, data=body)
req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')

try:
    with urllib.request.urlopen(req) as response:
        print(f"Status Code: {response.status}")
        print(f"Response: {response.read().decode('utf-8')}")
except Exception as e:
    print(f"Failed: {e}")
    if hasattr(e, 'read'):
        print(e.read().decode('utf-8'))
