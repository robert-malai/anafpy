"""Business-state polling shared by the wait-for-outcome flows.

The clients do **no transport retry** (``DESIGN.md`` §4) — this is the other
kind of loop: re-reading an ANAF-side *business* state that starts out
non-terminal and settles on its own (an upload still ``in prelucrare``, a
report ANAF has not generated yet). Only the state is retried; any HTTP/auth
exception propagates on the first attempt, keeping each read a single
transparent call.

:func:`poll_until` is that loop, once, for the three callers that need it
(``EFacturaClient.upload_and_wait``, ``ETransportClient.upload_and_wait``,
``SpvClient.wait_for_report``). It exists because tenacity's *result*-based
retry needs a two-step dance per attempt — run the fetch inside ``with
attempt``, then feed the value to ``set_result`` **after** the block so the
attempt's own outcome is recorded first — which is easy to get subtly wrong
and was previously written out three times.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_result,
    stop_after_delay,
    wait_exponential_jitter,
)

__all__ = ["poll_until"]


async def poll_until[ResultT](
    fetch: Callable[[], Awaitable[ResultT]],
    *,
    pending: Callable[[ResultT], bool],
    timeout: float,
    timeout_message: str,
    initial_wait: float = 2.0,
    max_wait: float = 30.0,
) -> ResultT:
    """Call *fetch* until *pending* says the result has settled; return it.

    Waits between attempts with exponential backoff plus jitter, giving up
    after *timeout* seconds in total.

    Args:
        fetch: the read to repeat — one full client call per attempt.
        pending: ``True`` while the result is still non-terminal and worth
            re-reading.
        timeout: total wall-clock budget across all attempts.
        timeout_message: the :class:`TimeoutError` message when the budget runs
            out — each caller words its own (which id, what to do next).
        initial_wait: first inter-attempt delay, in seconds.
        max_wait: ceiling on the inter-attempt delay, in seconds.

    Returns:
        The first result for which *pending* is ``False``.

    Raises:
        TimeoutError: the budget was exhausted while still pending.
        Exception: anything *fetch* raises propagates immediately — exceptions
            are never retried here.
    """
    last: ResultT | None = None
    try:
        async for attempt in AsyncRetrying(
            retry=retry_if_result(pending),
            wait=wait_exponential_jitter(initial=initial_wait, max=max_wait),
            stop=stop_after_delay(timeout),
            reraise=True,
        ):
            with attempt:
                last = await fetch()
            # set_result drives the result-based retry; it must run after the
            # `with` block so the attempt's outcome is recorded first.
            if not attempt.retry_state.outcome.failed:  # type: ignore[union-attr]
                attempt.retry_state.set_result(last)
    except RetryError as exc:
        raise TimeoutError(timeout_message) from exc
    # Exiting the loop without RetryError means an attempt returned a result
    # `pending` rejected, so `last` holds it.
    assert last is not None
    return last
