# SUT Course API

Simple Vercel Serverless API for querying course information from the SUT Registrar system.

## Endpoint

`GET /api/course`

### Parameters

| Parameter | Required | Default |
|---|---|---|
| acadyear | No | 2569 |
| semester | No | 2 |
| coursecode | No* | - |
| coursename | No* | - |

`coursecode` or `coursename` must be provided.

Examples:

`/api/course?coursecode=eng39*`

`/api/course?acadyear=2569&semester=2&coursecode=ENG39+2001`

`/api/course?coursename=Computer+Programming`

Spaces are converted to `+` when building the SUT Registrar URL. The `*` wildcard in coursecode is preserved.

## Local development

Install dependencies:

```bash
pip install -r requirements.txt
```

Deploy with Vercel:

```bash
vercel
```
