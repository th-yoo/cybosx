from enum import Enum
from datetime import datetime

from .cybosx_if import CybosIfBase

class Market(Enum):
    NULL        = 0
    KOSPI       = 1
    KOSDAQ      = 2
    FREEBOARD   = 3
    KRX         = 4
    KONEXT      = 5

class SecType(Enum):
    NULL = 0
    STOCK = 1
    MUTUAL_FUND = 2
    REITS = 3   # Real Estate Investment Trust
    SC = 4    # Ship Investment Company
    IF = 5   # Infrastructure Fund
    DR = 6  # Depository Receipt 주식예탁증서
    SW = 7  # Security Warrants 신수인수권증권
    SR = 8  # Subscription Rights 신주인수권증서
    ELW = 9 # Equity Linked Warrant 주식워런트증권
    ETF = 10    # Exchange-Traded Fund 상장지수펀드
    BC = 11 # Benefit Certificate 수익증권
    FETF = 12 # Foreign ETF
    FOREIGN = 13 # Foreign Securities
    FUTURE = 14
    OPTION = 15
    KONEX = 16
    ETN = 17    # Exchange-Traded Note

class TickerInfo:
    def __init__(self, code: str):
        self._code = code

    def __getattr__(self, name):
        if not hasattr(CpCodeMgr(), name):
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'"
            )

        # filter out non-ticker functions
        if (name in (
            'GetMiniFutureList',
            'GetMiniOptionList', 
            'ReLoadPortData',
            'GetStockListByMarket', # market function
            'GetGroupCodeList',     # group function
            'GetGroupName',
            'GetIndustryList',      # industry function
            'GetIndustryName',
            'GetMemberList',        # trade source member company
            'GetMemberName',
            'GetKosdaqIndustry1List',
            'GetKosdaqIndustry2List',
            'GetKostarFutureList',
            'GetKostarOptionList',
            #'GetFOTradeUnit',
            'GetIndustryGroupCodeList',
            'GetIndexCodeList',
            #'GetListingStock', outstanding shares
            'GetMarketStartTime',
            'GetMarketEndTime',
            'IsFrnMember',
            #'GetNewMarketStartTime',
            #'GetNewMarketEndTime',
            #'GetTickUnit',
            #'GetTickValue',
            'OvFutGetAllCodeList',
            'OvFutGetExchList',
            #'OvFutCodeToName',
            #'OvFutExchCode',
            #'OvFutGetLastTradeDate',
            #'OvFutGetProdCode',
            #'GetStartTime',
            #'GetEndTime',
            #'IsTradeCondition',
            'GetStockFutureList',
            'GetStockFutureBaseList',
            #'GetStockFutureListByBaseCode',
            #'GetStockFutureBaseCode'
        )):
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'. use CpCodeMgr instead."
            )

        attr = getattr(CpCodeMgr(), name)
        def method(self, *args, **kwargs):
            return attr(self._code, *args, **kwargs)
        setattr(TickerInfo, name, method)

        # method bound to self
        # at the very first time to be retrieved by __getattr__
        return method.__get__(self, TickerInfo)

class CpCodeMgr(CybosIfBase):
    _instance = None

    Market = Market
    SecType = SecType

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = \
                super(CpCodeMgr, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            super().__init__('CpUtil.CpCodeMgr', 'CpCodeMgr')
            self._initialized = True

    def GetStockMarketKind(self, code: str):
        return Market(self.com.GetStockMarketKind(code))

    def GetStockSectionKind(self, code: str):
        return SecType(self.com.GetStockSectionKind(code))

    def GetStockListedDate(self, code: str):
        d = str(self.com.GetStockListedDate(code))
        #datetime.strptime(listing_date, '%Y-%m-%d').date()
        return datetime(int(d[:4]), int(d[4:6]), int(d[6:]))


if __name__ == '__main__':
    cpcodemgr = CpCodeMgr()
    code = 'A005930'
    print(cpcodemgr.CodeToName(code))
    print(cpcodemgr.GetStockMarketKind(code))
    print(cpcodemgr.GetStockListedDate(code))
    print(cpcodemgr is CpCodeMgr())

    ti = TickerInfo(code)
    print(ti.CodeToName())
    print(ti.CodeToName())
    print(ti.GetStockSectionKind())
    print(ti.GetStockMarketKind())
    print(ti.GetStockListedDate())
