import sys
import os
import uuid

# ensure project root is on sys.path so we can import app
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import app

c = app.test_client()
unique = str(uuid.uuid4())[:8]
email = f'tbx_{unique}@example.com'
username = 'u' + unique
# register
print('Registering', username, email)
r = c.post('/register', data={'username': username, 'email': email, 'password': 'pass1234'}, follow_redirects=True)
print('Register status:', r.status_code)
print('Register HTML snippet:', r.get_data(as_text=True)[:400])
# submit URL from screenshot (BBC link example)
url = 'https://www.bbc.co.uk/news/articles/c8721jel283o'
r2 = c.post('/dashboard', data={'url': url}, follow_redirects=True)
html = r2.get_data(as_text=True)
print('STATUS:', r2.status_code)
print('HTML length:', len(html))
print('---HTML START---')
print(html[:8000])
print('---HTML END---')
