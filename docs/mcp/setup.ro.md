# Instalarea anafpy pe un calculator nou

> 🇬🇧 This guide is also available [in English](setup.md).

Acest ghid te duce de la un calculator complet nou până la a discuta cu ANAF din
[Claude Cowork](https://claude.com) — să-ți listezi mesajele din e-Factura, să
depui declarații e-Transport, să cauți parteneri de afaceri. Este scris pentru un
contabil, nu pentru un programator: fiecare comandă este dată în întregime, iar
fiecare pas spune ce ar trebui să vezi.

Vei face cinci lucruri, în ordine:

1. Înregistrezi o aplicație pe portalul ANAF (o singură dată, pe site-ul ANAF).
2. Instalezi două unelte mici: `git` și `uv`.
3. Descarci anafpy.
4. Te autentifici la ANAF o dată, cu certificatul tău calificat.
5. Conectezi serverul la Claude și verifici că funcționează.

Pașii 1–4 se fac o singură dată. Rezervă-ți în jur de 30 de minute, plus cât
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
siguranță). Ele identifică aplicația *ta* la ANAF și vei avea nevoie de ele la pașii
4 și 5. Nu sunt parola ta de SPV și nu înlocuiesc certificatul.

## Pasul 2 — Instalează git și uv

Deschide un terminal — **Terminal** pe macOS, **PowerShell** pe Windows (apasă
Start, scrie „PowerShell") — și rulează:

**macOS**

```bash
xcode-select --install                                 # instalează git (sari peste dacă git --version merge deja)
curl -LsSf https://astral.sh/uv/install.sh | sh        # instalează uv
```

**Windows (PowerShell)**

```powershell
winget install --id Git.Git -e
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Închide și redeschide terminalul, apoi verifică că amândouă răspund:

```bash
git --version
uv --version
```

`uv` se ocupă de Python în locul tău — **nu** trebuie să instalezi Python separat;
versiunea potrivită este descărcată automat la prima utilizare.

## Pasul 3 — Descarcă anafpy

Tot în terminal:

```bash
git clone https://github.com/robert-malai/anafpy
cd anafpy
uv sync --frozen --extra mcp
```

Ultima comandă construiește mediul din lista de dependențe blocată (locked); durează
un minut prima dată. Ține minte unde a ajuns folderul (rulează `pwd` pe macOS sau
`cd` pe Windows ca să-l afișezi) — vei lipi calea aceea la pasul 5. Ca să
actualizezi anafpy mai târziu: `git pull` în acest folder, apoi din nou
`uv sync --frozen --extra mcp`.

(anafpy este și pe PyPI — `pip install 'anafpy[mcp]'` — dar acest ghid folosește
intenționat folderul descărcat: documentația de referință ANAF și skill-urile de
flux de lucru pe care serverul le oferă lui Claude vin cu folderul, nu cu pachetul
de pe PyPI.)

## Pasul 4 — Autentifică-te la ANAF (o singură dată, cu certificatul)

Acesta este singurul pas care folosește certificatul. După ce confirmi certificatul
în browser, ANAF trimite calculatorului tău un cod de unică folosință — și există
două moduri de a-l prinde:

- **Varianta A — automat (recomandat).** O configurare unică a certificatului face
  `https://localhost` real pe calculatorul tău; autentificarea se finalizează apoi
  singură în browser, nimic de copiat.
- **Varianta B — mod copiere (fără configurare).** Browserul ajunge pe o pagină de
  eroare și tu copiezi adresa ei în terminal în ~60 de secunde.

### Varianta A — captură automată

Întâi, instalează [mkcert](https://github.com/FiloSottile/mkcert) — o unealtă mică
ce face certificate în care calculatorul tău are încredere:

**macOS** (prin [Homebrew](https://brew.sh); instalează întâi Homebrew dacă
`brew --version` nu răspunde):

```bash
brew install mkcert
```

**Windows (PowerShell)**:

```powershell
winget install FiloSottile.mkcert
```

Apoi — la fel pe ambele sisteme — redeschide terminalul, mergi în folderul `anafpy`
de la pasul 3 și creează certificatul `localhost` (o singură dată):

```bash
mkcert -install          # o singură dată; adaugă autoritatea mkcert în magazinul de încredere al calculatorului — confirmă solicitarea de parolă/UAC
mkcert localhost 127.0.0.1
```

Acest lucru scrie `localhost+1.pem` și `localhost+1-key.pem` în folderul curent.
Certificatele pe care le face mkcert sunt de încredere **doar pe acest calculator**
— nimic nu iese din el.

Apoi conectează token-ul USB și rulează (o singură linie, cu valorile tale de la
pasul 1):

```bash
uv run anafpy auth login --client-id <CLIENT_ID> --client-secret <CLIENT_SECRET> \
  --redirect-uri https://localhost:9002/callback \
  --tls-cert localhost+1.pem --tls-key localhost+1-key.pem
```

**Browserul se deschide** pe pagina de autentificare ANAF și îți cere
**certificatul** — alege-l și confirmă (introdu PIN-ul token-ului dacă ți se cere).
După aceea browserul ajunge pe o pagină care spune **„You can close this tab and
return to the terminal"** — gata, codul a fost prins automat, fără avertismente,
nimic de copiat. Dacă ascultătorul (listener) nu poate porni din orice motiv,
comanda revine singură la modul copiere (Varianta B).

### Varianta B — mod copiere

```bash
uv run anafpy auth login --client-id <CLIENT_ID> --client-secret <CLIENT_SECRET> \
  --redirect-uri https://localhost:9002/callback --paste
```

Ce se întâmplă, în ordine:

1. **Browserul se deschide** pe pagina de autentificare ANAF și îți cere
   **certificatul** — alege-l și confirmă (introdu PIN-ul token-ului dacă ți se
   cere).
2. Browserul ajunge apoi pe o pagină de eroare („can't connect to localhost" sau
   ceva similar). **Acest lucru este normal** — nu rulează nimic la adresa aceea;
   codul de care ai nevoie este în bara de adrese.
3. **Copiază adresa (URL) completă din bara de adrese a browserului** și
   **lipește-o în terminal**, care o așteaptă. Fă asta repede — codul expiră în
   aproximativ **60 de secunde**. (Dacă expiră, rulează pur și simplu comanda din
   nou.)

### În oricare variantă

Comanda schimbă codul pe token-uri și le stochează în magazinul securizat de
credențiale al calculatorului (macOS Keychain / Windows Credential Manager).
Verifică dacă a funcționat:

```bash
uv run anafpy auth status
```

Ar trebui să raporteze un token valid. De aici înainte, totul este automat:
token-ul de acces se reînnoiește singur timp de aproximativ **un an**, fără
certificat. Repeți acest pas doar când expiră token-ul de reînnoire (~365 de zile)
sau dacă anulezi aplicația pe portalul ANAF — deci token-ul USB este necesar cam **o
dată pe an**.

## Pasul 5 — Conectează serverul la Claude

anafpy vine cu un server MCP local — un program mic pe care Claude îl pornește pe
calculatorul tău și cu care vorbește. Nu trimite niciodată credențialele tale
nicăieri, decât la ANAF.

### Claude Desktop / Cowork

Cowork ajunge la serverele locale prin aplicația Claude Desktop instalată pe același
calculator, așa că configurarea stă în Claude Desktop:

1. Instalează și autentifică-te în [Claude Desktop](https://claude.ai/download).
2. Deschide fișierul de configurare (creează-l dacă lipsește):
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
     (în Claude Desktop: *Settings → Developer → Edit Config*)
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
3. Adaugă acest text (înlocuiește cele trei valori `...` și calea folderului de la
   pasul 3; pe Windows scrie calea cu backslash dublat, de ex.
   `C:\\Users\\ana\\anafpy`):

```json
{
  "mcpServers": {
    "anafpy": {
      "command": "uv",
      "args": [
        "run", "--directory", "/Users/ana/anafpy",
        "--frozen", "--extra", "mcp", "anafpy-mcp"
      ],
      "env": {
        "ANAFPY_CLIENT_ID": "...",
        "ANAFPY_CLIENT_SECRET": "...",
        "ANAFPY_CIF": "12345678"
      }
    }
  }
}
```

`ANAFPY_CIF` este CUI-ul firmei (doar cifre) — codul fiscal implicit folosit când nu
spui altceva în conversație.

4. Închide complet Claude Desktop și redeschide-l. Uneltele anafpy apar la
   connectors/tools ale aplicației, iar sesiunile Cowork de pe acest calculator le
   pot folosi.

### Claude Code (alternativă)

Dacă folosești Claude Code într-un terminal:

```bash
claude mcp add anafpy \
  -e ANAFPY_CLIENT_ID=... -e ANAFPY_CLIENT_SECRET=... -e ANAFPY_CIF=... \
  -- uv run --directory /Users/ana/anafpy --frozen --extra mcp anafpy-mcp
```

## Pasul 6 — Verifică că funcționează

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

## Pasul 7 (opțional) — Deblochează uneltele pentru cutia poștală SPV

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

Într-un terminal, în folderul anafpy:

```bash
uv run anafpy spv certs                  # listează certificatele tale
uv run anafpy spv select <thumbprint>    # alege-l pe al tău (id-ul hex din `certs`)
uv run anafpy spv login                  # răspunde la solicitarea de PIN / 2FA a token-ului
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

## Bine de știut

- **Producție vs. test**: serverul vorbește implicit cu ANAF **producție**. Ca să
  exersezi în schimb pe mediul de **TEST** al ANAF, adaugă `"ANAFPY_ENV": "test"`
  lângă celelalte intrări din `env` (depunerile de test emit UIT-uri care arată real
  dar nu au valoare juridică).
- **Credențialele tale rămân pe acest calculator**: Client Secret-ul stă în fișierul
  de configurare de mai sus, iar token-urile în magazinul de credențiale al
  sistemului (macOS Keychain / Windows Credential Manager) — protejează contul de pe
  calculator așa cum îți protejezi accesul la SPV.
- **Token-uri într-un fișier în loc de keychain**: necesar doar pe gazde fără un
  magazin de credențiale (de ex. un server Linux sau Docker). Rulează autentificarea
  de la pasul 4 cu `--store-backend file` adăugat și pune
  `"ANAFPY_TOKEN_STORE_BACKEND": "file"` lângă celelalte intrări din `env` în
  configurarea Claude; token-urile stau atunci în `~/.anafpy/tokens.json` —
  protejează acel folder.
- **Sesiunile SPV sunt scurte**: spre deosebire de token-urile OAuth (anuale),
  sesiunea SPV pe cookie se închide după mult sub o oră de inactivitate. Este
  setarea ANAF, nu a ta; rulează `anafpy spv login` oricând ți-o cer uneltele
  `spv_*`.
- **Reînnoirea anuală**: când uneltele încep să eșueze cu un mesaj „rulează
  `anafpy auth login`" după ~un an, repetă pasul 4. Nimic altceva nu trebuie
  schimbat.
- **Deautentificare** (când lași un calculator partajat, îl predai către IT): rulează
  `uv run anafpy auth logout` din folderul `anafpy`. Șterge token-urile de pe acest
  calculator — după aceea uneltele răspund „rulează `anafpy auth login`" până când
  cineva se autentifică din nou cu certificatul. (ANAF nu oferă nicio modalitate ca
  un program să anuleze token-urile din partea sa; ele expiră singure. Ca să
  întrerupi totul și din partea ANAF, folosește *Renunțare Oauth* în portalul ANAF,
  care șterge întreaga înregistrare a aplicației.)

## Depanare

| Simptom | Rezolvare |
|---|---|
| `mkcert: command not found` imediat după ce l-ai instalat | Închide și redeschide terminalul ca noua unealtă să fie preluată, apoi reîncearcă. |
| Autentificarea spune că nu poate citi `localhost+1.pem` (varianta A) | Rulează comanda de autentificare din folderul `anafpy` — acolo a scris `mkcert` fișierele de certificat — sau dă calea lor completă. |
| Avertismentul *„Connection is not private"* la `localhost` (varianta A) | `mkcert -install` nu s-a finalizat (are nevoie de confirmarea de parolă/UAC). Rulează-l din nou, apoi reîncearcă autentificarea; poți de asemenea să dai click o dată pe **Advanced → Proceed to localhost**. |
| Pagină de eroare în browser după pasul cu certificatul (varianta B) | Normal în modul `--paste` — copiază adresa (URL) din bara de adrese în terminal (pasul 4). |
| Cod „expired" / invalid la lipire | Ai așteptat peste ~60 s. Rulează comanda de autentificare din nou și lipește repede. |
| Nicio solicitare de certificat în browser | Driverul/software-ul token-ului nu este instalat sau browserul nu vede certificatul. Testează autentificându-te întâi în SPV; rezolvă acolo, apoi reîncearcă. |
| Claude Desktop arată serverul ca eșuat / `uv` nu este găsit | Aplicațiile desktop nu văd întotdeauna PATH-ul terminalului. În configurare, înlocuiește `"command": "uv"` cu calea completă — macOS: `/Users/<tu>/.local/bin/uv`; Windows: `C:\\Users\\<tu>\\.local\\bin\\uv.exe` (rulează `where.exe uv` / `which uv` ca să confirmi). |
| Uneltele răspund „rulează `anafpy auth login`" | Pasul 4 nu a fost finalizat pe acest calculator, sau token-ul a expirat (~1 an). Rulează din nou pasul 4. |
| Depunere respinsă de ANAF | Acesta este verdictul ANAF asupra conținutului documentului, nu o problemă de instalare — textul erorii revine în rezultatul uneltei; corectează datele și pregătește din nou. |
| `anafpy spv login` eșuează instant cu `SEC_E_UNKNOWN_CREDENTIALS` pe un calculator Windows-on-ARM (de ex. Parallels pe un Mac) | Software-ul furnizorului de certificat este doar pentru Intel (certSIGN vToken este), deci curl-ul încorporat în Windows nu poate folosi certificatul. Instalează [Git for Windows](https://git-scm.com/download/win) (versiunea pe **64 de biți**, nu ARM64) și adaugă `"ANAFPY_CURL": "C:\\Program Files\\Git\\mingw64\\bin\\curl.exe"` lângă celelalte intrări din `env`; setează aceeași variabilă în PowerShell înainte de `anafpy spv login`. |
| `anafpy spv login` eșuează cu `schannel: failed to read data from server: SEC_E_CONTEXT_EXPIRED (0x80090317)` pe Windows | Curl-ul încorporat în Windows (`C:\Windows\System32\curl.exe`) versiunile **8.13–8.15** au o [eroare Schannel](https://github.com/curl/curl/issues/18029) care strică renegocierea TLS a ANAF cu un certificat din magazinul de certificate. Verifică cu `curl --version`; dacă este în acest interval, instalează [Git for Windows](https://git-scm.com/download/win) (curl-ul lui inclus este mai nou) și direcționează `ANAFPY_CURL` către `C:\\Program Files\\Git\\mingw64\\bin\\curl.exe` — în blocul `env` și în PowerShell înainte de `anafpy spv login` (rulează `cygpath -w "$(command -v curl)"` în Git Bash ca să afli calea exactă). anafpy fixează backend-ul Schannel pentru tine. |
