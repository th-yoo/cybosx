# XXX
import sys
sys.coinit_flags = 0

import threading
import asyncio

from typing import Any

import win32com.client

from .cpcybos import CpCybos
from .eventsink_thread import (
    EventSinkThread,
    wait_for_event,
    get_into_apartment,
)

from .pool import ResourcePool
from .util import singletonize

def create_thread(id):
    thread = EventSinkThread(f'thread_{id:02d}')
    thread.start()
    return thread

def dispose_thread(thread):
    thread.stop()
    thread.join()

# multi thread
SinkThreadPool = singletonize(ResourcePool(create_thread, 0, dispose_thread))

class RequestContext:
    def __init__(self, thread, event, cookie):
        self.thread = thread
        self.event = event
        self.cookie = cookie

    def __iter__(self):
        return iter((self.thread, self.event, self.cookie))

class CybosIfBase:
    def __init__(self, progid: str, name: Any=''):
        # PyIDispatch?
        self._com = win32com.client.Dispatch(progid)
        self._name = str(name)

    @property
    def com(self):
        return self._com

    @property
    def name(self):
        return self._name

    def __getattr__(self, name):
        if name == '_initialized':
            return False
        return getattr(self._com, name)

class Transaction:
    def __init__(self):
        self._query = None

    async def send(self, query, callback=None):
        def __send(query, callback):
            with get_into_apartment():
                asyncio.run(self._send(query, callback))
        return await asyncio.to_thread(__send, query, callback)

    async def _send(self, query, callback=None):
        ctx = None
        try:
            ctx = await self._pre_request()
            self.query = query

            more = self._get_more()

            while True:
                await self._request(ctx)
                self._proc_payload(callback)

                if not more():
                    break
        except Exception as e:
            raise e
        finally:
            await self._post_request(ctx)
        
    def bsend(self, query, callback=None):
        ctx = None

        if not CpCybos().IsConnect:
            raise Exception('Cybos is not connected')

        try:
            self.query = query

            more = self._get_more()

            while True:
                self._request_blocking()
                self._proc_payload(callback)

                if not more():
                    break
        finally:
            pass

    async def _init_thread(self):
        return await SinkThreadPool().get()

    async def _dispose_thread(self, thread):
        await SinkThreadPool().put(thread)

    async def _pre_request(self) -> RequestContext:
        if not CpCybos().IsConnect:
            raise Exception('Cybos is not connected')

        thread = await self._init_thread()
        event = threading.Event()

        class Sink:
            def OnReceived(self):
                event.set()
        cookie = thread.on(self._com, Sink)

        return RequestContext(thread, event, cookie)

    async def _post_request(self, req_ctx: RequestContext):
        if not req_ctx:
            return

        thread, _, cookie = req_ctx

        if thread:
            if cookie is not None:
                thread.off(cookie)
            await self._dispose_thread(thread)

    @property
    def query(self):
        return self._query

    @query.setter
    def query(self, query):
        query.serialize(self._com)
        self._query = query
        
    async def _request(self, req_ctx: RequestContext):
        await CpCybos().wait_call_limit()
        if self._com.GetDibStatus():
            raise Exception(f'Invalid Stockchart.DibStatus: {rc}')
        self._com.Request()
        await wait_for_event(req_ctx.event)

    def _request_blocking(self):
        CpCybos().wait_call_limit_blocking()
        if self._com.GetDibStatus():
            raise Exception(f'Invalid Stockchart.DibStatus: {rc}')
        self._com.BlockRequest()

    def _proc_payload(self, callback=None):
        try:
            if callback:
                callback(self)
            else:
                cb = getattr(self, '_on_resp', lambda: None)
                cb()
        except Exception as e:
            print('FIXME: do not throw exception from callback')
            raise e

    def _get_more(self, *args, **kwargs):
        def more():
            self._query = None
            return False
        return more

class CybosxIf(CybosIfBase, Transaction):
    def __init__(self, progid: str, name: Any=''):
        super().__init__(progid, name)
   
if __name__ == '__main__':
    import asyncio
    from enum import Enum
    from dataclasses import dataclass, field

    class StockMst(CybosxIf):
        def __init__(self, name: Any=''):
            super().__init__('DsCbo1.StockMst', 'StockMst')

    @dataclass
    class StockMstRequest:
        symbol: str = field()

        def __post_init__(self):
            self.symbol = self._symbol_validate(self.symbol)

        def serialize(self, stock_mst):
            stock_mst.SetInputValue(0, self.symbol)

        @staticmethod
        def _symbol_validate(val: str) -> str:
            if not val or not isinstance(val, str):
                raise TypeError(f'Invalid symbol type: {type(val)}')
            if len(val) == 7:
                if not val.startswith('A'):
                    raise ValueError(f'Invalid symbol value: {val}')
                val = val[1:]
            if len(val) != 6 or not val.isdigit():
                raise ValueError(f'Invalid symbol value: {val}')
            return 'A' + val

    query = StockMstRequest(symbol = 'A005930')
    def on_resp(cybos_obj):
        com = cybos_obj.com
        print(com.GetHeaderValue(11))
        print(com.GetHeaderValue(12))

    async def main():
        with SinkThreadPool():
            trans = StockMst()
            trans.bsend(query, on_resp)
            await trans.send(query, on_resp)

    asyncio.run(main())

