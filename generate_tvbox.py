import json
import hashlib

def convert_to_tvbox():
    # 读取巡检过滤后的 lite.json
    try:
        with open("lite.json", "r", encoding="utf-8") as f:
            kvideo_data = json.load(f)
    except Exception as e:
        print(f"读取 lite.json 失败: {e}")
        return

    # 若 lite.json 外层有 key（如 {"sites": [...]}），按实际结构获取列表
    items = kvideo_data if isinstance(kvideo_data, list) else kvideo_data.get("sites", [])

    tvbox_sites = []
    for item in items:
        # 兼容不同的 api 字段命名
        api_url = item.get("api") or item.get("baseUrl")
        name = item.get("name", "未命名源")
        
        if not api_url:
            continue

        # 生成唯一 key
        site_key = "cms_" + hashlib.md5(api_url.encode("utf-8")).hexdigest()[:8]

        tvbox_sites.append({
            "key": site_key,
            "name": name,
            "type": 1,              # 1 代表苹果 CMS (json) 接口
            "api": api_url,
            "searchable": 1,
            "quickSearch": 1,
            "filterable": 1
        })

    tvbox_config = {
        "spider": "",
        "wallpaper": "http://饭太硬.top/深色壁纸/api.php",
        "sites": tvbox_sites
    }

    with open("tvbox.json", "w", encoding="utf-8") as f:
        json.dump(tvbox_config, f, ensure_ascii=False, indent=2)
    print(f"转换成功，已生成包含 {len(tvbox_sites)} 个有效源的 tvbox.json")

if __name__ == "__main__":
    convert_to_tvbox()
