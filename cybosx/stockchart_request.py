from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from typing import Optional, Union, List, Tuple

def dateint2datetime(date_int: int) -> datetime:
    date = str(date_int)
    if len(date) != 8:
        raise ValueError(f'Invalid date int: {date}')

    y, m, d  = (int(date[:4]), int(date[4:6]), int(date[6:]))
    return datetime(y, m, d)

class FieldKey(Enum):
    symbol          =  0
    retrieval_mode  =  1
    end_date        =  2
    beg_date        =  3
    n_record        =  4
    record_cols     =  5
    timeframe       =  6
    timeperiod      =  7        #  tick, min only?
    gap_adjusted    =  8
    price_adjusted  =  9
    volume_scope    = 10
    early_start     = 11

class RetrievalMode(Enum):
    TERM = ord('1')
    NUM  = ord('2')

class RecordCol(Enum):
    # default
    DATE = 0
    O = 2
    H = 3
    L = 4
    C = 5
    V = 8

    # commonly available
    DPRICE_PDAY = 6 # price change from the previous day
    AMOUNT = 9      # KRW 10000 unit (?)

    # available only for min and tick
    TIME = 1        # meaningful only for min and tick
    ACC_SELL_BID_VOL = 10
    ACC_BUY_ASK_VOL = 11
    ACC_SELL_EXE_PRICE_VOL = 62
    ACC_BUY_EXE_PRICE_VOL = 63

    # not available for min and tick
    N_SHARES = 12
    MARKET_CAP = 13
    FOREIGN_LIMIT = 14
    FOREIGN_BUYABLE = 15
    FOREIGN_SHARES = 16
    FOREIGN_PCT = 17
    ADJUSTED_DATE = 18
    ADJUSTED_RATIO = 19
    INST_BOUGHT = 20
    INST_ACC_BOUGHT = 21
    PRICE_FLUCTUATION = 22
    PRICE_CHANGE_RATIO = 23
    DEPOSIT_AMOUNT = 24
    TURNOVER_RATE = 25
    TRADE_COMPLETION_RATE = 26
    DIFF_SIGN = 37

class Timeframe(Enum):
    DAY   = ord('D')
    WEEK  = ord('W')
    MONTH = ord('M')
    MIN   = ord('m')
    TICK  = ord('T')

class RecordCols(set):
    def __init__(self, *args):
        super().__init__(args)

    def validate(self,
        tf: Timeframe,
        ohlc=True
    ) -> list[int]:
        if ohlc:
            self.update([
                RecordCol.DATE,
                RecordCol.O,
                RecordCol.H,
                RecordCol.L,
                RecordCol.C,
                RecordCol.V
            ])
            if tf in (Timeframe.MIN, Timeframe.TICK):
                self.add(RecordCol.TIME)
        if tf in (Timeframe.MIN, Timeframe.TICK):
            self.difference_update({
                RecordCol.N_SHARES,
                RecordCol.MARKET_CAP,
                RecordCol.FOREIGN_LIMIT,
                RecordCol.FOREIGN_BUYABLE,
                RecordCol.FOREIGN_SHARES,
                RecordCol.FOREIGN_RATIO,
                RecordCol.ADJUSTED_DATE,
                RecordCol.ADJUSTED_RATIO,
                RecordCol.INST_BOUGHT,
                RecordCol.INST_ACC_BOUGHT,
                RecordCol.PRICE_FLUCTUATION,
                RecordCol.PRICE_CHANGE_RATIO,
                RecordCol.DEPOSIT_AMOUNT,
                RecordCol.TURNOVER_RATE,
                RecordCol.TRADE_COMPLETION_RATE,
                RecordCol.DIFF_SIGN,
            })
        else:
            self.difference_update({
                RecordCol.ACC_SELL_BID_VOL,
                RecordCol.ACC_BUY_ASK_VOL,
                RecordCol.ACC_SELL_EXE_PRICE_VOL,
                RecordCol.ACC_BUY_EXE_PRICE_VOL,
            })

        # unordered
        #return [col.value for col in list(self)]
        #return list(self).sort(key = lambda c: c.value)
        return sorted(list(self), key = lambda c: c.value)

class GapAdjusted(Enum):
    FALSE = ord('0')
    TRUE  = ord('1')

class PriceAdjusted(Enum):
    FALSE = ord('0')
    TRUE  = ord('1')

class VolumeScope(Enum):
    ALL         = ord('1')
    POST_MARKET = ord('2')
    MARKET      = ord('3')
    PRE_MARKET  = ord('4')

class EarlyStart(Enum):
    FALSE = ord('N')
    TRUE  = ord('Y')

@dataclass
class StockChartRequest:
    # types
    FieldKey = FieldKey
    RetrievalMode = RetrievalMode
    RecordCol = RecordCol
    Timeframe = Timeframe
    RecordCols = RecordCols
    GapAdjusted = GapAdjusted
    PriceAdjusted = PriceAdjusted
    VolumeScope = VolumeScope
    EarlyStart = EarlyStart

    # helper function
    dateint2datetime = dateint2datetime

    # fields
    symbol: str                 = field()
    ohlc: bool                  = field(default=True)
    retrieval_mode: Optional[RetrievalMode]  = field(default=RetrievalMode.NUM)
    end_date: Optional[Union[datetime,int]]  = field(default=0) 
    beg_date: Optional[datetime] = field(default=datetime(1997,10,2))
    n_record: Optional[int]      = field(default=10000000)
    record_cols: Optional[
        Union[
            List[RecordCol], 
            Tuple[RecordCol], 
            set[RecordCol],
            RecordCols[RecordCol]
        ]
    ] = field(default_factory=RecordCols)
    timeframe: Optional[Timeframe]  = field(default=Timeframe.DAY)
    timeperiod: Optional[int]       = field(default=1)
    gap_adjusted: Optional[GapAdjusted]     = field(default=GapAdjusted.FALSE)
    price_adjusted: Optional[PriceAdjusted] = field(default=PriceAdjusted.TRUE)
    volume_scope: Optional[VolumeScope] = field(default=VolumeScope.MARKET)
    early_start: Optional[EarlyStart] = field(default=EarlyStart.FALSE)

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

    @staticmethod
    def _retrieval_mode_validate(val: RetrievalMode):
        if not isinstance(val, RetrievalMode):
            raise TypeError(f'Invalid num_or_term type: {type(val)}')
        return val

    @staticmethod
    def _date_validate(field: str, val: datetime):
        if not isinstance(val, datetime):
            raise TypeError(f'Invalid {field} type: {type(val)}')
        return int(val.strftime('%Y%m%d'))
       
    @staticmethod
    def _beg_date_validate(end_date: int, val: datetime):
        min_date = datetime(1997,10,2)

        rv = StockChartRequest._date_validate('beg_date', val)

        if val < min_date:
            raise ValueError(f'beg_date is earlier than min_date {min_date}')

        # TODO: get the latest market day
        # end_date can be zero
        if end_date and rv > end_date:
            end_date = dateint2datetime(end_date)
            raise ValueError(f'beg_date is later than end_date {end_date}')
        return rv

    # TODO: check RetrievalMode
    # check num_or_term in serialize()
    @staticmethod
    def _n_record_validate(val):
        if not isinstance(val, int):
            raise TypeError(f'Invalid n_record type: {type(val)}')
        if val < 1:
            raise ValueError(f'Invalid n_record value: {val}')
        return val
    
    def _record_cols_validate(self):
        if isinstance(self.record_cols, (list, tuple, set)):
            self.record_cols = RecordCols(*self.record_cols)
        if not isinstance(self.record_cols, RecordCols):
            raise TypeError(
                f'Invalid record_cols type: {type(self.record_cols)}'
            )

        return self.record_cols.validate(self.timeframe, self.ohlc)

    def _timeframe_validate(self, val):
        if not isinstance(val, Timeframe):
            raise TypeError(f'Invalid timeframe type: {type(val)}')

        if (
            self.retrieval_mode == RetrievalMode.TERM and
            val != Timeframe.DAY
        ):
            raise ValueError(f'Timeframe {val} can not be applied to term')
        return val


    @staticmethod
    def _timeperiod_validate(val):
        if not isinstance(val, int):
            raise TypeError(f'Invalid timeperiod type: {type(val)}')
        if val < 1:
            raise ValueError(f'Invalid timeperiod value: {val}')
        return val

    @staticmethod
    def _gap_adjusted_validate(val):
        if not isinstance(val, GapAdjusted):
            raise TypeError(f'Invalid gap_adjusted type: {type(val)}')
        return val

    @staticmethod
    def _price_adjusted_validate(val):
        if not isinstance(val, PriceAdjusted):
            raise TypeError(f'Invalid price_adjusted type: {type(val)}')
        return val

    @staticmethod
    def _volume_scope_validate(val):
        if not isinstance(val, VolumeScope):
            raise TypeError(f'Invalid volume_scope type: {type(val)}')
        return val

    @staticmethod
    def _early_start_validate(val):
        if not isinstance(val, EarlyStart):
            raise TypeError(f'Invalid early_start type: {type(val)}')
        return val

    def _validate_timeframe_and_term(self):
        if (
            self.timeframe != Timeframe.DAY and
            self.retrival_mode == RetrievalMode.TERM
        ):
            raise ValueError('term is only available for day')

    def __post_init__(self):
        self.symbol = self._symbol_validate(self.symbol)
        self.retrieval_mode = self._retrieval_mode_validate(self.retrieval_mode)
        self.timeframe = self._timeframe_validate(self.timeframe)

        self._validate_timeframe_and_term()

        if not self.end_date:
            self.end_date = 0
        else:
            self.end_date = self._date_validate('end_date', self.end_date)

        self.beg_date = self._beg_date_validate(self.end_date, self.beg_date)
        self.n_record = self._n_record_validate(self.n_record)

        self.record_cols = self._record_cols_validate()

        self.gap_adjusted = self._gap_adjusted_validate(self.gap_adjusted)
        self.price_adjusted = self._price_adjusted_validate(self.price_adjusted)
        self.volume_scope = self._volume_scope_validate(self.volume_scope)
        self.early_start = self._early_start_validate(self.early_start)

    def serialize(self, stock_chart):
        for key in FieldKey:
            # beg_date takes effect on the # of candle sticks
            if (
                key == FieldKey.beg_date and
                self.retrieval_mode == RetrievalMode.NUM
            ):
                continue

            if (
                key == FieldKey.n_record and
                self.retrieval_mode == RetrievalMode.TERM
            ):
                continue

            val = getattr(self, key.name)
            if isinstance(val, (str, int)):
                value = val
            elif isinstance(val, Enum):
                value = val.value
            # record_cols
            elif isinstance(val, list):
                value = [c.value for c in val]
            else:
                raise TypeError(f'{key.name} is of unknown type {type(val)}')
            #print(key.name, key.value, val, value)
            if stock_chart:
                stock_chart.SetInputValue(key.value, value)

        return self.record_cols

if __name__ == '__main__':
    r = StockChartRequest(
        symbol = 'A005930'
    )
    print(r)
    r.serialize(None)
