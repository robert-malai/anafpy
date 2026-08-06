# Instalarea anafpy pe un calculator nou

> 🇬🇧 This guide is also available [in English](setup.md).

Acest ghid te duce de la un calculator complet nou până la a discuta cu ANAF din
[Claude Cowork](https://claude.com) — să-ți listezi mesajele din e-Factura, să
depui declarații e-Transport, să cauți parteneri de afaceri. Este scris pentru un
contabil, nu pentru un programator: fiecare pas spune exact ce ai de făcut și ce
ar trebui să vezi, și nimic nu are nevoie de un terminal.

Vei face cinci lucruri, în ordine:

1. Înregistrezi o aplicație pe portalul ANAF (o singură dată, pe site-ul ANAF).
2. Instalezi Claude Desktop și extensia anafpy (un singur click).
3. Completezi setările extensiei.
4. Te autentifici la ANAF o dată, cu certificatul tău calificat — cerându-i lui
   Claude.
5. Verifici că funcționează.

Pașii 1–4 se fac o singură dată. Rezervă-ți în jur de 15 minute, plus cât
durează portalul ANAF.

## Înainte să începi

Ai nevoie de:

- **Certificatul tău digital calificat** (token-ul USB pe care îl folosești deja
  pentru SPV / declarațiile ANAF), conectat și funcțional în browser. Dacă te poți
  autentifica azi în SPV cu el, ești pregătit.
- **Înrolarea în SPV** pentru firmă (rolul SPV PJ) — din nou, dacă depui deja pentru
  firmă prin SPV, e gata.
- **CUI-ul** firmei (codul fiscal).

Un lucru de știut de la început: anafpy este gratuit și oferit **ca atare** (as-is),
iar suportul este pe cât se poate (best-effort). Aplicația pe care o înregistrezi pe
portalul ANAF la pasul 1 este **a ta** — te identifică la ANAF, nimeni nu o
operează în locul tău, iar menținerea ei (și a certificatului) în ordine este
responsabilitatea ta.

## Pasul 1 — Înregistrează o aplicație OAuth pe portalul ANAF

ANAF cere ca fiecare program care apelează API-urile sale să fie înregistrat. Faci
asta o singură dată, pe portal, cu certificatul tău:

1. **Înrolează-te ca utilizator API**: pe [anaf.ro](https://www.anaf.ro), mergi la
   *Servicii Online → Înregistrare utilizatori → Dezvoltatori aplicații →
   Înregistrare pentru API-uri*. ANAF îți trimite pe e-mail un cod de securitate
   pentru confirmare.
2. **Creează un profil de aplicație OAuth** (*Profil Oauth*):
   - **Denumire aplicație**: orice nume, de ex. `anafpy`.
   - **Callback URL 1**: exact `https://localhost:9002/callback` — atenție la
     **`https://`**; portalul respinge `http://`. Această adresă nu are nevoie
     niciodată de un server public; doar browserul tău o folosește.
   - **Serviciu**: bifează **E-Factura** și **E-Transport**.
3. Apasă **Generare Client ID**. Portalul afișează un **Client ID** și un **Client
   Secret**.

Copiază-le pe amândouă într-un manager de parole (sau notează-le undeva în
siguranță). Ele identifică aplicația *ta* la ANAF și vei avea nevoie de ele la
pasul 3. Nu sunt parola ta de SPV și nu înlocuiesc certificatul.

## Pasul 2 — Instalează Claude Desktop și extensia anafpy

Cowork ajunge la serverele locale prin aplicația Claude Desktop instalată pe același
calculator, așa că acest pas se face în Claude Desktop:

1. Instalează și autentifică-te în [Claude Desktop](https://claude.ai/download).
2. Descarcă extensia anafpy potrivită calculatorului tău de la
   [ultima versiune publicată](https://github.com/robert-malai/anafpy/releases/latest)
   (la secțiunea *Assets*): **`anafpy-darwin-arm64.mcpb`** pe un Mac cu Apple
   silicon (M1 sau mai nou), **`anafpy-darwin-x64.mcpb`** pe un Mac cu Intel
   (meniul Apple → *About This Mac* îți spune care), sau
   **`anafpy-win32-x64.mcpb`** pe Windows. Extensia este de sine stătătoare —
   vine cu propriul Python, nu mai trebuie instalat nimic altceva.
3. În Claude Desktop, deschide **Settings → Extensions**, trage fișierul
   `.mcpb` descărcat peste acea pagină (merge și dublu-click pe fișier)
   și apasă **Install**.

Uneltele anafpy apar la connectors/tools ale aplicației, iar sesiunile Cowork
de pe acest calculator le pot folosi. Chiar și înainte de orice configurare,
căutările publice funcționează deja — uneltele autentificate se deblochează în
următorii doi pași.

## Pasul 3 — Completează setările extensiei

În setările extensiei, completează primele trei câmpuri cu valorile tale de
la pasul 1: **ANAF Client ID**, **ANAF Client Secret** și **CUI-ul firmei**
(doar cifre — codul fiscal implicit folosit când nu spui altceva în
conversație). Secretul este păstrat în magazinul securizat de credențiale
al calculatorului. Câmpurile rămase acoperă cazuri rare (un callback URL
înregistrat diferit; remedierea curl pentru Windows din
[tabelul de depanare](#depanare)) — lasă-le goale.

## Pasul 4 — Autentifică-te la ANAF (o singură dată, cu certificatul)

Acesta este singurul pas care folosește certificatul. Conectează token-ul USB
și cere-i lui Claude, într-o conversație nouă:

> *„Autentifică-mă la ANAF."*

Claude îți cere confirmarea, apoi **browserul se deschide**. Ce se întâmplă,
în ordine:

1. Pagina de autentificare ANAF îți cere **certificatul** — alege-l și confirmă
   (introdu PIN-ul token-ului dacă ți se cere).
2. Browserul arată apoi un avertisment că conexiunea la `localhost` **nu este
   privată**. **Acest lucru este normal** — autentificarea creează un certificat
   de unică folosință pentru propriul tău calculator, ca să poată prinde
   răspunsul de la ANAF, iar browserele avertizează despre orice certificat
   nesemnat de o autoritate publică. Avertismentul nu are nicio legătură cu ANAF
   sau cu datele tale; este calculatorul tău vorbind cu el însuși.
3. Apasă **„Advanced"**, apoi **„Proceed to localhost"** (Chrome/Edge; Firefox:
   „Accept the Risk and Continue"). Browserul ajunge pe o pagină care spune că
   poți închide fila — gata, Claude confirmă autentificarea.

Token-urile sunt stocate în magazinul securizat de credențiale al calculatorului
(macOS Keychain / Windows Credential Manager). De aici înainte, totul este
automat: token-ul de acces se reînnoiește singur timp de aproximativ **un an**,
fără certificat. Repeți acest pas doar când expiră token-ul de reînnoire
(~365 de zile) sau dacă anulezi aplicația pe portalul ANAF — deci token-ul USB
este necesar cam **o dată pe an**.

(Aceeași autentificare există și ca o comandă de terminal, cu câteva opțiuni în
plus — vezi [ruta prin terminal](#ruta-prin-terminal) mai jos.)

## Pasul 5 — Verifică că funcționează

Întreabă-l pe Claude, într-o conversație nouă:

1. *„Care este statusul autentificării mele la ANAF?"* — ar trebui să raporteze un
   token valid (asta citește autentificarea de la pasul 4).
2. *„Caută CUI-ul 14399840 în registrul contribuabililor ANAF."* — căutările
   publice funcționează chiar și înainte de autentificare, deci asta confirmă că
   serverul însuși rulează.
3. *„Listează mesajele mele din e-Factura din ultimele 7 zile."* — confirmă
   conexiunea autentificată e-Factura de la un capăt la altul.

Pentru e-Transport, depunerea este intenționat în doi pași: Claude pregătește
declarația și îți arată o previzualizare, iar **nimic nu este depus până nu aprobi
explicit** — abia atunci trimite și raportează UIT-ul. Încearcă cerându-i lui
Claude să declare un transport dintr-o factură sau un CMR pe care le ai la îndemână.

## Pasul 6 (opțional) — Deblochează uneltele pentru cutia poștală SPV

Uneltele `spv_*` îi permit lui Claude să-ți citească **cutia poștală SPV**
(recipise, decizii, notificări) și să solicite rapoarte oficiale — vectorul fiscal,
obligațiile restante, istoricul declarațiilor, duplicatele de declarații,
adeverințele de venit. Sunt **doar pentru citire**: nimic nu poate fi depus prin
ele.

SPV se autentifică direct cu **certificatul tău calificat** (același pe care l-ai
folosit la autentificarea din browser de la pasul 4), deci acesta este un pas
separat, la fel de „aproape o singură dată" — diferența este că sesiunile SPV sunt
de scurtă durată (sub o oră de inactivitate), așa că refaci autentificarea când ai
nevoie data viitoare de SPV, nu anual.

Selecția inițială a certificatului folosește comanda de terminal `anafpy` —
instaleaz-o mai întâi ([ruta prin terminal](#ruta-prin-terminal) explică cum).

Pe **Windows**, rulează întâi `curl --version`: versiunile **8.13–8.15** ale
curl-ului încorporat strică autentificarea cu certificat la ANAF, iar
calculatoarele Windows-on-ARM au nevoie oricum de curl-ul din Git for Windows,
indiferent de versiune — aplică rezolvarea cu `ANAFPY_CURL` din
[tabelul de depanare](#depanare) *înainte* de prima încercare de autentificare,
ca să nu eșueze după ce ai introdus deja PIN-ul.

Într-un terminal:

```bash
anafpy spv certs                  # listează certificatele tale
anafpy spv select <thumbprint>    # alege-l pe al tău (id-ul hex din `certs`)
anafpy spv login                  # răspunde la solicitarea de PIN / 2FA a token-ului
```

Certificatele de tip token USB și cele din cloud (de ex. certSIGN vToken) apar în
`certs` prin middleware-ul lor propriu — trebuie să fie instalat și pornit, exact ca
pentru SPV în browser. Autentificarea poate eșua ocazional din partea ANAF; rulează
pur și simplu din nou (solicitarea ta de PIN/2FA se declanșează la fiecare încercare
— este normal).

Apoi întreabă-l pe Claude: *„Care este statusul meu SPV?"* — ar trebui să raporteze
certificatul tău și lista de firme (CUI-uri) pe care le poate interoga. Când sesiunea
expiră (inactivitatea le închide în sub o oră), poți pur și simplu să-i spui lui
Claude *„autentifică-mă în SPV"* — îți cere confirmarea, apoi se declanșează
solicitarea de PIN/2FA a token-ului tău ca de obicei; aprobând-o pe dispozitivul tău
finalizezi autentificarea. Comanda din terminal funcționează în continuare și ea.

## Pasul 7 (opțional) — Deblochează uneltele pentru declarații

Uneltele `declaratie_*` îi permit lui Claude să completeze, să valideze, să
genereze, să **semneze** și — cu aprobarea ta explicită la fiecare pas
important — să **depună** o declarație fiscală (decontul de TVA D300, D100,
D112 și orice alt formular acoperit de validatorul ANAF). Depunerea merge pe
portalul real al ANAF (declarațiile nu au un mediu de test) printr-un flux de
confirmare în doi pași, iar dacă preferi poți dezactiva depunerea complet cu
`ANAFPY_DECLARATII_UPLOAD: "off"` în blocul `env` al
[configurării manuale](#ruta-prin-terminal) — Claude îți predă atunci
PDF-ul semnat, iar tu îl încarci pe portal. Semnarea funcționează pe macOS și pe
Windows, cu certificatul din magazinul de certificate al sistemului.

Aceste unelte rulează validatorul desktop al ANAF, **DUKIntegrator** — iar
anafpy îl instalează pentru tine:

1. Asigură-te că ai **Java** instalat (un JRE/JDK, versiunea 8 sau mai nouă) —
   `java -version` într-un terminal ar trebui să afișeze o versiune. (anafpy
   rulează doar pașii de *validare* și de *generare a PDF-ului* din
   DUKIntegrator, care funcționează pe orice JVM modern; limitarea „doar Java 8"
   despre care poți citi se referă la semnarea proprie a DUK, pe care anafpy nu
   o folosește. Instalat, dar comanda nu este găsită? anafpy se uită și la
   `JAVA_HOME`, pe care instalatoarele de Java pentru Windows îl setează de
   obicei.)
2. Cere-i lui Claude *„instalează validatorul de declarații"* — apelează
   `declaratie_duk_install`, care descarcă DUKIntegrator și validatoarele
   formularelor uzuale direct din fluxul oficial de actualizare al ANAF în
   `~/.anafpy/duk-dist`. Fiecare fișier vine de pe `static.anaf.ro` prin HTTPS,
   iar un manifest consemnează ce s-a instalat, de unde, cu sume de control.
   Aceeași comandă există și în terminal ca `anafpy duk install`, iar
   validatorul unui formular mai rar este la un `anafpy duk install D208`
   distanță — Claude poate face asta și în mijlocul unei sarcini.

Nu este nevoie de nicio intrare de configurare pentru asta: serverul găsește
singur instalarea gestionată. (Ai deja propriul tău folder `dist/` de
DUKIntegrator? Direcționează `ANAFPY_DUK_DIR` către el în blocul `env` al
configurării manuale — un folder explicit are întotdeauna prioritate față de
cel gestionat.)

Repornește Claude și cere-i *„verifică instalarea pentru declarații"* — Claude
rulează `declaratie_duk_status`, care confirmă instalarea și te avertizează dacă
un validator este învechit (DUKIntegrator în linie de comandă nu se actualizează
singur, spre deosebire de fereastra sa desktop — Claude rezolvă asta cu
`declaratie_duk_install`, iar echivalentul din terminal este
`anafpy duk update`). Semnarea folosește **același certificat calificat** ca
SPV (pasul 6): dacă ai selectat unul acolo, semnatarul de declarații îl
refolosește; altfel setează `"ANAFPY_SIGN_IDENTITY"` — pe macOS la numele
certificatului din Keychain, pe Windows la amprenta lui (codul de 40 de
caractere pe care îl listează `anafpy spv certs`). Când Claude semnează, te
avertizează mai întâi, apoi se declanșează solicitarea de PIN/2FA a token-ului
tău — aprobând-o pe dispozitivul tău obții PDF-ul semnat.

## Pasul 8 (opțional) — Instalează skill-urile de lucru

Extensia îi dă lui Claude uneltele individuale; plugin-ul **anafpy workflows**
adaugă peste ele [playbook-urile de lucru](skills.md) — rețete în mai mulți
pași pe care Claude le urmează singur când îi ceri în limbaj obișnuit:

- **`etransport-declare`** — depune o declarație e-Transport și obține UIT-ul
  pornind de la orice sursă (un e-mail, o factură PDF, un CMR), cu garanțiile
  legale incluse. Funcționează cu instalarea de bază (pașii 1–4).
- **`declaratie-prepare`** — construiește, validează, semnează și depune o
  declarație fiscală din date-sursă nestructurate (are nevoie de pasul 7).
- **`personal-income-summary`** — adună adeverințele de venit anuale din SPV
  și le rezumă (are nevoie de pasul 6).

Pentru instalare, în Claude Desktop (sau în Cowork pe web):

1. Apasă butonul **+** de lângă caseta de mesaje și alege
   **Plugins → Add plugin**.
2. Adaugă acest marketplace:

    ```text
    robert-malai/anafpy
    ```

3. Instalează de acolo plugin-ul **anafpy workflows**.

Skill-urile se declanșează apoi singure — este de ajuns să ceri *„declară
transportul acesta din factura atașată"*; apar și în lista de skill-uri. Fără
plugin, aceleași playbook-uri rămân accesibile, doar manual: extensia le
servește ca prompt-uri în meniul **+** din Claude Desktop.

## Ruta prin terminal

Nimic de mai sus nu are nevoie de un terminal. Unealta în linie de comandă
există pentru pașii opționali (selecția certificatului SPV de la pasul 6),
pentru opțiunile pe care setările extensiei nu le expun și pentru dezvoltatorii
care preferă să lege serverul manual.

### Instalează unealta în linie de comandă

Instalează mai întâi [`uv`](https://docs.astral.sh/uv/) — se ocupă de Python în
locul tău (**nu** trebuie să instalezi Python separat). Deschide un terminal —
**Terminal** pe macOS, **PowerShell** pe Windows — și rulează:

**macOS**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell)**

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Închide și redeschide terminalul, apoi:

```bash
uv tool install "anafpy[mcp]"
```

Comanda descarcă anafpy de pe [PyPI](https://pypi.org/project/anafpy/) și
instalează două comenzi: `anafpy` (CLI-ul) și `anafpy-mcp` (același server pe
care îl împachetează extensia, pentru configurarea manuală de mai jos). Ele
ajung în `~/.local/bin` pe macOS și în `%USERPROFILE%\.local\bin` pe Windows.
Ca să actualizezi mai târziu: `uv tool upgrade anafpy`. (Dezvoltatorii care
preferă să ruleze dintr-un checkout al sursei: vezi
[README-ul](https://github.com/robert-malai/anafpy#install).)

### Autentificarea, din terminal

Geamănul din terminal al autentificării de la pasul 4 (același flux din
browser, același magazin de token-uri):

```bash
anafpy auth login --client-id <CLIENT_ID> --client-secret <CLIENT_SECRET>
```

Adresa de callback are ca valoare implicită
`https://localhost:9002/callback`, exact cea înregistrată la pasul 1 —
folosește `--redirect-uri` doar dacă ai înregistrat alta. Verifică dacă a
funcționat cu `anafpy auth status`.

Dacă ascultătorul (listener) nu poate porni din orice motiv — sau nu sosește
nimic la timp — comanda revine singură la **modul copiere**: browserul ajunge pe
o pagină de eroare și tu copiezi adresa (URL) completă din bara de adrese în
terminalul care o așteaptă, în aproximativ **60 de secunde**. (Poți alege acest
mod și direct, cu `--paste`.)

??? tip "Opțional: elimină avertismentul din browser (mkcert)"

    Dacă te deranjează click-ul pe avertisment o dată pe an, fă `https://localhost`
    real pe acest calculator cu [mkcert](https://github.com/FiloSottile/mkcert) —
    o unealtă mică ce creează certificate în care propriul tău calculator are
    încredere (sunt valabile **doar pe acest calculator**; nimic nu iese din el):

    **macOS** (prin [Homebrew](https://brew.sh)): `brew install mkcert` —
    **Windows (PowerShell)**: `winget install FiloSottile.mkcert`

    Apoi, redeschide terminalul și (o singură dată):

    ```bash
    mkcert -install          # adaugă autoritatea mkcert în magazinul de încredere al calculatorului — confirmă solicitarea de parolă/UAC
    mkcert localhost 127.0.0.1
    ```

    Acest lucru scrie `localhost+1.pem` și `localhost+1-key.pem` în folderul
    curent; adaugă-le la comanda de autentificare, rulată din același folder:

    ```bash
    anafpy auth login --client-id <CLIENT_ID> --client-secret <CLIENT_SECRET> \
      --tls-cert localhost+1.pem --tls-key localhost+1-key.pem
    ```

    Autentificarea se finalizează atunci în browser fără niciun avertisment.

### Configurare manuală (în locul extensiei — și pentru mediul de TEST)

Extensia este o comoditate peste fișierul de configurare al Claude Desktop;
poți lega serverul și manual (deocamdată, doar așa se pot seta opțiuni
suplimentare precum `ANAFPY_ENV`, `ANAFPY_SIGN_IDENTITY` sau
`ANAFPY_DECLARATII_UPLOAD`):

1. Deschide fișierul de configurare (creează-l dacă lipsește):
    - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
      (în Claude Desktop: *Settings → Developer → Edit Config*)
    - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
2. Adaugă acest text (înlocuiește cele trei valori `...` și pune în `"command"`
   calea completă a comenzii `anafpy-mcp` instalate; pe Windows scrie-o cu
   backslash dublat, de ex. `C:\\Users\\ana\\.local\\bin\\anafpy-mcp.exe`):

    ```json
    {
      "mcpServers": {
        "anafpy": {
          "command": "/Users/ana/.local/bin/anafpy-mcp",
          "env": {
            "ANAFPY_CLIENT_ID": "...",
            "ANAFPY_CLIENT_SECRET": "...",
            "ANAFPY_CIF": "12345678"
          }
        }
      }
    }
    ```

3. Închide complet Claude Desktop și redeschide-l — citește acest fișier
   doar la pornire.

### Claude Code

Dacă folosești Claude Code într-un terminal:

```bash
claude mcp add anafpy \
  -e ANAFPY_CLIENT_ID=... -e ANAFPY_CLIENT_SECRET=... -e ANAFPY_CIF=... \
  -- anafpy-mcp
```

## Bine de știut

- **Producție vs. test**: serverul vorbește implicit cu ANAF **producție**. Ca să
  exersezi în schimb pe mediul de **TEST** al ANAF, adaugă `"ANAFPY_ENV": "test"`
  lângă celelalte intrări din `env` — asta cere
  [configurarea manuală](#ruta-prin-terminal); extensia nu expune `ANAFPY_ENV`
  (depunerile de test emit UIT-uri care arată real dar nu au valoare juridică).
- **Credențialele tale rămân pe acest calculator**: cu extensia, Client
  Secret-ul și token-urile stau în magazinul de credențiale al sistemului
  (macOS Keychain / Windows Credential Manager); cu configurarea manuală,
  secretul stă în fișierul de configurare — protejează contul de pe calculator
  așa cum îți protejezi accesul la SPV.
- **Token-uri într-un fișier în loc de keychain**: necesar doar pe gazde fără un
  magazin de credențiale (de ex. un server Linux sau Docker). Rulează
  autentificarea din terminal cu `--store-backend file` adăugat și pune
  `"ANAFPY_TOKEN_STORE_BACKEND": "file"` lângă celelalte intrări din `env` în
  configurarea Claude; token-urile stau atunci în `~/.anafpy/tokens.json` —
  protejează acel folder.
- **Sesiunile SPV sunt scurte**: spre deosebire de token-urile OAuth (anuale),
  sesiunea SPV pe cookie se închide după mult sub o oră de inactivitate. Este
  setarea ANAF, nu a ta; spune-i lui Claude *„autentifică-mă în SPV"* (sau
  rulează `anafpy spv login`) oricând ți-o cer uneltele `spv_*`.
- **Reînnoirea anuală**: când uneltele încep să eșueze cu un mesaj de tip
  „autentifică-te la ANAF" după ~un an, repetă pasul 4. Nimic altceva nu
  trebuie schimbat.
- **Deautentificare** (când lași un calculator partajat, îl predai către IT): rulează
  `anafpy auth logout` într-un terminal (are nevoie de
  [unealta în linie de comandă](#ruta-prin-terminal)). Șterge token-urile de pe
  acest calculator — după aceea uneltele răspund „autentifică-te la ANAF" până
  când cineva se autentifică din nou cu certificatul. (ANAF nu oferă nicio
  modalitate ca un program să anuleze token-urile din partea sa; ele expiră
  singure. Ca să întrerupi totul și din partea ANAF, folosește *Renunțare
  Oauth* în portalul ANAF, care șterge întreaga înregistrare a aplicației.)

## Depanare

| Simptom | Rezolvare |
|---|---|
| Avertismentul *„Connection is not private"* la `localhost` în timpul autentificării | Normal cu autentificarea implicită — certificatul de unică folosință este al propriului tău calculator. Apasă **Advanced → Proceed to localhost** și autentificarea se finalizează. (Cu certificate mkcert înseamnă că `mkcert -install` nu s-a finalizat — are nevoie de confirmarea de parolă/UAC; rulează-l din nou, apoi reîncearcă.) |
| Dialogul de instalare al extensiei nu apare | Trage fișierul `.mcpb` peste pagina **Settings → Extensions** din Claude Desktop, în loc de dublu-click. |
| `mkcert: command not found` imediat după ce l-ai instalat | Închide și redeschide terminalul ca noua unealtă să fie preluată, apoi reîncearcă. |
| Autentificarea spune că nu poate citi `localhost+1.pem` (mkcert) | Rulează comanda de autentificare din folderul în care `mkcert` a scris fișierele de certificat — sau dă calea lor completă. |
| Pagină de eroare în browser după pasul cu certificatul (autentificarea din terminal) | Normal în modul `--paste` (sau după ce ascultătorul a revenit singur la el) — copiază adresa (URL) din bara de adrese în terminal. |
| Cod „expired" / invalid la lipire | Ai așteptat peste ~60 s. Rulează comanda de autentificare din nou și lipește repede. |
| Nicio solicitare de certificat în browser | Driverul/software-ul token-ului nu este instalat sau browserul nu vede certificatul. Testează autentificându-te întâi în SPV; rezolvă acolo, apoi reîncearcă. |
| `anafpy: command not found` în terminal | Închide și redeschide terminalul ca noile comenzi să fie preluate; dacă persistă, rulează `uv tool update-shell`, apoi redeschide din nou. |
| Claude Desktop arată serverul ca eșuat / `anafpy-mcp` nu este găsit (configurarea manuală) | Aplicațiile desktop nu văd întotdeauna PATH-ul terminalului. În configurare, `"command"` trebuie să fie calea completă — macOS: `/Users/<tu>/.local/bin/anafpy-mcp`; Windows: `C:\\Users\\<tu>\\.local\\bin\\anafpy-mcp.exe` (rulează `which anafpy-mcp` / `where.exe anafpy-mcp` ca să confirmi). |
| Uneltele răspund „autentifică-te la ANAF" | Pasul 4 nu a fost finalizat pe acest calculator, sau token-ul a expirat (~1 an). Rulează din nou pasul 4. |
| Depunere respinsă de ANAF | Acesta este verdictul ANAF asupra conținutului documentului, nu o problemă de instalare — textul erorii revine în rezultatul uneltei; corectează datele și pregătește din nou. |
| `anafpy spv login` eșuează instant cu `SEC_E_UNKNOWN_CREDENTIALS` pe un calculator Windows-on-ARM (de ex. Parallels pe un Mac) | Software-ul furnizorului de certificat este doar pentru Intel (certSIGN vToken este), deci curl-ul încorporat în Windows nu poate folosi certificatul. Instalează [Git for Windows](https://git-scm.com/download/win) (versiunea pe **64 de biți**, nu ARM64) și lipește `C:\Program Files\Git\mingw64\bin\curl.exe` în câmpul de setări **curl program (Windows fix)** al extensiei (configurarea manuală: `"ANAFPY_CURL"` cu backslash dublat, lângă celelalte intrări din `env`); setează aceeași variabilă în PowerShell înainte de `anafpy spv login`. |
| `anafpy spv login` eșuează cu `schannel: failed to read data from server: SEC_E_CONTEXT_EXPIRED (0x80090317)` pe Windows | Curl-ul încorporat în Windows (`C:\Windows\System32\curl.exe`) versiunile **8.13–8.15** au o [eroare Schannel](https://github.com/curl/curl/issues/18029) care strică renegocierea TLS a ANAF cu un certificat din magazinul de certificate. Verifică cu `curl --version`; dacă este în acest interval, instalează [Git for Windows](https://git-scm.com/download/win) (curl-ul lui inclus este mai nou) și direcționează câmpul de setări **curl program (Windows fix)** al extensiei către `C:\Program Files\Git\mingw64\bin\curl.exe` (configurarea manuală: `"ANAFPY_CURL"` în blocul `env`) și setează aceeași variabilă în PowerShell înainte de `anafpy spv login` (rulează `cygpath -w "$(command -v curl)"` în Git Bash ca să afli calea exactă). anafpy fixează backend-ul Schannel pentru tine. |
