# 精简版 S&P 500 — 选取主要市值股票，覆盖核心板块
SP500_TICKERS: list[dict] = [
    # 信息技术
    {"ticker": "AAPL",  "name": "苹果",     "sector": "信息技术·消费电子"},
    {"ticker": "MSFT",  "name": "微软",     "sector": "信息技术·软件"},
    {"ticker": "NVDA",  "name": "英伟达",   "sector": "信息技术·半导体"},
    {"ticker": "AVGO",  "name": "博通",     "sector": "信息技术·半导体"},
    {"ticker": "ORCL",  "name": "甲骨文",   "sector": "信息技术·软件"},
    {"ticker": "AMD",   "name": "超微半导体","sector": "信息技术·半导体"},
    {"ticker": "QCOM",  "name": "高通",     "sector": "信息技术·半导体"},
    {"ticker": "INTC",  "name": "英特尔",   "sector": "信息技术·半导体"},
    {"ticker": "META",  "name": "Meta",    "sector": "通信服务·社交媒体"},
    {"ticker": "GOOGL", "name": "谷歌",     "sector": "通信服务·互联网"},
    {"ticker": "NFLX",  "name": "奈飞",     "sector": "通信服务·流媒体"},
    # 消费
    {"ticker": "AMZN",  "name": "亚马逊",   "sector": "非必需消费·电商"},
    {"ticker": "TSLA",  "name": "特斯拉",   "sector": "非必需消费·电动车"},
    {"ticker": "HD",    "name": "家得宝",   "sector": "非必需消费·零售"},
    {"ticker": "MCD",   "name": "麦当劳",   "sector": "非必需消费·餐饮"},
    {"ticker": "SBUX",  "name": "星巴克",   "sector": "非必需消费·餐饮"},
    {"ticker": "COST",  "name": "好市多",   "sector": "必需消费·零售"},
    {"ticker": "WMT",   "name": "沃尔玛",   "sector": "必需消费·零售"},
    {"ticker": "KO",    "name": "可口可乐", "sector": "必需消费·饮料"},
    {"ticker": "PEP",   "name": "百事可乐", "sector": "必需消费·饮料"},
    # 金融
    {"ticker": "JPM",   "name": "摩根大通", "sector": "金融·银行"},
    {"ticker": "BAC",   "name": "美国银行", "sector": "金融·银行"},
    {"ticker": "GS",    "name": "高盛",     "sector": "金融·投资银行"},
    {"ticker": "V",     "name": "Visa",    "sector": "金融·支付"},
    {"ticker": "MA",    "name": "万事达",   "sector": "金融·支付"},
    # 医疗
    {"ticker": "JNJ",   "name": "强生",     "sector": "医疗保健·制药"},
    {"ticker": "UNH",   "name": "联合健康", "sector": "医疗保健·保险"},
    {"ticker": "PFE",   "name": "辉瑞",     "sector": "医疗保健·制药"},
    {"ticker": "ABBV",  "name": "艾伯维",   "sector": "医疗保健·制药"},
    {"ticker": "MRK",   "name": "默克",     "sector": "医疗保健·制药"},
    # 能源
    {"ticker": "XOM",   "name": "埃克森美孚","sector": "能源·石油天然气"},
    {"ticker": "CVX",   "name": "雪佛龙",   "sector": "能源·石油天然气"},
    # 工业
    {"ticker": "CAT",   "name": "卡特彼勒", "sector": "工业·机械"},
    {"ticker": "BA",    "name": "波音",     "sector": "工业·航空航天"},
    {"ticker": "HON",   "name": "霍尼韦尔", "sector": "工业·多元化"},
    # 其他常见
    {"ticker": "BRK-B", "name": "伯克希尔", "sector": "金融·多元化"},
    {"ticker": "SPY",   "name": "标普500ETF","sector": "ETF·大盘"},
    {"ticker": "QQQ",   "name": "纳斯达克ETF","sector": "ETF·科技"},
]

FX_PAIRS: list[dict] = [
    {"ticker": "EURUSD=X", "name": "欧元/美元", "sector": "外汇·主要货币对"},
    {"ticker": "GBPUSD=X", "name": "英镑/美元", "sector": "外汇·主要货币对"},
    {"ticker": "USDJPY=X", "name": "美元/日元", "sector": "外汇·主要货币对"},
    {"ticker": "USDCHF=X", "name": "美元/瑞郎", "sector": "外汇·主要货币对"},
    {"ticker": "AUDUSD=X", "name": "澳元/美元", "sector": "外汇·主要货币对"},
    {"ticker": "USDCAD=X", "name": "美元/加元", "sector": "外汇·主要货币对"},
    {"ticker": "NZDUSD=X", "name": "纽元/美元", "sector": "外汇·主要货币对"},
    {"ticker": "EURGBP=X", "name": "欧元/英镑", "sector": "外汇·交叉盘"},
    {"ticker": "EURJPY=X", "name": "欧元/日元", "sector": "外汇·交叉盘"},
    {"ticker": "GBPJPY=X", "name": "英镑/日元", "sector": "外汇·交叉盘"},
    {"ticker": "AUDJPY=X", "name": "澳元/日元", "sector": "外汇·交叉盘"},
    {"ticker": "EURCHF=X", "name": "欧元/瑞郎", "sector": "外汇·交叉盘"},
    {"ticker": "GBPCHF=X", "name": "英镑/瑞郎", "sector": "外汇·交叉盘"},
    {"ticker": "CADJPY=X", "name": "加元/日元", "sector": "外汇·交叉盘"},
    {"ticker": "AUDCAD=X", "name": "澳元/加元", "sector": "外汇·交叉盘"},
    {"ticker": "NZDJPY=X", "name": "纽元/日元", "sector": "外汇·交叉盘"},
    {"ticker": "EURCAD=X", "name": "欧元/加元", "sector": "外汇·交叉盘"},
    {"ticker": "GBPAUD=X", "name": "英镑/澳元", "sector": "外汇·交叉盘"},
    {"ticker": "AUDNZD=X", "name": "澳元/纽元", "sector": "外汇·交叉盘"},
    {"ticker": "CHFJPY=X", "name": "瑞郎/日元", "sector": "外汇·交叉盘"},
]

_TICKER_MAP: dict[str, dict] = {
    item["ticker"]: item
    for item in SP500_TICKERS + FX_PAIRS
}


def get_all_tickers() -> list[dict]:
    return SP500_TICKERS + FX_PAIRS


def get_ticker_info(ticker: str) -> dict | None:
    return _TICKER_MAP.get(ticker)


def is_forex(ticker: str) -> bool:
    return ticker.endswith("=X")
