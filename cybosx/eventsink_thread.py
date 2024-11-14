import threading
import asyncio
from contextlib import contextmanager

# http://www.icodeguru.com/webserver/Python-Programming-on-Win32/appd.htm
# https://gist.github.com/weshouman/e7a997dd3eb03263c561fdc6fd0b6eb2
# this should be executed at the entry point of the main thread`
import sys
sys.coinit_flags = 0
import pythoncom

import win32com.client

from .win32_thread import Win32Thread

@contextmanager
def get_into_apartment(coinit = pythoncom.COINIT_MULTITHREADED):
    try:
        pythoncom.CoInitializeEx(coinit)
        yield
    except Exception as e:
        raise e
    else:
        pythoncom.CoUninitialize()

class IDManager:
    def __init__(self):
        self._free = set()
        self._cur = 1

    def alloc(self):
        if self._free:
            return self._free.pop()
        rv = self._cur
        self._cur += 1
        return rv

    def free(self, id):
        self._free.add(id)

class EventSinkThread(Win32Thread):
    class COM(Win32Thread.COM):
        on = 0
        off = 1

    def __init__(self, name=''):
        super().__init__()
        self._name = str(name)

        self._cookie = IDManager()
        self._sinks = {}

        self._com_handler = (
            self._on_impl,
            self._off_impl
        )

    def run(self):
        with get_into_apartment():
            super().run()

    def on(self, source, sink):
        return self._invoke(self.COM.on, source, sink)

    def off(self, cookie):
        return self._invoke(self.COM.off, cookie)

    def _on_impl(self, source, sink):
        s = win32com.client.WithEvents(source, sink)
        cookie = self._cookie.alloc()
        self._sinks[cookie] = s
        return cookie

    def _off_impl(self, cookie):
        sink = self._sinks.pop(cookie, None)
        if sink is not None:
            del sink
            self._cookie.free(cookie)

async def wait_for_event(event: threading.Event):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, event.wait)
    event.clear()

# https://money2.daishin.com/e5/mboard/ptype_basic/plusPDS/DW_Basic_Read.aspx?boardseq=299&seq=89&page=1&searchString=blockrequest&prd=&lang=&p=8831&v=8638&m=9508
if __name__ == '__main__':
    async def main():
        thread = EventSinkThread()
        try:
            thread.start()

            code = 'A005930'
            stock_mst = win32com.client.Dispatch("DsCbo1.StockMst")

            event = threading.Event()
            class Sink:
                def OnReceived(self):
                    print('OnReceived')
                    event.set()

            cookie = thread.on(stock_mst, Sink)

            stock_mst.SetInputValue(0, code)
            stock_mst.Request()

            await wait_for_event(event)

            thread.off(cookie)

            print('closing price:', stock_mst.GetHeaderValue(11))
            print('delta price from prev day:', stock_mst.GetHeaderValue(12))

        finally:
            thread.stop()
            thread.join()

            # CoInitializeEx is called at 'import pythoncom'
            pythoncom.CoUninitialize()

    asyncio.run(main())
