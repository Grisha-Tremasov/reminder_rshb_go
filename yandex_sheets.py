import os
import tempfile
import httpx
import fastexcel
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

    # Сохраняем во временный файл для fastexcel
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp.write(file_resp.content)
        tmp_path = tmp.name

    try:
        excel = fastexcel.read_excel(tmp_path)
        # header_row=1 означает, что заголовки находятся во 2-й строке Excel (индексация с 0)
        sheet = excel.load_sheet_by_name(SHEET_NAME, header_row=1)
        data_dict = sheet.to_arrow().to_pydict()

        cols = list(data_dict.values())
        employees = cols[0]   # Колонка A: Сотрудник
        days_list = cols[10]  # Колонка K: Осталось до смены пароля

        employees_data: dict[str, float | None] = {}
        for emp, days in zip(employees, days_list):
            if emp and str(emp).strip():
                emp_name = str(emp).strip()
                parsed_days = float(days) if isinstance(days, (int, float)) else None
                employees_data[emp_name] = parsed_days

        return employees_data

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

