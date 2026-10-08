import re

import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

BASE_URL = "https://reg2.sut.ac.th/registrar/class_info_1.asp"

app = FastAPI(title="SUT Course API", version="0.2.0")


def clean_text(text):
    """ทำความสะอาด whitespace"""
    return re.sub(r"\s+", " ", text).strip()


def extract_course_code_version(text):
    """
    Supported course code formats:

    ENGxx xxxx
    Example:
        ENG39 2001 - 1
        -> code = ENG39 2001
        -> version = 1

    xxxxxx
    Example:
        539100 - 1
        -> code = 539100
        -> version = 1
    """
    text = clean_text(text)

    match = re.search(
        r"((?:[A-Z]{3}\d{2}\s\d{4})|(?:\d{6}))\s*-\s*(\d+)",
        text,
    )

    if not match:
        return "", ""

    return match.group(1), match.group(2)


def extract_teachers(td):
    teachers = []

    for li in td.find_all("li"):
        direct_text = "".join(
            str(node) for node in li.contents if getattr(node, "name", None) is None
        )
        direct_text = clean_text(direct_text)

        if direct_text:
            teachers.append(direct_text)

    return teachers


def extract_course_name(text):
    """
    Extract course name from the Registrar course-name cell.

    The course name is normally followed by additional information
    in parentheses. If no parenthesis is present, use the first Thai
    character as the boundary before teacher/other Thai text.
    """
    text = clean_text(text)

    # Method 1: parenthesis marks the end of the course name.
    match = re.search(r"\s*\(", text)
    if match:
        return text[: match.start()].strip()

    # Method 2: if there is no parenthesis, stop at the first Thai character.
    match = re.search(r"[ก-๙]", text)
    if match:
        return text[: match.start()].strip()

    return text


def extract_additional_info(td):
    text = clean_text(td.get_text(" ", strip=True))
    match = re.search(r"\(.*?\)", text)

    return clean_text(match.group(0)) if match else ""


def extract_schedule(td):
    schedule = []

    for bold in td.find_all("b"):
        day = clean_text(bold.get_text(" ", strip=True))
        if not day:
            continue

        parts = []
        node = bold.next_sibling

        while node is not None:
            if getattr(node, "name", None) == "br":
                break

            if hasattr(node, "get_text"):
                value = node.get_text(" ", strip=True)
            else:
                value = str(node)

            value = clean_text(value)
            if value:
                parts.append(value)

            node = node.next_sibling

        text = clean_text(" ".join(parts))

        match = re.search(
            r"(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})\s+(.+?)(?=\s+[A-Za-z]{1,3}\s+\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2}|$)",
            text,
        )

        if match:
            schedule.append(
                {
                    "day": day,
                    "start_time": match.group(1),
                    "end_time": match.group(2),
                    "room": clean_text(match.group(3)),
                }
            )

    return schedule


def parse_credits(td):
    text = clean_text(td.get_text(" ", strip=True))

    numbers = re.findall(r"\d+(?:\.\d+)?", text)
    if not numbers:
        return None, ""

    credits = int(numbers[0]) if numbers[0].isdigit() else float(numbers[0])
    credit_detail = ""

    match = re.search(r"(\d+\s*-\s*\d+\s*-\s*\d+)", text)
    if match:
        credit_detail = re.sub(r"\s+", "", match.group(1))

    return credits, credit_detail


def parse_courses(html):
    """
    Parse SUT Registrar course rows using the original course-specific
    parser structure rather than a generic table-to-dict parser.
    """
    soup = BeautifulSoup(html, "html.parser")
    results = []

    for tr in soup.find_all("tr"):
        tds = tr.find_all("td", recursive=False)

        if len(tds) < 12:
            continue

        if not tds[1].find("a", href=re.compile(r"class_info_2\.asp", re.I)):
            continue

        course_code, version = extract_course_code_version(
            tds[1].get_text(" ", strip=True)
        )

        if not course_code:
            continue

        course_name = extract_course_name(
            tds[2].get_text(" ", strip=True)
        )
        teachers = extract_teachers(tds[2])
        additional_info = extract_additional_info(tds[2])

        credits, credit_detail = parse_credits(tds[3])

        language = clean_text(tds[4].get_text(" ", strip=True))
        level = clean_text(tds[5].get_text(" ", strip=True))
        schedule = extract_schedule(tds[6])

        group = clean_text(tds[7].get_text(" ", strip=True))
        capacity = clean_text(tds[8].get_text(" ", strip=True))
        enrolled = clean_text(tds[9].get_text(" ", strip=True))
        remaining = clean_text(tds[10].get_text(" ", strip=True))
        status = clean_text(tds[11].get_text(" ", strip=True))

        results.append(
            {
                "course_code": course_code,
                "version": version,
                "course_name": course_name,
                "teachers": teachers,
                "credits": credits,
                "credit_detail": credit_detail,
                "language": language,
                "level": level,
                "schedule": schedule,
                "group": group,
                "capacity": capacity,
                "enrolled": enrolled,
                "remaining": remaining,
                "status": status,
                "additional_info": additional_info,
            }
        )

    return results


def build_url(acadyear, semester, coursecode="", coursename=""):
    coursecode = coursecode.replace(" ", "+")
    coursename = coursename.replace(" ", "+")

    return (
        f"{BASE_URL}?coursestatus=O00"
        f"&facultyid=all&maxrow=50&CAMPUSID=&LEVELID=&cmd=2"
        f"&acadyear={acadyear}&semester={semester}"
        f"&coursecode={coursecode}&coursename={coursename}"
    )


def decode_html(content):
    """
    SUT Registrar has inconsistent/incorrect charset declarations.
    Prefer UTF-8 when the raw response is valid UTF-8, then fall back
    to the Thai Windows-874 encoding used by older pages.
    """
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return content.decode("cp874")


def fetch_courses(acadyear, semester, coursecode="", coursename=""):
    url = build_url(acadyear, semester, coursecode, coursename)

    response = requests.get(
        url,
        timeout=15,
        headers={"User-Agent": "sut-course-api/1.0"},
    )
    response.raise_for_status()

    html = decode_html(response.content)
    return parse_courses(html)


@app.get("/api/course")
def get_courses(
    acadyear: str = Query(default="2569"),
    semester: str = Query(default="2"),
    coursecode: str = Query(default=""),
    coursename: str = Query(default=""),
):
    if not acadyear.isdigit():
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "acadyear must be numeric"},
        )

    if not semester.isdigit():
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "semester must be numeric"},
        )

    coursecode = coursecode.strip()
    coursename = coursename.strip()

    try:
        data = fetch_courses(acadyear, semester, coursecode, coursename)
    except requests.RequestException as exc:
        return JSONResponse(
            status_code=502,
            content={
                "success": False,
                "error": "Failed to fetch SUT registrar",
                "detail": str(exc),
            },
        )
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Internal server error",
                "detail": str(exc),
            },
        )

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
