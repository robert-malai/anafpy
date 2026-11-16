# Exceptions and shared types

The `AnafError` hierarchy — transport, auth, and configuration failures. Business
outcomes are typed values, not exceptions: see the
[error model](../library/errors.md).

::: anafpy.exceptions

## Environment

The OAuth clients' `environment` argument, re-exported as `anafpy.Environment`.

::: anafpy._transport.base.Environment
