"""
通貨ペア正規化ルール（USD基準統一）

設計原則:
- 内部表現はUSD基準（USDニュートラル）に統一
- すべて「USD / 通貨」表現に正規化
- HistDataの元表記（EURUSD/USDJPYなど）は入口で吸収

正規化ルール:
- XXXUSD（EURUSD, GBPUSD, AUDUSD, NZDUSD）: そのまま使う
- USDXXX（USDJPY, USDCAD, USDCHF）: 逆数にする

内部では「1 通貨が何 USDか」に必ず揃える。
"""

# 通貨ペア正規化ルール
PAIR_RULES = {
    # XXXUSD: そのまま使用（EUR/USD = EURUSD）
    "EURUSD": {"invert": False, "output_name": "EURUSD"},
    "GBPUSD": {"invert": False, "output_name": "GBPUSD"},
    "AUDUSD": {"invert": False, "output_name": "AUDUSD"},
    "NZDUSD": {"invert": False, "output_name": "NZDUSD"},
    
    # USDXXX: 逆数にする（JPY/USD = 1 / USDJPY）
    "USDJPY": {"invert": True, "output_name": "JPYUSD"},
    "USDCAD": {"invert": True, "output_name": "CADUSD"},
    "USDCHF": {"invert": True, "output_name": "CHFUSD"},
}

# HistDataで使用される通貨ペアリスト（入力用）
HISTDATA_PAIRS = list(PAIR_RULES.keys())

# 正規化後の通貨ペアリスト（出力用）
OUTPUT_PAIRS = [rule["output_name"] for rule in PAIR_RULES.values()]


def normalize_to_usd_base(price: float, invert: bool) -> float:
    """
    USD基準に正規化
    
    Args:
        price: 元の価格
        invert: Trueの場合は逆数にする（USDXXXの場合）
    
    Returns:
        正規化後の価格（USD基準）
    
    Examples:
        >>> normalize_to_usd_base(1.10, False)  # EURUSD
        1.10
        >>> normalize_to_usd_base(110.0, True)   # USDJPY -> JPYUSD
        0.0090909...
    """
    if invert:
        return 1.0 / price
    return price


def get_pair_rule(pair: str) -> dict:
    """
    通貨ペアのルールを取得
    
    Args:
        pair: 通貨ペア名（例: "EURUSD", "USDJPY"）
    
    Returns:
        ルール辞書（invert, output_name）
    
    Raises:
        KeyError: 未定義の通貨ペアの場合
    """
    if pair not in PAIR_RULES:
        raise KeyError(f"Unknown currency pair: {pair}. Available pairs: {list(PAIR_RULES.keys())}")
    return PAIR_RULES[pair]

