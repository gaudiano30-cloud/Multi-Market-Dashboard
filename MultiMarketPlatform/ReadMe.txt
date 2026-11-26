MULTIMARKETPLATFORM - MERGE LOCALE DASHBOARD + 2FA
=====================================================

1. COSA CAMBIA
  - main.py: il tuo app.py completo, con un'unica chiamata alla factory 2FA.
  - style.py: il tuo file di stile, con il link Esci.
  - authentication/: contiene TUTTA la logica del login, Sign up, password, OTP,
    sessioni, protezione delle API e pagine HTML.
  - database/market_data.db: resta il TUO database finanziario (non incluso nello ZIP).
  - database/users_auth.sqlite3: database LOCALE utenti, creato automaticamente.
  - instance/.flask-secret: chiave privata locale creata al primo avvio.

2. INSTALLAZIONE NEL TUO PROGETTO GIA' ESISTENTE (IMPORTANTE)
  A) Fai copia di sicurezza della cartella dashboard/ originale.
  B) Apri la cartella con app.py, style.py, analytics/, assets/,
     database/ e providers/ (quella della tua schermata).
  C) Copia in essa SOLO i seguenti elementi del nuovo ZIP:
       main.py, style.py, authentication/, requirements.txt, .gitignore
     Mantieni assets/MFEimage.png e config.py esistenti (oppure usa il logo incluso).
     NON eliminare/sostituire analytics/, providers/, database/ e market_data.db.
  D) Il vecchio app.py puo' restare come backup, ma usa SOLO python main.py
     per la versione protetta. Evita di avviare app.py: non ha il login!

3. PRIMO AVVIO SU MAC (TERMINALE)
  cd /percorso/della/tua/MultiMarketPlatform
  python3 -m venv .venv                      # solo la prima volta
  source .venv/bin/activate
  python -m pip install -r requirements.txt
  python main.py
  Apri http://127.0.0.1:8050/
  Se hai gia' un .venv, salta la creazione.

4. COME FUNZIONA
  Apri / -> vieni reindirizzato a /auth/ (Benvenuto con logo).
  Sign up -> username+password -> QR OTP -> primo codice -> dashboard.
  Sign in -> username+password -> codice OTP -> dashboard.
  Esci -> conferma logout -> sessione revocata sul server.
  Tutti gli endpoint Dash (inclusi _dash-layout e _dash-update-component)
  sono negati con 401 fino alla verifica OTP.

5. DOVE SONO SALVATI GLI UTENTI
  database/users_auth.sqlite3 in tabelle utenti, sessioni e limiti ai tentativi.
  Password: SOLO hash Argon2id; mai password in chiaro.
  OTP: segreto TOTP cifrato con una chiave derivata dalla chiave privata.
  Sessioni: token casuale il cui hash e' memorizzato nel DB, con scadenza.
  Chiave di cifratura: instance/.flask-secret (NON cancellare e NON condividere).
  Questi dati sono LOCALI e NON si sincronizzano fra PC.
  Se una copia del progetto viene distribuita, ogni PC crea i propri utenti.
  Per condivisione fra computer serviranno, in futuro, un backend online
  e un archivio utenti centralizzato: questa versione NON usa Render.

6. SICUREZZA E LIMITI
  E' un prototipo locale universitario con 2FA reale e controlli lato server.
  Host 127.0.0.1 e debug=False; non esporre l'app su Internet in questa forma.
  Prima di pubblicare online: HTTPS, segreti in ambiente protetto, revisione
  sicurezza, backup delle chiavi e database, monitoraggio.
  Non committare users_auth.sqlite3, instance/ o .env.
  Se perdi instance/.flask-secret gli OTP gia' registrati potrebbero non
  essere piu' decifrabili. Non cancellare la chiave per 'resettare' utenti.

7. TEST
  python -m pytest -q tests
  Il test HTTP richiede Dash, Flask e qrcode installati.

8. STRUTTURA FINALE
  MultiMarketPlatform/
    main.py
    style.py
    config.py                       (tuo file)
    README.txt
    requirements.txt
    assets/MFEimage.png
    authentication/ ...
    analytics/metrics.py              (tuo file)
    providers/...                     (tuoi file)
    database/connection.py            (tuo file)
    database/market_data.db           (tuo file)
    database/users_auth.sqlite3       (creato automaticamente)
    instance/.flask-secret            (creato automaticamente)

Per avviare usa python main.py, NON python app.py.
