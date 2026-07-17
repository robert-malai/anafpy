"""Romanian tax-declaration authoring, validation, signing, and status tracking.

Authoring is a purely local layer — subprocess (ANAF's DUKIntegrator for
validation and the official PDF render), platform crypto (the qualified
certificate's raw signature, delegated to the OS), and files. **Status
tracking** needs no credentials at all: ANAF's StareD112 service is public and
unauthenticated, so :class:`DeclarationStatusClient` answers "was my
declaration accepted?" and downloads the signed recipisa with nothing but the
upload index and the CUI. **Filing** (M2, recon-grade) is
:class:`DeclarationUploadClient`: the certificate login on the ``WAS6DUS``
portal plus the one multipart POST; its success-page parse was live-verified
by a D406T filing on 2026-07-17.

Public surface:

* :func:`payment_evidence_number` — the ``nr_evid`` payment-evidence composer.
* :class:`DukIntegrator` (+ :class:`DukResult`, :class:`DukFinding`) — the
  headless DUKIntegrator wrapper (validate / render).
* :class:`RawSigner` protocol and its macOS :class:`KeychainRawSigner`
  implementation. :func:`load_pdfsign` loads the optional pyHanko embedding
  module with a clear install hint.
* :class:`DeclarationStatusClient` (+ :class:`DeclarationStatusList`,
  :class:`DeclarationDocument`, :class:`DeclarationState`) — filing status and
  recipisa download over the public StareD112 service.
* :class:`DeclarationUploadClient` (+ :class:`PortalCurlBootstrapper`,
  :class:`PortalUploadResult`) — the portal upload (certificate login + the
  multipart filing POST).

The platform signer imports without optional dependencies; calling
:func:`load_pdfsign` without ``anafpy[declaratii]`` raises a clear
:class:`~anafpy.exceptions.AnafConfigError`.
"""

from __future__ import annotations

from .duk import DukIntegrator, fetch_feed_versions
from .models import (
    DeclarationDocument,
    DeclarationState,
    DeclarationStatusList,
    DukFinding,
    DukResult,
    PdfSignResult,
    PortalUploadResult,
)
from .nr_evid import payment_evidence_number
from .signing import KeychainRawSigner, RawSigner, default_signed_path, load_pdfsign
from .status import DeclarationStatusClient
from .upload import DeclarationUploadClient, PortalCurlBootstrapper

__all__ = [
    "DeclarationDocument",
    "DeclarationState",
    "DeclarationStatusClient",
    "DeclarationStatusList",
    "DeclarationUploadClient",
    "DukFinding",
    "DukIntegrator",
    "DukResult",
    "KeychainRawSigner",
    "PdfSignResult",
    "PortalCurlBootstrapper",
    "PortalUploadResult",
    "RawSigner",
    "default_signed_path",
    "fetch_feed_versions",
    "load_pdfsign",
    "payment_evidence_number",
]
