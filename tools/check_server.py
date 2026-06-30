import time
import urllib.request
import sys
url='http://127.0.0.1:5000/'
for i in range(30):
    try:
        r=urllib.request.urlopen(url, timeout=3)
        print('UP', r.status)
        print(r.read(200).decode(errors='ignore'))
        sys.exit(0)
    except Exception as e:
        print('wait', i, str(e))
        time.sleep(1)
print('NOT_UP')
sys.exit(2)
