"""Romanian tax-declaration authoring, validation, signing, and status tracking.

Authoring is a purely local layer — subprocess (ANAF's DUKIntegrator for
validation and the official PDF render), platform crypto (the qualified
certificate's raw signature, delegated to the OS), and files. Filing the signed
document with ANAF (portal upload) is a later milestone and deliberately not
here — but **status tracking already is**: ANAF's StareD112 service is public
and unauthenticated, so :class:`DeclarationStatusClient` answers "was my
(manually filed) declaration accepted?" and downloads the signed recipisa with
nothing but the upload index and the CUI.

Public surface:

* :func:`payment_evidence_number` — the ``nr_evid`` payment-evidence composer.
* :class:`DukIntegrator` (+ :class:`DukResult`, :class:`DukFinding`) — the
  headless DUKIntegrator wrapper (validate / render).
* :class:`RawSigner` protocol and its macOS :class:`KeychainRawSigner`
  implementation, plus :func:`sign_pdf` — the pyHanko embedding that turns a
  raw OS signature into a qualified PDF signature.
* :class:`DeclarationStatusClient` (+ :class:`DeclarationStatusList`,
  :class:`DeclarationDocument`, :class:`DeclarationState`) — filing status and
  recipisa download over the public StareD112 service.

The signer and :func:`sign_pdf` need the optional ``anafpy[declaratii]`` extra
(pyHanko); importing them without it raises a clear
:class:`~anafpy.exceptions.AnafConfigError`.
"""

from __future__ import annotations

from .duk import DukFinding, DukIntegrator, DukResult
from .nr_evid import payment_evidence_number
from .signing import KeychainRawSigner, RawSigner
from .status import (
    DeclarationDocument,
    DeclarationState,
    DeclarationStatusClient,
    DeclarationStatusList,
)

__all__ = [
    "DeclarationDocument",
    "DeclarationState",
    "DeclarationStatusClient",
    "DeclarationStatusList",
    "DukFinding",
    "DukIntegrator",
    "DukResult",
    "KeychainRawSigner",
    "RawSigner",
    "payment_evidence_number",
]
