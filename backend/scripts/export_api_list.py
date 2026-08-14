"""
scripts/export_api_list.py — Export API endpoint list จาก OpenAPI spec เป็น Excel/CSV

วิธีการทำงาน:
1. ดึง openapi.json จาก running server (http://localhost:8000/openapi.json)
   หรือ fallback อ่านจากไฟล์ local ถ้าไม่ได้รัน server
2. Parse โครงสร้าง paths แล้วดึงข้อมูลแต่ละ endpoint
3. Export เป็น .xlsx และ .csv พร้อม timestamp ในชื่อไฟล์

รันด้วย: uv run python scripts/export_api_list.py
"""

import json
import sys
from datetime import datetime
from pathlib import Path

try:
    import httpx
    import pandas as pd
    from openpyxl.utils import get_column_letter
except ImportError:
    print("Please install: uv add httpx pandas openpyxl")
    sys.exit(1)

OPENAPI_URL = "http://localhost:8000/openapi.json"
OUTPUT_DIR = Path(__file__).parent.parent / "storage" / "artifacts"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def fetch_openapi_spec() -> dict:
    """ดึง OpenAPI spec จาก server หรืออ่านจาก local file"""
    try:
        resp = httpx.get(OPENAPI_URL, timeout=5)
        resp.raise_for_status()
        print(f"[OK] Fetching spec from {OPENAPI_URL}")
        return resp.json()
    except Exception as e:
        print(f"[WARN] Server not ready ({e}) — trying local file...")

    local = Path(__file__).parent / "openapi.json"
    if local.exists():
        print(f"[OK] Reading from {local}")
        return json.loads(local.read_text(encoding="utf-8"))

    print("[ERROR] Spec not found on server or local file")
    sys.exit(1)


def parse_endpoints(spec: dict) -> list[dict]:
    """Parse paths จาก OpenAPI spec เป็น list ของ dict"""
    rows = []
    paths = spec.get("paths", {})

    for path, methods in paths.items():
        for method, operation in methods.items():
            if method.upper() not in ("GET", "POST", "PUT", "PATCH", "DELETE"):
                continue

            # Request body schema
            req_schema = ""
            if "requestBody" in operation:
                content = operation["requestBody"].get("content", {})
                for mime, schema_info in content.items():
                    ref = schema_info.get("schema", {}).get("$ref", "")
                    req_schema = ref.split("/")[-1] if ref else mime

            # Response model
            responses = operation.get("responses", {})
            resp_codes = ", ".join(responses.keys())
            resp_model = ""
            for code, resp_info in responses.items():
                content = resp_info.get("content", {})
                for mime, schema_info in content.items():
                    ref = schema_info.get("schema", {}).get("$ref", "")
                    if ref:
                        resp_model = ref.split("/")[-1]
                        break

            rows.append({
                "Method":          method.upper(),
                "Path":            path,
                "Tag":             ", ".join(operation.get("tags", [])),
                "Summary":         operation.get("summary", ""),
                "Description":     operation.get("description", "").strip()[:200],
                "Request Schema":  req_schema,
                "Response Model":  resp_model,
                "Status Codes":    resp_codes,
            })

    return rows


def export_to_files(rows: list[dict]) -> None:
    """Export เป็น xlsx และ csv พร้อม timestamp ในชื่อไฟล์"""
    today = datetime.now().strftime("%Y-%m-%d")
    df = pd.DataFrame(rows)

    # ── Excel ──
    xlsx_path = OUTPUT_DIR / f"api_snapshot_{today}.xlsx"
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="API Endpoints")
        ws = writer.sheets["API Endpoints"]
        for i, col in enumerate(df.columns, 1):
            max_len = max(df[col].astype(str).map(len).max(), len(col)) + 4
            ws.column_dimensions[get_column_letter(i)].width = min(max_len, 60)
    print(f"[OK] Excel: {xlsx_path}")

    # ── CSV ──
    csv_path = OUTPUT_DIR / f"api_snapshot_{today}.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"[OK] CSV:   {csv_path}")

    print(f"\nTotal {len(rows)} endpoint(s)")


if __name__ == "__main__":
    spec = fetch_openapi_spec()
    rows = parse_endpoints(spec)
    export_to_files(rows)
