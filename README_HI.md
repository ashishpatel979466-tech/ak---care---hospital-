# AK Care Hospital — Appointment Booking Starter

यह प्रोजेक्ट आपकी single HTML page को एक छोटे Flask backend और SQLite database से जोड़ता है।

## इसमें क्या है?
- Patient appointment request database में सेव होती है।
- Server-side validation: नाम, 10-digit phone, allowed department और future date.
- CSRF protection (forms), secure cookie flags, basic security headers.
- Admin login और appointments देखने/स्थिति बदलने का dashboard.
- Status: Pending, Confirmed, Cancelled, Completed.

## Windows पर लोकल में चलाएँ
1. Python 3.11 या नया Python install करें (install करते समय "Add Python to PATH" चुनें)।
2. इस folder को extract करें।
3. File Explorer में इस folder के अंदर address bar में `cmd` लिखकर Enter दबाएँ।
4. ये commands एक-एक करके चलाएँ:

```bat
py -m venv .venv
.venv\Scripts\activate
py -m pip install -r requirements.txt
set AKCARE_SECRET_KEY=put-a-long-random-secret-here
set AKCARE_ADMIN_USER=admin
set AKCARE_ADMIN_PASSWORD=choose-a-unique-long-password
py app.py
```

5. Browser में `http://127.0.0.1:5000` खोलें।
6. Admin panel: `http://127.0.0.1:5000/admin/login`
7. Admin username/password वही होंगे जो environment variables में सेट किए।

`set` commands केवल उस CMD window के लिए हैं। Server बंद करने के लिए Ctrl+C दबाएँ। SQLite file `appointments.db` इसी folder में बनेगी।

## macOS/Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export AKCARE_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
export AKCARE_ADMIN_USER="admin"
export AKCARE_ADMIN_PASSWORD="choose-a-unique-long-password"
python app.py
```

## Important before public launch
- यह starter project है; public hospital use से पहले professional deployment/security review जरूरी है।
- Production में HTTPS अनिवार्य करें और `AKCARE_HTTPS=1` सेट करें।
- `AKCARE_SECRET_KEY` को strong, private secret से सेट करें। Admin password unique और लंबा रखें; credentials GitHub या public code में न डालें।
- SQLite छोटे demo/local use के लिए है। Public/high-volume production के लिए managed PostgreSQL, encrypted backups, monitoring, updates, access controls और incident plan पर विचार करें।
- केवल आवश्यक patient data रखें; real patient data को demo/testing में न डालें। Access केवल authorized staff को दें।
- यहाँ email/SMS confirmations, doctor time-slot availability, duplicate-booking checks, cancellation links और audit log शामिल नहीं हैं।
- इस वेबसाइट के contact numbers, address, email, doctors, departments और emergency claims को publish करने से पहले hospital owner से verify करें। Emergency के लिए website booking पर निर्भर न रहें।
- Appointment request का status पहले `Pending` है; admin confirmation के बिना इसे confirmed appointment न समझें.
