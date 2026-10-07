from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import re
import requests
from bs4 import BeautifulSoup


BASE_URL = "https://reg2.sut.ac.th/registrar/class_info_1.asp"


def clean_text(text):
    return re.sub(r"\s+", " ", text).strip()


def build_url(acadyear, semester, coursecode="", coursename=""):
    # The SUT site expects spaces as '+'. Keep '*' in coursecode as a wildcard.
    coursecode = coursecode.replace(" ", "+")
    coursename = coursename.replace(" ", "+")

    params = (
        f"coursestatus=O00"
        f"&facultyid=all"
        f"&maxrow=50"
        f"&CAMPUSID="
        f"&LEVELID="
        f"&cmd=2"
        f"&acadyear={acadyear}"
        f"&semester={semester}"
        f"&coursecode={coursecode}"
        f"&coursename={coursename}"
    )
    return f"{BASE_URL}?{params}"


def parse_course_table(html):
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")

    results = []

    for table in tables:
        rows = table.find_all("tr")
        if not rows:
            continue

        parsed_rows = []
        for row in rows:
            cells = row.find_all(["th", "td"])
            values = [clean_text(cell.get_text(" ", strip=True)) for cell in cells]
            if any(values):
                parsed_rows.append(values)

        if len(parsed_rows) < 2:
            continue

        headers = parsed_rows[0]

        # Only treat a table as course data when it looks like a result table.
        header_text = " ".join(headers).lower()
        if not any(
            keyword in header_text
            for keyword in ("course", "รหัส", "วิชา", "section", "หน่วยกิต")
        ):
            continue

        for row in parsed_rows[1:]:
            item = {}
            for index, value in enumerate(row):
                key = headers[index] if index < len(headers) else f"column_{index + 1}"
                key = key or f"column_{index + 1}"
                item[key] = value

            if item:
                results.append(item)

    return results


def fetch_courses(acadyear, semester, coursecode="", coursename=""):
    url = build_url(acadyear, semester, coursecode, coursename)

    response = requests.get(
        url,
        timeout=15,
        headers={
            "User-Agent": "sut-course-api/1.0"
        },
    )
    response.raise_for_status()

    data = parse_course_table(response.content)

    return {
        "url": url,
        "data": data,
    }


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)

        acadyear = query.get("acadyear", ["2569"])[0].strip()
        semester = query.get("semester", ["2"])[0].strip()
        coursecode = query.get("coursecode", [""])[0].strip()
        coursename = query.get("coursename", [""])[0].strip()

        if not acadyear.isdigit():
            return self.send_json(
                400,
                {"success": False, "error": "acadyear must be numeric"},
            )

        if not semester.isdigit():
            return self.send_json(
                400,
                {"success": False, "error": "semester must be numeric"},
            )

        try:
            result = fetch_courses(
                acadyear,
                semester,
                coursecode,
                coursename,
            )

            if not result["data"]:
                return self.send_json(
                    404,
                    {
                        "success": False,
                        "error": "No course data found",
                        "query": {
                            "acadyear": acadyear,
                            "semester": semester,
                            "coursecode": coursecode,
                            "coursename": coursename,
                        },
                    },
                )

            return self.send_json(
                200,
                {
                    "success": True,
                    "query": {
                        "acadyear": acadyear,
                        "semester": semester,
                        "coursecode": coursecode,
                        "coursename": coursename,
                    },
                    "data": result["data"],
                },
            )

        except requests.RequestException as exc:
            return self.send_json(
                502,
                {
                    "success": False,
                    "error": "Failed to fetch SUT registrar",
                    "detail": str(exc),
                },
            )
        except Exception as exc:
            return self.send_json(
                500,
                {
                    "success": False,
                    "error": "Internal server error",
                    "detail": str(exc),
                },
            )

    def send_json(self, status, payload):
        import json

        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
