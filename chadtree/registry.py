from asyncio import Queue
from functools import lru_cache
from typing import Any, Awaitable, Callable

from pynvim_pp.autocmd import AutoCMD
from pynvim_pp.handler import RPC
from pynvim_pp.types import Method

NAMESPACE = "CHAD"


def _name_gen(fn: Callable[..., Awaitable[Any]]) -> str:
    return fn.__qualname__.lstrip("_").capitalize()


@lru_cache(maxsize=None)
def queue() -> Queue:
    return Queue()


autocmd = AutoCMD()
rpc = RPC(NAMESPACE, name_gen=_name_gen)


async def enqueue_event(method: Method, *args: Any) -> None:
    msg = (method, args)
    await queue().put(msg)
