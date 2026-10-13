import json
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

DATA_FILE = Path(__file__).resolve().parent / 'data' / 'subscriptions.json'
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
