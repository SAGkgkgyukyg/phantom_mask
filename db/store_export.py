import re
import json
import os
from datetime import datetime
import time


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


def parse_opening_hours(opening_hours):
    """
    從營業時間字串解析出週日、開始時間和結束時間
    支援格式:
    1. "Mon - Fri 08:00 - 17:00" 代表從周一到周五的 0800~1700
    2. "Mon, Wed, Fri 08:00 - 12:00 / Tue, Thur 14:00 - 18:00" 代表週一、三、五的 0800~1200 和週二、四的 1400~1800
    3. "Mon - Fri 08:00 - 17:00 / Sat, Sun 08:00 - 12:00" 代表週一到週五的 0800~1700 和週六、日的 0800~1200
    """
    if not opening_hours:
        return []

    # 建立星期對照表
    day_map = {
        'Mon': 1, 'Tue': 2, 'Wed': 3, 'Thu': 4, 'Thur': 4, 'Fri': 5, 'Sat': 6, 'Sun': 7
    }

    # 分割不同時段 (由 / 分隔)
    periods = opening_hours.split('/')
    results = []

    for period in periods:
        # 將星期與時間字串分離並解析
        # 星期需判斷是否為範圍或列表
        period = period.strip()
        match = re.match(
            r'^(.*?)\s+(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})$', period)
        if not match:
            continue
        # 解析星期部分
        days_part = match.group(1).strip()
        # - means range
        # , means list
        days = []
        range_match = re.search(r'(\w+)\s*-\s*(\w+)', days_part)
        if range_match:
            start_day = range_match.group(1)
            end_day = range_match.group(2)

            if start_day in day_map and end_day in day_map:
                start_idx = day_map[start_day]
                end_idx = day_map[end_day]

                # 處理如 "Fri - Sun" 的情況
                if start_idx <= end_idx:
                    days.extend(range(start_idx, end_idx + 1))
                else:
                    # 如 "Fri - Mon" 的跨週情況
                    days.extend(range(start_idx, 8))
                    days.extend(range(1, end_idx + 1))
        else:
            # 處理列表格式 "Mon, Wed, Fri"
            for day in re.findall(r'\b(Mon|Tue|Wed|Thu|Thur|Fri|Sat|Sun)\b', days_part):
                if day in day_map:
                    days.append(day_map[day])
        open_time = match.group(2)
        close_time = match.group(3)
        # 判斷是否跨日
        is_overnight = False
        if open_time > close_time:
            is_overnight = True
        # 建立營業時間記錄
        for day in days:
            results.append({
                'weekday_id': day,
                'open_time': open_time,
                'close_time': close_time,
                'is_overnight': is_overnight
            })

    return results


def create_weekdays_data():
    """
    建立星期資料表，避免重複儲存字串
    """
    return [
        {'weekday_id': 1, 'name': 'Monday', 'short_name': 'Mon'},
        {'weekday_id': 2, 'name': 'Tuesday', 'short_name': 'Tue'},
        {'weekday_id': 3, 'name': 'Wednesday', 'short_name': 'Wed'},
        {'weekday_id': 4, 'name': 'Thursday', 'short_name': 'Thu'},
        {'weekday_id': 5, 'name': 'Friday', 'short_name': 'Fri'},
        {'weekday_id': 6, 'name': 'Saturday', 'short_name': 'Sat'},
        {'weekday_id': 7, 'name': 'Sunday', 'short_name': 'Sun'}
    ]


def normalize_mask_data(pharmacies_data):
    """
    正規化藥房和口罩資料，建立適合資料庫的結構
    """
    # 初始化結果集合
    brands = set()
    colors = set()
    pack_sizes = set()
    mask_types = []
    pharmacies = []
    pharmacy_hours = []
    inventory = []

    # 追蹤已存在的口罩類型
    mask_type_map = {}
    mask_type_id = 1

    # 追蹤藥房 ID
    pharmacy_id = 1
    schedule_id = 1
    inventory_id = 1

    # 當前時間戳，用於 created_at 和 updated_at
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 處理每個藥房
    for pharmacy_data in pharmacies_data:
        pharmacy_name = pharmacy_data.get('name')
        if not pharmacy_name:
            continue

        opening_hours = pharmacy_data.get('openingHours')

        # 新增藥房資料
        pharmacies.append({
            'pharmacy_id': pharmacy_id,
            'name': pharmacy_name,
            'cash_balance': pharmacy_data.get('cashBalance'),
            'opening_hours': opening_hours,
            'created_at': current_time,
            'updated_at': current_time
        })

        # 解析並新增營業時間
        hours_data = parse_opening_hours(opening_hours)
        for hour in hours_data:
            pharmacy_hours.append({
                'schedule_id': schedule_id,
                'pharmacy_id': pharmacy_id,
                'weekday_id': hour['weekday_id'],
                'open_time': hour['open_time'],
                'close_time': hour['close_time'],
                'is_overnight': hour['is_overnight']
            })
            schedule_id += 1

        # 處理每個口罩
        for mask in pharmacy_data.get('masks', []):
            mask_name = mask.get('name')
            price = mask.get('price')

            if not price:
                continue

            if not mask_name:
                # 處理缺少名稱的口罩 (跳過或以其他方式處理)
                continue

            # 解析口罩名稱
            brand, color, quantity = parse_mask_name(mask_name)

            if not brand or not color or not quantity:
                continue

            # 新增到集合
            brands.add(brand)
            colors.add(color)
            pack_sizes.add(quantity)

            # 建立唯一識別碼
            mask_key = f"{brand}|{color}|{quantity}"

            # 檢查這個口罩類型是否已存在
            if mask_key not in mask_type_map:
                mask_type_map[mask_key] = mask_type_id

                # 新增口罩類型
                mask_types.append({
                    'mask_type_id': mask_type_id,
                    'brand_id': len([b for b in sorted(brands) if b < brand]) + 1,
                    'color_id': len([c for c in sorted(colors) if c < color]) + 1,
                    'pack_size_id': len([p for p in sorted(pack_sizes) if p < quantity]) + 1,
                    'display_name': mask_name
                })

                mask_type_id += 1

            # 新增庫存資料
            inventory.append({
                'inventory_id': inventory_id,
                'pharmacy_id': pharmacy_id,
                'mask_type_id': mask_type_map[mask_key],
                'price': price,
                'quantity': 10,  # 設置默認庫存數量
                'last_updated': current_time
            })
            inventory_id += 1

        pharmacy_id += 1

    # 將集合轉換為列表
    brands_list = [{'brand_id': i+1, 'brand_name': brand, 'created_at': current_time}
                   for i, brand in enumerate(sorted(brands))]
    colors_list = [{'color_id': i+1, 'color_name': color}
                   for i, color in enumerate(sorted(colors))]
    pack_sizes_list = [{'size_id': i+1, 'quantity': size}
                       for i, size in enumerate(sorted(pack_sizes))]

    # 建立星期資料
    weekdays = create_weekdays_data()

    return {
        'pharmacies': pharmacies,
        'weekdays': weekdays,
        'pharmacy_hours': pharmacy_hours,
        'brands': brands_list,
        'colors': colors_list,
        'pack_sizes': pack_sizes_list,
        'mask_types': mask_types,
        'inventory': inventory
    }


def main():
    # 讀取 JSON 檔案
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_PATH = os.path.join(BASE_DIR, '../data/pharmacies.json')

    with open(DATA_PATH, 'r', encoding='utf-8') as file:
        pharmacies_data = json.load(file)

    # 正規化資料
    normalized_data = normalize_mask_data(pharmacies_data)

    # 輸出結果
    print("正規化資料結果:")
    print(f"藥房數量: {len(normalized_data['pharmacies'])}")
    print(f"星期資料: {len(normalized_data['weekdays'])}")
    print(f"營業時間記錄: {len(normalized_data['pharmacy_hours'])}")
    print(f"品牌數量: {len(normalized_data['brands'])}")
    print(f"顏色數量: {len(normalized_data['colors'])}")
    print(f"包裝尺寸數量: {len(normalized_data['pack_sizes'])}")
    print(f"口罩類型數量: {len(normalized_data['mask_types'])}")
    print(f"庫存項目數量: {len(normalized_data['inventory'])}")

    # 將結果寫入檔案
    output_dir = os.path.join(BASE_DIR, '../db/normalized')
    os.makedirs(output_dir, exist_ok=True)

    for name, data in normalized_data.items():
        output_path = os.path.join(output_dir, f"{name}.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\n正規化資料已儲存至: {output_dir}")


if __name__ == "__main__":
    main()
