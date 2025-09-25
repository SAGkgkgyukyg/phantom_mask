import re
import json
import os
from datetime import datetime


def parse_mask_name(mask_name):
    """
    從口罩名稱字串中解析出品牌名稱、顏色和包裝數量
    格式: "[品牌名稱] ([顏色]) ([數量] per pack)"
    """
    if not mask_name:
        return None, None, None

    # 使用正則表達式解析名稱
    pattern = r'^(.*?)\s+\((.*?)\)\s+\((\d+)\s+per\s+pack\)$'
    match = re.match(pattern, mask_name)

    if match:
        brand = match.group(1).strip()
        color = match.group(2).strip()
        quantity = int(match.group(3))
        return brand, color, quantity

    return None, None, None


def normalize_user_data(users_data):
    """
    正規化使用者和購買資料，建立適合資料庫的結構
    """
    # 初始化結果集合
    users = []
    purchase_histories = []
    purchase_details = []

    # 追蹤藥局和口罩類型的映射
    pharmacy_map = {}
    mask_type_map = {}

    # ID 計數器
    user_id = 1
    purchase_id = 1
    detail_id = 1
    pharmacy_id = 1
    mask_type_id = 1

    # 當前時間戳，用於 created_at 和 updated_at
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 處理每個使用者
    for user_data in users_data:
        user_name = user_data.get('name')
        cash_balance = user_data.get('cashBalance', 0)
        
        if not user_name:
            continue

        # 新增使用者資料
        users.append({
            'id': user_id,
            'name': user_name,
            'cash_balance': cash_balance,
            'created_at': current_time,
            'updated_at': current_time
        })

        # 處理購買歷史記錄
        for history in user_data.get('purchaseHistories', []):
            pharmacy_name = history.get('pharmacyName')
            mask_name = history.get('maskName')
            transaction_amount = history.get('transactionAmount')
            transaction_date = history.get('transactionDate')

            if not all([pharmacy_name, mask_name, transaction_amount, transaction_date]):
                continue

            # 處理藥局映射
            if pharmacy_name not in pharmacy_map:
                pharmacy_map[pharmacy_name] = pharmacy_id
                pharmacy_id += 1

            # 處理口罩類型映射
            if mask_name not in mask_type_map:
                mask_type_map[mask_name] = mask_type_id
                mask_type_id += 1

            # 新增購買歷史記錄
            purchase_histories.append({
                'id': purchase_id,
                'user_id': user_id,
                'pharmacy_id': pharmacy_map[pharmacy_name],
                'transaction_amount': transaction_amount,
                'transaction_date': transaction_date,
                'created_at': current_time
            })

            # 解析口罩名稱以獲取詳細資訊
            # brand, color, pack_quantity = parse_mask_name(mask_name)

            # 假設每次交易購買一包口罩
            quantity = 1
            price = transaction_amount  # 單包價格等於交易金額
            total_price = transaction_amount

            # 新增購買詳細資訊
            purchase_details.append({
                'id': detail_id,
                'purchase_id': purchase_id,
                'mask_type_id': mask_type_map[mask_name],
                'quantity': quantity,
                'price': price,
                'total_price': total_price,
                'created_at': current_time
            })

            purchase_id += 1
            detail_id += 1

        user_id += 1

    return {
        'users': users,
        'purchase_histories': purchase_histories,
        'purchase_details': purchase_details
    }


def main():
    # 讀取 JSON 檔案
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_PATH = os.path.join(BASE_DIR, '../data/users.json')

    with open(DATA_PATH, 'r', encoding='utf-8') as file:
        users_data = json.load(file)

    # 正規化資料
    normalized_data = normalize_user_data(users_data)

    # 輸出結果統計
    print("正規化資料結果:")
    print(f"使用者數量: {len(normalized_data['users'])}")
    print(f"購買歷史記錄: {len(normalized_data['purchase_histories'])}")
    print(f"購買詳細記錄: {len(normalized_data['purchase_details'])}")

    # 將結果寫入檔案
    output_dir = os.path.join(BASE_DIR, 'normalized')
    os.makedirs(output_dir, exist_ok=True)

    for name, data in normalized_data.items():
        output_path = os.path.join(output_dir, f"{name}.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\n正規化資料已儲存至: {output_dir}")


if __name__ == "__main__":
    main()
