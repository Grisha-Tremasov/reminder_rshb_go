import io
import os
import httpx
from python_calamine import CalamineWorkbook
from dotenv import load_dotenv

load_dotenv()

YANDEX_TOKEN = os.getenv("YANDEX_TOKEN")
PUBLIC_URL = os.getenv("YANDEX_PUBLIC_URL")
SHEET_NAME = "УЗ ПРОД"


def get_sheet_data() -> dict[str, float | None]:
    headers = {"Authorization": f"OAuth {YANDEX_TOKEN}"}
    api_url = "https://cloud-api.yandex.net/v1/disk/public/resources/download"

    with httpx.Client(follow_redirects=True, headers=headers) as client:
        resp = client.get(api_url, params={"public_key": PUBLIC_URL})
        resp.raise_for_status()
        download_url = resp.json()["href"]

        file_resp = client.get(download_url)
        file_resp.raise_for_status()

    wb = CalamineWorkbook.from_filelike(io.BytesIO(file_resp.content))
    rows = wb.get_sheet_by_name(SHEET_NAME).to_python()

    # Словарь вида: {"Фамилия Имя Отчество": days_left}
    employees_data: dict[str, float | None] = {}

    for idx in range(2, len(rows)):
        row = rows[idx]
        emp = row[0] if len(row) > 0 else None
        days = row[10] if len(row) > 10 else None

        if emp and str(emp).strip():
            emp_name = str(emp).strip()
            # Преобразуем число дней в float или None, если пусто
            parsed_days = float(days) if isinstance(days, (int, float)) else None
            employees_data[emp_name] = parsed_days

    return employees_data
