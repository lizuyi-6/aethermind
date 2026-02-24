import urllib.request
import urllib.error

try:
    req = urllib.request.Request('http://127.0.0.1:5000/api/v1/admin/config/llm')
    response = urllib.request.urlopen(req)
    print("SUCCESS:", response.status)
    print(response.read().decode())
except urllib.error.HTTPError as e:
    print("HTTP ERROR:", e.code)
    try:
        print(e.read().decode())
    except:
        print(e.read())
except Exception as e:
    print("OTHER ERROR:", e)
