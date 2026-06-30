import sys, os, uuid
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from app import app

c = app.test_client()
unique = str(uuid.uuid4())[:8]
email = f'e2e_{unique}@example.com'
username = 'u' + unique
print('Registering', username, email)
r = c.post('/register', data={'username': username, 'email': email, 'password': 'pass1234'}, follow_redirects=True)
print('Register status', r.status_code)

# Use a realistic news text with keywords so is_news passes
news_text = ('President announced a major economic policy today that will affect the economy and millions of people. '
             'The minister said the policy will be effective next month and analysts expect significant changes. '
             'Experts from the government and independent companies commented on the expected impact and percent estimates.')

resp = c.post('/api/analyze', data={'news': news_text})
data = resp.get_json()
print('API status', resp.status_code)
print('API response:', data)
# end
