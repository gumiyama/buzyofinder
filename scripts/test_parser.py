import re

def _parse_yen_value(value_text):
    if not value_text or value_text == '-':
        return None
        
    # 全角を半角に、カンマを除去、括弧内を除去
    text = value_text.translate(str.maketrans('０１２３４５６７８９（）／', '0123456789()/'))
    text = text.replace(',', '')
    # 括弧内の除去（再帰的な対応は困難だが、SUUMOの形式に合わせて強化）
    text = re.sub(r'\(.*?\)', '', text)
    text = re.sub(r'（.*?）', '', text)
    
    total_yen = 0
    
    # 億の処理
    oku_match = re.search(r'(\d+)億', text)
    if oku_match:
        total_yen += int(oku_match.group(1)) * 100000000
    
    # 万の処理
    man_match = re.search(r'(\d+)万', text)
    if man_match:
        total_yen += int(man_match.group(1)) * 10000
        
    # 円の処理（「万」の後に続く数字も含む）
    # 例：「1万4000円」の「4000」
    leftover_match = re.search(r'(?:万|億|^)(\d+)円', text)
    if leftover_match:
        total_yen += int(leftover_match.group(1))
    elif not oku_match and not man_match:
        # 「万」も「億」も「円」もないが数字だけある場合
        num_match = re.search(r'(\d+)', text)
        if num_match:
            total_yen = int(num_match.group(1))
            
    return total_yen if total_yen > 0 else None

# テスト
test_cases = [
    "1万4000円／月（委託(巡回)）",
    "15,270円",
    "1万330円／月",
    "7,310円",
    "1億1680万円",
    "1,234円",
    "-",
    "0円"
]

for tc in test_cases:
    print(f"Input: {tc} -> Output: {_parse_yen_value(tc)}")
