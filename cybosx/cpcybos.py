import asyncio
from enum import Enum

import win32com.client

class CpCybos:
    _instance = None

    class TR_TYPE(Enum):
        LT_TRADE_REQUEST    = 0  #주문 / 계좌 관련 RQ 요청
        LT_NONTRADE_REQUEST = 1  #시세관련 RQ 요청          history
        LT_SUBSCRIBE        = 2  #시세관련 SB

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(CpCybos, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._cybos = win32com.client.Dispatch('CpUtil.CpCybos')
            self._initialized = True

    @property
    def IsConnect(self):
        return self._cybos.IsConnect

    @property
    def ServerType(self):
        return self._cybos.ServerType

    @property
    def LimitRequestRemainTime(self):
        return self._cybos.LimitRequestRemainTime

    def GetLimitRemainCount(self, tr_type):
        return self._cybos.GetLimitRemainCount(tr_type.value)

    def GetLimitRemainTime(self, tr_type): 
        return self._cybos.GetLimitRemainTime(tr_type.value)

    async def wait_call_limit(
        self,
        tr_type=TR_TYPE.LT_NONTRADE_REQUEST
    ):
        n_call = self.GetLimitRemainCount(tr_type) 
        if n_call > 0:
            return
        ms_left = self.LimitRequestRemainTime

        import time
        start_time = time.perf_counter()

        while n_call <= 0:
            await asyncio.sleep(ms_left/1000)
            n_call = self.GetLimitRemainCount(tr_type) 
            ms_left = self.GetLimitRemainTime(tr_type)

        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        print(f"Elapsed time: {elapsed_time:.2f} seconds")

    def wait_call_limit_blocking(
        self,
        tr_type=TR_TYPE.LT_NONTRADE_REQUEST
    ):
        n_call = self.GetLimitRemainCount(tr_type) 
        if n_call > 0:
            return
        ms_left = self.LimitRequestRemainTime

        import time
        start_time = time.perf_counter()

        print('n_call', n_call, 'ms_left', ms_left)
        while n_call <= 0:
            #await asyncio.sleep(ms_left/1000)
            time.sleep(ms_left/1000)
            n_call = self.GetLimitRemainCount(tr_type) 
            ms_left = self.GetLimitRemainTime(tr_type)

        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        print(f"Elapsed time: {elapsed_time:.2f} seconds")


if __name__ == '__main__':
    from run_as_task import run_as_task
    run_as_task()

    async def main():
        cybos = CpCybos()

        attrs = ['IsConnect', 'ServerType', 'LimitRequestRemainTime']
        for a in attrs:
            print(a, getattr(cybos, a))

        for tr_type in CpCybos.TR_TYPE:
            cnt = cybos.GetLimitRemainCount(tr_type)
            left = cybos.GetLimitRemainTime(tr_type)
            print('cnt', tr_type.name, cnt, left)

        await cybos.wait_call_limit(CpCybos.TR_TYPE.LT_NONTRADE_REQUEST)
    asyncio.run(main())
