# XXX
import sys
sys.coinit_flags = 0

from dataclasses import dataclass, field
from enum import Enum

from .cybosx_if import CybosxIf, SinkThreadPool

# https://money2.daishin.com/e5/mboard/ptype_basic/HTS_Plus_Helper/DW_Basic_Read_Page.aspx?boardseq=284&seq=3&page=1&searchString=StockMst&p=8839&v=8642&m=9508
#class RespHKey(Enum):
#    symbol = 0

#@dataclass
#class StockMstResponse:


class StockMst(CybosxIf):
    def __init__(self, name='StockMst'):
        super().__init__('DsCbo1.StockMst', name)

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


if __name__ == '__main__':
    import asyncio

    def on_resp(cybos_obj):
        stock_mst = cybos_obj._com
        print(stock_mst.GetHeaderValue(11))
        print(stock_mst.GetHeaderValue(12))

    async def main():
        query = StockMstRequest(symbol = 'A005930')

        with SinkThreadPool():
            stock_mst = StockMst()
            stock_mst.bsend(query, on_resp)
            await stock_mst.send(query, on_resp)

    asyncio.run(main())

