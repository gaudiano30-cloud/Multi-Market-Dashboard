"""Configurazione centralizzata; instance/ non va versionata.
un unico modulo che conserva le impostazioni condivise dagli altri moduli di autenticazione.
Le tre responsabilità principali di settings.py sono:
- Definire dove si trovano i file e le cartelle.
- Stabilire i tempi di validità delle sessioni e delle verifiche.
- Gestire la chiave segreta dell'applicazione e preparare lo strumento per cifrare i segreti OTP."""

import base64  # base64 è una libreria standard di Python che permette di rappresentare dati binari mediante caratteri testuali.
import hashlib  # hashlib è un modulo standard di Python che contiene diverse funzioni di hashing. Un hash è il risultato di una trasformazione matematica che prende dei dati in ingresso e produce un valore di lunghezza fissa.
import os
import secrets  # libreria serve a generare valori casuali adatti a utilizzi di sicurezza

# A differenza di molte funzioni del modulo random, secrets è progettato per generare valori difficili da prevedere.
from pathlib import Path

# Path permette di rappresentare percorsi di file e cartelle come oggetti Python.
from cryptography.fernet import Fernet

# cryptography è una libreria esterna che contiene strumenti crittografici.
# Fernet è un sistema di cifratura simmetrica autenticata.
# Fernet è utilizzato per proteggere i segreti OTP, non per salvare le password.

ROOT = Path(__file__).resolve().parent.parent
# Assegna a ROOT il percorso della cartella principale del progetto.
INSTANCE = ROOT / "instance"
# La cartella instance serve a conservare informazioni private dell'installazione.
# Nel nostro caso conterrà la chiave segreta del server.

DB_PATH = ROOT / "database" / "users_auth.sqlite3"  # costruisce il percorso del database degli utenti:
# questa riga non crea il database SQLite. Definisce soltanto dove deve trovarsi.

SECRET_PATH = INSTANCE / ".flask-secret"
# Questa riga stabilisce dove salvare la chiave segreta dell'applicazione.
# i file il cui nome inizia con . sono normalmente nascosti nelle visualizzazioni standard.
# Ma un file nascosto non è automaticamente sicuro. Per questo il codice imposta anche permessi di accesso specifici, che vedremo tra poco.

SESSION_IDLE_SECONDS = (
    30 * 60
)  # indica quanto può durare l'inattività prima che una sessione venga considerata scaduta.
SESSION_MAX_SECONDS = (
    8 * 60 * 60
)  # indica la durata massima assoluta della sessione, anche se l'utente continua a utilizzare la dashboard.
SIGNIN_CHALLENGE_SECONDS = (
    5 * 60
)  # è il tempo disponibile per completare l'OTP dopo aver verificato correttamente username e password.
SIGNUP_CHALLENGE_SECONDS = (
    15 * 60
)  # è il tempo disponibile per completare la registrazione configurando l'Authenticator.
# Le costanti vengono poi utilizzate dai moduli storage.py e views.py


def load_secret_key() -> str:
    """Questa funzione è responsabile di recuperare o generare la chiave segreta dell'applicazione.
    La chiave segreta dell'applicazione è una credenziale tecnica che Python utilizza dietro le quinte per proteggere il funzionamento dell'autenticazione.
    Chiave permanente da variabile d'ambiente oppure file privato 0600."""
    INSTANCE.mkdir(parents=True, exist_ok=True)
    configured = os.environ.get("MFE_SECRET_KEY")
    if configured:
        if len(configured) < 32:
            raise RuntimeError("MFE_SECRET_KEY deve contenere almeno 32 caratteri casuali.")
        return configured
    try:
        fd = os.open(str(SECRET_PATH), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        pass
    else:
        with os.fdopen(fd, "w", encoding="ascii") as stream:
            stream.write(secrets.token_urlsafe(48))
    if os.name == "posix":
        SECRET_PATH.chmod(0o600)
    return SECRET_PATH.read_text(encoding="ascii").strip()


def secret_cipher(key: str) -> Fernet:
    # Derivazione separata dalla chiave di firma cookie.
    raw = hashlib.sha256(("mfe-totp-secret-v1:" + key).encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(raw))
