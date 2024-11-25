# XXX
import sys
sys.coinit_flags = 0

from enum import Enum
from datetime import timedelta

from .cybosx_if import CybosxIf, SinkThreadPool
from .stockchart_request import StockChartRequest

class RespHKey(Enum):
    symbol              =  0
    n_cols              =  1
    col_names           =  2
    n_records           =  3
    n_last_candle_tick  =  4
    last_trade_date     =  5
    close_price_prev_day = 6
    price               =  7
    trend               =  8
    delta               =  9
    volume              = 10
    ask                 = 11
    bid                 = 12
    open_price          = 13
    high                = 14
    low                 = 15
    amount              = 16
    shares              = 18
    cap                 = 19
    vol_prev_day        = 20
    last_updated_time   = 21
    limit_up            = 22
    limit_down          = 23

class StockChart(CybosxIf):
    Request = StockChartRequest
    RespHKey = RespHKey

    def __init__(self, name='StockChart'):
        super().__init__('CpSysDib.StockChart', name)

    def _get_more(self):
        if self.query.retrieval_mode == self.Request.RetrievalMode.NUM:
            n_left = self.query.n_record

            # day{n_shares,market_cap} [1,2500)
            def more():
                nonlocal n_left

                n = self._com.GetHeaderValue(RespHKey.n_records.value)
                if not n:
                    return False
                n_left -= n

                rv = 0 < n_left and self._com.Continue

                # the last request for this query
                if rv and n_left < n:
                    earliest_date = self._com.GetDataValue(0, n-1)

                    # update n_record
                    self._com.SetInputValue(
                        self.Request.FieldKey.n_record.value,
                        n_left
                    )

                    # update end_date
                    earliest_date = self.Request.dateint2datetime(earliest_date)
                    end_date = earliest_date - timedelta(days=1)
                    end_date = int(end_date.strftime('%Y%m%d'))
                    self._com.SetInputValue(
                        self.Request.FieldKey.end_date.value,
                        end_date
                    )
                return rv

            return more
        else:
            beg_date = self.query.beg_date

            def more():
                nonlocal beg_date
                n = self._com.GetHeaderValue(RespHKey.n_records.value)
                if not n:
                    return False
                earliest_date = self._com.GetDataValue(0, n-1)
                return beg_date < earliest_date and self._com.Continue 

            return more

if __name__ == '__main__':
    import asyncio

    def on_resp(sc):
        stock_chart = sc.com

        cols = sc.query.record_cols
        n_records = stock_chart.GetHeaderValue(RespHKey.n_records.value)
        print([col.name for col in cols])
        for i in range(n_records):
            row = []
            for ci, col in enumerate(cols):
                val = stock_chart.GetDataValue(ci, i)
                row.append(val)
            print(row)
        print(sc.name, n_records, stock_chart.GetDataValue(0, 0))

    async def main():
        query = StockChartRequest(
            symbol = 'A005930',
            retrieval_mode = StockChartRequest.RetrievalMode.NUM,
            #n_record = 2500,
            n_record = 1,
            ohlc = True,
            record_cols = [
                StockChartRequest.RecordCol.N_SHARES,
                #StockChartRequest.RecordCol.MARKET_CAP,
                StockChartRequest.RecordCol.FOREIGN_LIMIT,
                #StockChartRequest.RecordCol.FOREIGN_SHARES,
                StockChartRequest.RecordCol.FOREIGN_PCT,
            ],
        )

        with SinkThreadPool():
            stock_chart = StockChart()
            #await asyncio.to_thread(stock_chart.bsend, query, on_resp)
            await stock_chart.send(query, on_resp)

    asyncio.run(main())
