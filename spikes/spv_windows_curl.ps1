<#
M0 spike: call SPV `listaMesaje` via Windows Schannel mTLS (system curl.exe).

THROWAWAY CODE - not part of the library. Purpose: observe real behavior of
the CertStore + Schannel client-certificate path against
https://webserviced.anaf.ro/SPVWS2/rest/ before designing the transport:

  1. Can the ships-with-Windows curl.exe (Schannel build) authenticate with
     --cert "CurrentUser\MY\<thumbprint>" where the private key lives on a
     USB token / CSP (SafeNet, certSIGN middleware)?
  2. PIN prompt frequency: does the middleware prompt once per curl PROCESS,
     once per TLS handshake, or once per Windows logon session?
     The script probes this by running (a) two separate curl processes and
     (b) one curl process fetching the URL twice (connection reuse within
     the process).
  3. Does the service set session cookies? (The reference Java client in
     docs/anaf-reference/_sources/clientspv/ installs a CookieManager.)

Run from PowerShell (5.1 or 7+), certificate token plugged in:

    .\spikes\spv_windows_curl.ps1                    # list candidates, auto-pick if unique
    .\spikes\spv_windows_curl.ps1 -List              # enumerate candidates and exit
    .\spikes\spv_windows_curl.ps1 -Thumbprint AB12... -Zile 5 [-Cif 12345678]

Note down WHEN each PIN prompt appears relative to the timestamped log
lines - that is the data point the transport design needs.
#>
[CmdletBinding()]
param(
    [string]$Thumbprint,
    [int]$Zile = 5,
    [string]$Cif,
    [switch]$List,
    [switch]$SkipSecondProcess
)

$ErrorActionPreference = 'Stop'
$BaseUrl = 'https://webserviced.anaf.ro/SPVWS2/rest/listaMesaje'
$ClientAuthOid = '1.3.6.1.5.5.7.3.2'
$RoQualifiedCas = 'certSIGN|DigiSign|Trans\s*Sped|ALFASIGN|AlfaTrust|CERTDIGITAL|Cert\s*Digital'

function Write-Log([string]$Message) {
    Write-Host ("[{0:HH:mm:ss.fff}] {1}" -f (Get-Date), $Message) -ForegroundColor Cyan
}

# --- 0. Verify the system curl is a Schannel build (not a Git-for-Windows one) ---
$curl = Get-Command curl.exe -ErrorAction SilentlyContinue
if (-not $curl) { throw 'curl.exe not found. Windows 10 1803+ ships it in System32.' }
$curlVersion = & $curl.Source -V
Write-Log "curl: $($curl.Source)"
Write-Log ($curlVersion | Select-Object -First 1)
if ($curlVersion -notmatch 'Schannel') {
    Write-Warning ("This curl.exe is NOT built against Schannel - CertStore " +
        "--cert syntax will not work. Use C:\Windows\System32\curl.exe explicitly.")
}

# --- 1. Certificate discovery: private key + clientAuth EKU + RO qualified CA ---
$candidates = Get-ChildItem Cert:\CurrentUser\My | Where-Object {
    $_.HasPrivateKey -and
    $_.NotAfter -gt (Get-Date) -and
    ($eku = $_.Extensions | Where-Object { $_ -is [System.Security.Cryptography.X509Certificates.X509EnhancedKeyUsageExtension] }) -and
    ($eku.EnhancedKeyUsages | Where-Object { $_.Value -eq $ClientAuthOid })
}
$qualified = @($candidates | Where-Object { $_.Issuer -match $RoQualifiedCas })

Write-Host "`nCandidate identities in CurrentUser\MY (private key + clientAuth EKU):`n"
foreach ($c in $candidates) {
    $flag = if ($c.Issuer -match $RoQualifiedCas) { 'RO qualified CA' } else { '-' }
    Write-Host ("  subject:    {0}" -f $c.Subject)
    Write-Host ("  issuer:     {0}" -f $c.Issuer)
    Write-Host ("  thumbprint: {0}" -f $c.Thumbprint)
    Write-Host ("  valid to:   {0:yyyy-MM-dd}   flags: {1}`n" -f $c.NotAfter, $flag)
}
if ($List) { return }

if (-not $Thumbprint) {
    if ($qualified.Count -eq 1) {
        $Thumbprint = $qualified[0].Thumbprint
        Write-Log "auto-picked the single RO qualified identity: $Thumbprint"
    } else {
        throw "Auto-pick found $($qualified.Count) RO qualified identities; rerun with -Thumbprint <hex>."
    }
}

# --- 2. The calls ---
$query = "zile=$Zile"
if ($Cif) { $query += "&cif=$Cif" }
$url = "${BaseUrl}?${query}"
$certArg = "CurrentUser\MY\$Thumbprint"

function Invoke-SpvCurl([string[]]$Urls, [string]$Tag) {
    $headerFile = Join-Path $env:TEMP "spv_spike_headers_$Tag.txt"
    $curlArgs = @('--silent', '--show-error', '--cert', $certArg,
                  '--dump-header', $headerFile, '--max-time', '90',
                  '--write-out', "`n[curl: %{http_code} in %{time_total}s, handshake %{time_appconnect}s]`n")
    $curlArgs += $Urls
    Write-Log "$Tag : curl --cert `"$certArg`" $($Urls -join ' ')  (PIN prompt, if any, fires NOW)"
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    & $curl.Source @curlArgs
    $sw.Stop()
    Write-Log ("$Tag : exit={0}, wall time {1:n2}s" -f $LASTEXITCODE, $sw.Elapsed.TotalSeconds)
    if (Test-Path $headerFile) {
        $cookies = Select-String -Path $headerFile -Pattern '^Set-Cookie:' -SimpleMatch:$false
        if ($cookies) { Write-Log "$Tag : $($cookies.Line -join '; ')" }
    }
}

Write-Log '--- run A: one curl process, URL fetched TWICE (in-process connection reuse) ---'
Invoke-SpvCurl @($url, $url) 'runA'

if (-not $SkipSecondProcess) {
    Write-Log '--- run B: a SECOND curl process (does the PIN prompt fire again?) ---'
    Invoke-SpvCurl @($url) 'runB'
}

Write-Host @"

=== Observations to note for the transport design ===
- run A: did ONE PIN prompt cover both fetches (in-process session reuse)?
  Compare time_appconnect of fetch 1 vs 2: ~0 on the second = TLS/connection reused.
- run B: did a new PROCESS re-prompt for the PIN? (per-process vs per-logon caching)
- Any Set-Cookie lines above? If yes, a cookie-preserving client may keep one
  authenticated session across requests (see docs/anaf-reference/spv/api.md par.1).
- If the JSON contains "eroare":"Nu exista mesaje..." that is a NO-RESULTS note,
  not a failure.
"@
