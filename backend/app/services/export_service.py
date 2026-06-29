"""通用数据导出服务：支持 JSON / CSV / Excel(.xlsx)

调用方式：
    from .export_service import build_export_response
    return build_export_response(rows, filename="crawlers", fmt="xlsx")

rows 为 List[dict]，所有 dict 应拥有相同的字段顺序（用 OrderedDict 或先序列化）。
"""
import csv
import io
import json
from datetime import datetime
from typing import List, Dict, Any
from urllib.parse import quote

from fastapi.responses import Response


def _serialize(value: Any) -> Any:
    """把 SQLAlchemy/Pydantic 不易序列化的对象转为可序列化值"""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    if value is None:
        return ""
    return value


def _normalize_rows(rows: List[Dict[str, Any]]) -> tuple[List[str], List[List[Any]]]:
    """提取列顺序和二维数据。以第一条记录的 key 顺序为准。"""
    if not rows:
        return [], []
    columns = list(rows[0].keys())
    data = [[_serialize(r.get(c)) for c in columns] for r in rows]
    return columns, data


def to_json_bytes(rows: List[Dict[str, Any]]) -> bytes:
    payload = [{k: _serialize(v) for k, v in r.items()} for r in rows]
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def to_csv_bytes(rows: List[Dict[str, Any]]) -> bytes:
    columns, data = _normalize_rows(rows)
    buf = io.StringIO()
    # 加 UTF-8 BOM 让 Excel 正确识别中文
    writer = csv.writer(buf)
    writer.writerow(columns)
    writer.writerows(data)
    return b"\xef\xbb\xbf" + buf.getvalue().encode("utf-8")


def to_xlsx_bytes(rows: List[Dict[str, Any]]) -> bytes:
    from openpyxl import Workbook
    columns, data = _normalize_rows(rows)
    wb = Workbook()
    ws = wb.active
    ws.title = "数据"
    ws.append(columns)
    for row in data:
        ws.append(row)
    # 自适应列宽（粗略）
    for i, col in enumerate(columns, start=1):
        max_len = max([len(str(col))] + [len(str(row[i - 1])) for row in data if row[i - 1] is not None])
        ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = min(max_len + 4, 60)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


_FORMAT_MAP = {
    "json": ("application/json", ".json", to_json_bytes),
    "csv": ("text/csv", ".csv", to_csv_bytes),
    "xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".xlsx", to_xlsx_bytes),
}


def build_export_response(rows: List[Dict[str, Any]], filename: str, fmt: str = "xlsx") -> Response:
    """构造文件下载响应。

    :param rows: 已转为 dict 的记录列表
    :param filename: 不带扩展名的文件名
    :param fmt: json / csv / xlsx
    """
    fmt = (fmt or "xlsx").lower()
    if fmt not in _FORMAT_MAP:
        fmt = "xlsx"
    content_type, ext, builder = _FORMAT_MAP[fmt]
    body = builder(rows)
    # RFC 5987 编码文件名，支持中文
    safe_name = filename.encode("utf-8").decode("latin-1", errors="replace")
    download_name = f"{filename}{ext}"
    return Response(
        content=body,
        media_type=content_type,
        headers={
            "Content-Disposition": (
                f"attachment; filename=\"{safe_name}{ext}\"; "
                f"filename*=UTF-8''{quote(download_name)}"
            ),
        },
    )
