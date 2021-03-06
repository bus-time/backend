# Bus Time Backend API

## Database Information

### Request

```http
GET /databases/:schema
```

### Response

```http
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

## Database Content

### Request

```http
GET /databases/:schema/content
GET /databases/:schema/contents
```

### Response

```http
HTTP/1.0 200 OK
Content-Type: application/octet-stream
Content-Length: 37412
Content-Disposition: attachment; filename=bus-time.db
Content-Encoding: gzip
X-Content-SHA256: a1e02fa6e5416c12605f923b38d018f725016cd9781951b4deea3301f7ef7eb2
Vary: Accept-Encoding
```

## Database Publication

### Request

```http
POST /databases
X-Content-Signature: A7Mb/Unk54CuAWn1Vkds+RxsJWUFwH...
```

```json
{
  "version": "1554a6d60a0e5cf071e14376ce719eeb227c0a95",
  "schema_versions": [
    {
      "schema_version": 1,
      "content": "Zmlyc3QgdmVyc2lvbiBjb250ZW50..."
    },
    {
      "schema_version": 2,
      "content": "c2Vjb25kIHZlcnNpb24gY29udGVudA..."
    }
  ]
}
```

Here `content` is Base64-encoded database file content;
`X-Content-Signature` header is Base64-encoded signature of
request body (JSON text above, encoded in UTF-8); signature
is calculated according to RSASSA-PKCS1-v1_5 scheme
using SHA512 hash function.

### Response

```http
HTTP/1.0 201 Created
Content-Type: application/json
Content-Length: 59
```

```json
{
  "version": "1554a6d60a0e5cf071e14376ce719eeb227c0a95"
}
```
