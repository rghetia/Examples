import json
import os
import tempfile
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

DATA_FILE = Path(__file__).resolve().parent / 'data' / 'subscriptions.json'
REPORT_FILE = Path(__file__).resolve().parent / 'data' / 'received_customer_report.json'
MAX_BODY_BYTES = 1024 * 1024
HOST = '0.0.0.0'
PORT = 8000


def load_subscriptions():
    with DATA_FILE.open(encoding='utf-8') as file:
        subscriptions = json.load(file)
    if isinstance(subscriptions, dict):
        subscriptions = [subscriptions]
    if not isinstance(subscriptions, list):
        raise ValueError('Subscription JSON must be an object or an array')
    ids = []
    for item in subscriptions:
        if not isinstance(item, dict) or not isinstance(item.get('id'), str) or not item['id']:
            raise ValueError('Each subscription must have a nonempty string id')
        ids.append(item['id'])
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate subscription IDs')
    return sorted(subscriptions, key=lambda item: item['id'])


def validate_reports(reports):
    if not isinstance(reports, list):
        raise ValueError('Request body must be a JSON array')
    required = {'customer_id', 'report_date', 'active_subscriptions', 'total_cost', 'currency'}
    for i, report in enumerate(reports):
        if not isinstance(report, dict) or set(report) != required:
            raise ValueError(f'Report {i} must contain exactly: {", ".join(sorted(required))}')
        if not isinstance(report['customer_id'], str) or not report['customer_id'].strip():
            raise ValueError(f'Report {i}: customer_id must be a nonempty string')
        if not isinstance(report['report_date'], str):
            raise ValueError(f'Report {i}: report_date must be a string')
        try:
            parsed = datetime.strptime(report['report_date'], '%Y-%m-%d %H:%M:%S %z')
            if parsed.utcoffset() is None:
                raise ValueError('Timezone required')
        except ValueError:
            raise ValueError(f'Report {i}: invalid report_date') from None
        subs = report['active_subscriptions']
        if not isinstance(subs, list) or any(not isinstance(x, str) or not x for x in subs):
            raise ValueError(f'Report {i}: active_subscriptions must be a list of nonempty strings')
        if type(report['total_cost']) is not int or report['total_cost'] < 0:
            raise ValueError(f'Report {i}: total_cost must be a nonnegative integer')
        if not isinstance(report['currency'], str) or len(report['currency']) != 3 or not report['currency'].isalpha():
            raise ValueError(f'Report {i}: currency must be a three-letter code')


def append_reports(reports):
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    if REPORT_FILE.exists():
        with REPORT_FILE.open(encoding='utf-8') as f:
            existing = json.load(f)
        if not isinstance(existing, list):
            raise ValueError('Existing report file must contain a JSON array')
    else:
        existing = []
    # Atomic replacement prevents truncation if writing fails.
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=REPORT_FILE.parent,
                                         prefix='.customer_reports_', suffix='.tmp', delete=False) as f:
            temp_path = Path(f.name)
            json.dump(existing + reports, f, indent=2)
            f.write('\n')
        os.replace(temp_path, REPORT_FILE)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


SUBSCRIPTIONS = load_subscriptions()
INDEX_BY_ID = {item['id']: i for i, item in enumerate(SUBSCRIPTIONS)}


class SubscriptionHandler(BaseHTTPRequestHandler):
    last_request_time = 0.0

    def send_json(self, status, payload, headers=None):
        body = json.dumps(payload).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        path = urlsplit(self.path).path
        if path == '/api/v1/subscription':
            return self.send_json(405, {'error': 'Method not allowed'}, {'Allow': 'GET'})
        if path != '/api/v1/customer_report':
            return self.send_json(404, {'error': 'Not found'})

        try:
            if urlsplit(self.path).query:
                raise ValueError('Query parameters are not supported')
            if self.headers.get('Content-Type', '').split(';')[0].strip().lower() != 'application/json':
                return self.send_json(415, {'error': 'Content-Type must be application/json'})
            raw_length = self.headers.get('Content-Length')
            if raw_length is None or not raw_length.isascii() or not raw_length.isdecimal():
                raise ValueError('Valid Content-Length is required')
            length = int(raw_length)
            if length == 0:
                raise ValueError('Request body must not be empty')
            if length > MAX_BODY_BYTES:
                return self.send_json(413, {'error': 'Request body too large'})
            reports = json.loads(self.rfile.read(length))
            validate_reports(reports)
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            print(f'Invalid customer report: {exc}', flush=True)
            return self.send_json(400, {'error': str(exc)})

        try:
            append_reports(reports)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f'Failed to save customer report: {exc}', flush=True)
            return self.send_json(500, {'error': 'Unable to save customer reports'})
        return self.send_json(201, {'message': 'Reports saved', 'count': len(reports)})

    def do_GET(self):
        url = urlsplit(self.path)
        if url.path != '/api/v1/subscriptions':
            return self.send_json(404, {'error': 'Not found'})

        # One request per second across this HTTPServer process.
        now = time.monotonic()
        if now - SubscriptionHandler.last_request_time < 1.0:
            return self.send_json(429, {
                'error': 'Too many requests',
                'message': 'Only 1 request per second is allowed'
            }, {'Retry-After': '1'})
        SubscriptionHandler.last_request_time = now

        try:
            params = parse_qs(url.query, keep_blank_values=True)
            for key, values in params.items():
                if key not in {'start_after', 'limit'}:
                    raise ValueError(f'Unknown parameter: {key}')
                if len(values) != 1:
                    raise ValueError(f'Duplicate parameter: {key}')

            start_after = params.get('start_after', [''])[0]
            raw_limit = params.get('limit', [None])[0]
            limit = None
            if raw_limit is not None:
                if not raw_limit.isascii() or not raw_limit.isdecimal():
                    raise ValueError('limit must be a positive integer')
                limit = int(raw_limit)
                if limit <= 0:
                    raise ValueError('limit must be greater than 0')

            start_index = 0
            if start_after:
                if start_after not in INDEX_BY_ID:
                    raise ValueError(f'Invalid start_after: {start_after}')
                start_index = INDEX_BY_ID[start_after] + 1

            end_index = len(SUBSCRIPTIONS) if limit is None else start_index + limit
            result = SUBSCRIPTIONS[start_index:end_index]
            return self.send_json(200, {
                'data': result,
                'count': len(result),
                'has_more': start_index + len(result) < len(SUBSCRIPTIONS),
                'next_cursor': result[-1]['id'] if result else None
            })
        except ValueError as exc:
            print(f'Invalid parameters: {exc}', flush=True)
            return self.send_json(400, {'error': str(exc)})


if __name__ == '__main__':
    server = HTTPServer((HOST, PORT), SubscriptionHandler)
    print(f'Server listening at http://localhost:{PORT}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
