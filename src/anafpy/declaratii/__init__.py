"""Romanian tax-declaration authoring, validation, and signing (local only).

This package is a purely local layer — subprocess (ANAF's DUKIntegrator for
validation and the official PDF render), platform crypto (the qualified
certificate's raw signature, delegated to the OS), and files. It has **no
transport client, no ANAF host, no session**: nothing under ``_transport/``.
Filing the signed document with ANAF (portal upload + recipisa tracking) is a
later milestone and deliberately not here.

Public surface:

* :func:`payment_evidence_number` — the ``nr_evid`` payment-evidence composer.
* :class:`DukIntegrator` (+ :class:`DukResult`, :class:`DukFinding`) — the
  headless DUKIntegrator wrapper (validate / render).
* :class:`RawSigner` protocol and its macOS :class:`KeychainRawSigner`
  implementation, plus :func:`sign_pdf` — the pyHanko embedding that turns a
  raw OS signature into a qualified PDF signature.

The signer and :func:`sign_pdf` need the optional ``anafpy[declaratii]`` extra
(pyHanko); importing them without it raises a clear
:class:`~anafpy.exceptions.AnafConfigError`.
"""

from __future__ import annotations

from .duk import DukFinding, DukIntegrator, DukResult
from .nr_evid import payment_evidence_number
from .signing import KeychainRawSigner, RawSigner

__all__ = [
    "DukFinding",
    "DukIntegrator",
    "DukResult",
    "KeychainRawSigner",
    "RawSigner",
    "payment_evidence_number",
]
