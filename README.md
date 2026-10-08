# SUT Course API

Simple Vercel Serverless API for querying course information from the SUT Registrar system.

This API is designed to provide structured course data for applications such as course search pages, curriculum tools, timetable views, and other frontend applications.

## API

Production base URL:

`https://sut-course-api.vercel.app`

Main endpoint:

`GET /api/course`

Health check:

`GET /api/health`

Full API specification:

`openapi.yaml`

---

## Course endpoint

### `GET /api/course`

Queries course information from the SUT Registrar system.

### Query parameters

| Parameter | Type | Required | Default | Description |
|---|---|---:|---|---|
| `acadyear` | string | No | `2569` | Academic year. Must contain only digits. |
| `semester` | string | No | `2` | Semester. Must contain only digits. |
| `coursecode` | string | No | empty | Course code search text. Spaces are converted to `+` when querying the SUT Registrar. The `*` wildcard is preserved. |
| `coursename` | string | No | empty | Course name search text. Spaces are converted to `+` when querying the SUT Registrar. |

The current API implementation accepts the parameters independently. Supplying both `coursecode` and `coursename` is also allowed.

### Examples

Search by course code:

`GET https://sut-course-api.vercel.app/api/course?coursecode=ENG392001`

Search by course code with academic year and semester:

`GET https://sut-course-api.vercel.app/api/course?acadyear=2569&semester=2&coursecode=ENG39%202001`

Search using the course-code wildcard:

`GET https://sut-course-api.vercel.app/api/course?coursecode=eng39*`

Search by course name:

`GET https://sut-course-api.vercel.app/api/course?coursename=Computer%20Programming`

---

## Success response

A successful request returns:

```json
{
  "success": true,
  "query": {
    "acadyear": "2569",
    "semester": "2",
    "coursecode": "ENG392001",
    "coursename": ""
  },
  "data": [
    {
      "course_code": "ENG39 2001",
      "version": "1",
      "course_name": "Example Course",
      "teachers": [
        "Example Teacher"
      ],
      "credits": 3,
      "credit_detail": "3-0-6",
      "language": "English",
      "level": "Bachelor",
      "schedule": [
        {
          "day": "We",
          "start_time": "13:00",
          "end_time": "15:00",
          "room": "B6503-A"
        }
      ],
      "group": "1",
      "capacity": "40",
      "enrolled": "35",
      "remaining": "5",
      "status": "O",
      "additional_info": ""
    }
  ]
}
```

The example above describes the response structure. Course values depend on the data currently available from the SUT Registrar system.

### Response fields

#### Top-level

| Field | Type | Description |
|---|---|---|
| `success` | boolean | `true` for a successful request. |
| `query` | object | The normalized query values received by the API. |
| `data` | array | Array of parsed course records. |

#### `query`

| Field | Type | Description |
|---|---|---|
| `acadyear` | string | Academic year used for the query. |
| `semester` | string | Semester used for the query. |
| `coursecode` | string | Course-code search text after trimming whitespace. |
| `coursename` | string | Course-name search text after trimming whitespace. |

#### Course object

| Field | Type | Description |
|---|---|---|
| `course_code` | string | Course code, e.g. `ENG39 2001`. |
| `version` | string | Course version number. |
| `course_name` | string | Course name. |
| `teachers` | string[] | List of instructors parsed from the registrar page. |
| `credits` | number \| null | Course credit value. |
| `credit_detail` | string | Detailed credit structure, e.g. `3-0-6`. |
| `language` | string | Course language. |
| `level` | string | Course level. |
| `schedule` | object[] | Class schedule entries. |
| `group` | string | Course section/group. |
| `capacity` | string | Maximum capacity. |
| `enrolled` | string | Number of enrolled students. |
| `remaining` | string | Remaining seats. |
| `status` | string | Registration status shown by the registrar. |
| `additional_info` | string | Additional information parsed from the course name/details. |

#### Schedule object

Each item in `schedule` represents one class period.

| Field | Type | Description |
|---|---|---|
| `day` | string | Day abbreviation from the registrar system, e.g. `We`. |
| `start_time` | string | Start time in `HH:MM` format. |
| `end_time` | string | End time in `HH:MM` format. |
| `room` | string | Room for this specific schedule period. It must not include the room/time information belonging to the next schedule period. |

For example, a parsed schedule should look like:

```json
{
  "day": "We",
  "start_time": "13:00",
  "end_time": "15:00",
  "room": "B6503-A"
}
```

---

## Error responses

### 400 — Invalid query

Returned when `acadyear` or `semester` contains a non-numeric value.

```json
{
  "success": false,
  "error": "acadyear must be numeric"
}
```

or:

```json
{
  "success": false,
  "error": "semester must be numeric"
}
```

### 502 — SUT Registrar request failed

Returned when the API cannot successfully fetch the SUT Registrar page.

```json
{
  "success": false,
  "error": "Failed to fetch SUT registrar",
  "detail": "..."
}
```

### 500 — Internal server error

Returned when an unexpected server-side error occurs.

```json
{
  "success": false,
  "error": "Internal server error",
  "detail": "..."
}
```

---

## Health check

### `GET /api/health`

Returns a simple response indicating that the API service is running.

```json
{
  "success": true,
  "service": "sut-course-api"
}
```

---

## Important frontend integration notes

When building a frontend against this API:

1. Use the `data` array as the list of courses.
2. A course can contain multiple `schedule` entries.
3. Do not assume every course has at least one teacher or schedule entry.
4. `credits` can be `null`.
5. Most numeric-looking fields such as `capacity`, `enrolled`, and `remaining` are currently returned as strings.
6. `course_code` and `version` are currently returned as strings.
7. Treat `schedule` as structured data rather than parsing the room/time text on the frontend.
8. The frontend should handle empty `data` as a valid search result with no matching courses.
9. The frontend should display a useful error state for HTTP 400, 500, and 502 responses.

The frontend should use the API response as-is rather than attempting to scrape the SUT Registrar website directly.

---

## Local development

Install dependencies:

```bash
pip install -r requirements.txt
```

Deploy with Vercel:

```bash
vercel
```
