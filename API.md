# Bus Time Backend API

## Database Information

### Request

```
GET /databases/:schema
```

### Response

```
HTTP/1.0 200 OK
Content-Type: application/json
Content-Length: 82
```

```json
{
  "schema_version": 2,
  "version": "e6695e5508d5dd7ef6298d57c07c24da7b1a2152"
}
```

## Database Contents

### Request

```
GET /databases/:schema/contents
```

### Response

```
HTTP/1.0 200 OK
Content-Type: application/octet-stream
Content-Length: 37412
Content-Disposition: attachment; filename=bus-time.db
Content-Encoding: gzip
X-Content-SHA256: a1e02fa6e5416c12605f923b38d018f725016cd9781951b4deea3301f7ef7eb2
Vary: Accept-Encoding
```
