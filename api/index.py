import re

import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

BASE_URL = "https://reg2.sut.ac.th/registrar/class_info_1.asp"

app = FastAPI(title="SUT Course API", version="0.1.0")


def clean_text(text):
    return re.sub(r"\s+", " ", text).strip()


def build_url(acadyear, semester, coursecode="", coursename=""):
    coursecode = coursecode.replace(" ", "+")
    coursename = coursename.replace(" ", "+")

    return (
        f"{BASE_URL}?coursestatus=O00"
        f"&facultyid=all&maxrow=50&CAMPUSID=&LEVELID=&cmd=2"
        f"&acadyear={acadyear}&semester={semester}"
        f"&coursecode={coursecode}&coursename={coursename}"
    )


def parse_course_table(html):
    soup = BeautifulSoup(html, "html.parser")
    results = []

    for table in soup.find_all("table"):
        rows = []
        for row in table.find_all("tr"):
            cells = row.find_all(["th", "td"])
            values = [clean_text(cell.get_text(" ", strip=True)) for cell in cells]
            if any(values):
                rows.append(values)

        if len(rows) < 2:
            continue

        headers = rows[0]
        header_text = " ".join(headers).lower()
        if not any(k in header_text for k in ("course", "รหัส", "วิชา", "section", "หน่วยกิต")):
            continue

        for row in rows[1:]:
            item = {}
            for i, value in enumerate(row):
                key = headers[i] if i < len(headers) else f"column_{i + 1}"
                item[key or f"column_{i + 1}"] = value
            if item:
                results.append(item)

    return results


def fetch_courses(acadyear, semester, coursecode="", coursename=""):
    url = build_url(acadyear, semester, coursecode, coursename)
    response = requests.get(
        url,
        timeout=15,
        headers={"User-Agent": "sut-course-api/1.0"},
    )
    response.raise_for_status()
    return parse_course_table(response.content)


@app.get("/api/course")
def get_courses(
    acadyear: str = Query(default="2569"),
    semester: str = Query(default="2"),
    coursecode: str = Query(default=""),
    coursename: str = Query(default=""),
):
    if not acadyear.isdigit():
        return JSONResponse(400, {"success": False, "error": "acadyear must be numeric"})
    if not semester.isdigit():
        return JSONResponse(400, {"success": False, "error": "semester must be numeric"})

    coursecode = coursecode.strip()
    coursename = coursename.strip()

    try:
        data = fetch_courses(acadyear, semester, coursecode, coursename)
    except requests.RequestException as exc:
        return JSONResponse(502, {
            "success": False,
            "error": "Failed to fetch SUT registrar",
            "detail": str(exc),
        })
    except Exception as exc:
        return JSONResponse(500, {
            "success": False,
            "error": "Internal server error",
            "detail": str(exc),
        })

    return {
        "success": True,
        "query": {
            "acadyear": acadyear,
            "semester": semester,
            "coursecode": coursecode,
            "coursename": coursename,
        },
        "data": data,
    }


@app.get("/api/health")
def health():
    return {"success": True, "service": "sut-course-api"}
