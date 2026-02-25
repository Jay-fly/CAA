import logging
import time

import httpx

from caa_nfz.config import BASE_URL, LAYERS, PAGE_SIZE

log = logging.getLogger(__name__)


def fetch_layer(name: str, endpoint: str) -> list[dict]:
    """分頁抓取單一圖層的所有 features。"""
    url = f"{BASE_URL}{endpoint}/query"
    all_features: list[dict] = []
    offset = 0
    page = 0

    with httpx.Client(verify=False, timeout=30) as client:
        while True:
            start = time.time()
            resp = client.get(
                url,
                params={
                    "where": "1=1",
                    "outFields": "*",
                    "returnGeometry": "true",
                    "outSR": "4326",
                    "resultOffset": str(offset),
                    "resultRecordCount": str(PAGE_SIZE),
                    "f": "json",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            elapsed = time.time() - start

            features = data.get("features", [])
            exceeded = data.get("exceededTransferLimit", False)

            all_features.extend(features)
            page += 1
            log.info("[%s] 第 %d 頁: %d 筆 (%.2fs)", name, page, len(features), elapsed)

            if not exceeded or len(features) == 0:
                break

            offset += len(features)

    log.info("[%s] 完成: %d 筆, %d 次請求", name, len(all_features), page)
    return all_features


def fetch_all_layers() -> dict[str, list[dict]]:
    """抓取所有圖層，回傳 {layer_name: [features]}。"""
    result: dict[str, list[dict]] = {}
    for name, cfg in LAYERS.items():
        result[name] = fetch_layer(name, cfg["endpoint"])
    return result


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(message)s",
        datefmt="%H:%M:%S",
    )

    log.info("開始抓取 CAA 無人機禁飛區資料")
    all_data = fetch_all_layers()

    # 摘要
    print("\n===== 摘要 =====")
    total = 0
    for name, features in all_data.items():
        print(f"  {name}: {len(features)} 筆")
        total += len(features)
    print(f"  合計: {total} 筆")


if __name__ == "__main__":
    main()
