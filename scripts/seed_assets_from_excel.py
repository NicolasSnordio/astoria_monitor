from __future__ import annotations

import argparse
import re
import sys
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path
from xml.etree import ElementTree as ET

from sqlalchemy import select

from backend.app.database import SessionLocal
from backend.app.models import Asset


NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pkgrel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def _cell_column(ref: str) -> int:
    letters = re.sub(r"[^A-Z]", "", ref.upper())
    value = 0
    for letter in letters:
        value = value * 26 + (ord(letter) - ord("A") + 1)
    return value - 1


def _read_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    strings = []
    for item in root.findall("main:si", NS):
        text = "".join(node.text or "" for node in item.findall(".//main:t", NS))
        strings.append(text)
    return strings


def _first_sheet_path(zf: zipfile.ZipFile) -> str:
    workbook = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    first_sheet = workbook.find("main:sheets/main:sheet", NS)
    if first_sheet is None:
        raise RuntimeError("A planilha nao possui abas.")
    relationship_id = first_sheet.attrib[f"{{{NS['rel']}}}id"]
    for rel in rels.findall("pkgrel:Relationship", NS):
        if rel.attrib["Id"] == relationship_id:
            target = rel.attrib["Target"].lstrip("/")
            return target if target.startswith("xl/") else f"xl/{target}"
    raise RuntimeError("Nao foi possivel localizar a primeira aba da planilha.")


def _cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    value_node = cell.find("main:v", NS)
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.findall(".//main:t", NS)).strip()
    if value_node is None or value_node.text is None:
        return ""
    raw = value_node.text.strip()
    if cell_type == "s":
        return shared_strings[int(raw)].strip()
    return raw


def _rows_from_xlsx(path: Path) -> list[dict[str, str]]:
    with zipfile.ZipFile(path) as zf:
        shared_strings = _read_shared_strings(zf)
        sheet = ET.fromstring(zf.read(_first_sheet_path(zf)))
        raw_rows: list[list[str]] = []
        for row in sheet.findall(".//main:sheetData/main:row", NS):
            values: list[str] = []
            for cell in row.findall("main:c", NS):
                col_index = _cell_column(cell.attrib["r"])
                while len(values) <= col_index:
                    values.append("")
                values[col_index] = _cell_value(cell, shared_strings)
            raw_rows.append(values)

    if not raw_rows:
        return []

    headers = [header.strip() for header in raw_rows[0]]
    records = []
    for row_number, row in enumerate(raw_rows[1:], start=2):
        record = {headers[index]: row[index].strip() if index < len(row) else "" for index in range(len(headers))}
        if any(record.values()):
            record["_source_key"] = f"Pasta1.xlsx:Planilha1:{row_number}"
            records.append(record)
    return records


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    if not cleaned:
        return None
    return re.sub(r"\s+", " ", cleaned)


def _upper(value: str | None) -> str | None:
    cleaned = _clean(value)
    return cleaned.upper() if cleaned else None


def _parse_excel_date(value: str | None) -> date | None:
    cleaned = _clean(value)
    if not cleaned:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            pass
    try:
        return (datetime(1899, 12, 30) + timedelta(days=float(cleaned))).date()
    except ValueError:
        return None


def _find_existing(record: dict[str, str], db) -> Asset | None:
    source_key = record.get("_source_key")
    if source_key:
        asset = db.scalar(select(Asset).where(Asset.notes == f"seed:{source_key}"))
        if asset is not None:
            return asset

    hostname = _upper(record.get("Nome do Comp."))
    service_tag = _upper(record.get("ServiceTag"))
    patrimony = _clean(record.get("Patrimonio"))
    conditions = []
    if hostname:
        conditions.append(Asset.expected_hostname == hostname)
    if service_tag:
        conditions.append(Asset.service_tag == service_tag)
    if patrimony:
        conditions.append(Asset.patrimony_code == patrimony)
    for condition in conditions:
        asset = db.scalar(select(Asset).where(condition))
        if asset is not None:
            return asset
    return None


def seed_assets(path: Path) -> tuple[int, int]:
    records = _rows_from_xlsx(path)
    created = 0
    updated = 0
    with SessionLocal() as db:
        for record in records:
            asset = _find_existing(record, db)
            if asset is None:
                asset = Asset()
                db.add(asset)
                created += 1
            else:
                updated += 1

            asset.expected_hostname = _upper(record.get("Nome do Comp."))
            asset.sector = _clean(record.get("Setor"))
            asset.assigned_user = _clean(record.get("Usuário"))
            asset.patrimony_code = _clean(record.get("Patrimonio"))
            asset.equipment_type_model = _clean(record.get("Tipo / Modelo"))
            asset.service_tag = _upper(record.get("ServiceTag"))
            asset.purchase_date = _parse_excel_date(record.get("Dt Compra Comp."))
            asset.warranty_end_date = _parse_excel_date(record.get("Dt Fim Garantia"))
            asset.monitor_description = _clean(record.get("Monitor / Tela"))
            asset.monitor_patrimony_code = _clean(record.get("Nº Pat. Monit"))
            asset.office_version = _clean(record.get("Versão Office "))
            asset.office_activation_email = _clean(record.get("E-mail / Ativação Office"))
            asset.notes = f"seed:{record['_source_key']}"

        db.commit()
    return created, updated


def main() -> int:
    parser = argparse.ArgumentParser(description="Carrega o cadastro inicial de ativos Astoria a partir de uma planilha XLSX.")
    parser.add_argument("xlsx_path", type=Path)
    args = parser.parse_args()
    if not args.xlsx_path.exists():
        print(f"Arquivo nao encontrado: {args.xlsx_path}", file=sys.stderr)
        return 1
    created, updated = seed_assets(args.xlsx_path)
    print(f"Ativos criados: {created}")
    print(f"Ativos atualizados: {updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
