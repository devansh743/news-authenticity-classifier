from app import app
import uuid

c=app.test_client()
unique=str(uuid.uuid4())[:8]
email=f'tmp_{unique}@example.com'
r=c.post('/register', data={'username':'u'+unique,'email':email,'password':'pass1234'}, follow_redirects=True)
print('register_status', r.status_code)
news='President announced a major economic policy today that will affect the economy and millions of people. The minister said the policy will be effective next month and analysts expect significant changes.'
resp=c.post('/dashboard', data={'news': news}, follow_redirects=True)
html=resp.get_data(as_text=True)
start=html.find('<div class="result-box')
if start!=-1:
    end=html.find('</div>', start)
    print('snippet:', html[start:end+6])
else:
    print('No result-box found; full response length', len(html))
