import json
import os
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 8000
DATA_DIR = "data"
OUTPUT_DIR = "output"


# Helper function to ensure data files and directory exist
def init_files():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    for filename, default_val in [
        ("customer.json", []),
        ("subscription.json", []),
    ]:
        filepath = os.path.join(DATA_DIR, filename)
        if not os.path.exists(filepath):
            with open(filepath, "w") as f:
                json.dump(default_val, f, indent=4)


class CustomRequestHandler(BaseHTTPRequestHandler):

    def _send_response(self, status_code, data, content_type="application/json"):
        self.send_response(status_code)
        self.send_header("Content-Type", content_type)
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def do_GET(self):
        # GET /api/v1/customers
        if self.path == "/api/v1/customers":
            filepath = os.path.join(DATA_DIR, "customer.json")
            try:
                with open(filepath, "r") as f:
                    customers = json.load(f)
                self._send_response(200, customers)
            except Exception as e:
                self._send_response(500, {"error": str(e)})

        # GET /api/v1/subscriptions
        elif self.path == "/api/v1/subscriptions":
            filepath = os.path.join(DATA_DIR, "subscription.json")
            try:
                with open(filepath, "r") as f:
                    subscriptions = json.load(f)
                self._send_response(200, subscriptions)
            except Exception as e:
                self._send_response(500, {"error": str(e)})

        else:
            self._send_response(404, {"error": "Not Found"})

    def do_POST(self):
        # POST /api/v1/bill
        if self.path == "/api/v1/bill":
            try:
                content_length = int(self.headers["Content-Length"])
                post_data = self.rfile.read(content_length)
                bill_data = json.loads(post_data.decode("utf-8"))

                # Validate expected payload keys
                required_keys = ["Id", "TotalCost", "NumberOfSubscriptions", "BillingEndDate"]
                # Adjust key checks if you prefer PascalCase/camelCase matching your json rules
                if not all(key in bill_data for key in required_keys):
                    self._send_response(
                        400,
                        {
                            "error": "Missing required fields. Expected: Id, TotalCost, NumberOfSubscriptions, BillingEndDate"
                        },
                    )
                    return

                filepath = os.path.join(OUTPUT_DIR, "monthly_bill.json")

                # Read existing bills, append new bill, and save back
                with open(filepath, "r+") as f:
                    bills = json.load(f)
                    bills.append(bill_data)
                    f.seek(0)
                    json.dump(bills, f, indent=4)
                    f.truncate()

                self._send_response(
                    201, {"message": "Bill successfully appended", "data": bill_data}
                )

            except Exception as e:
                # CATCH ALL ERRORS: Prints the full failure details to your terminal window
                print("\n" + "="*50)
                print(f"[SERVER ERROR] Exception encountered during POST request:")
                print(f"Error Type: {type(e).__name__}")
                print(f"Error Message: {str(e)}")
                print("-" * 50)
                traceback.print_exc()  # Prints the exact line number that broke
                print("="*50 + "\n")
                
                # Send the explicit error message back to the client/browser/curl
                error_response = {
                    "error": "Internal Server Error",
                    "exception_type": type(e).__name__,
                    "details": str(e)
                }
                self._send_response(500, error_response)
            except json.JSONDecodeError:
                self._send_response(400, {"error": "Invalid JSON payload"})

        else:
            self._send_response(404, {"error": "Not Found"})


def run():
    init_files()
    server_address = ("", PORT)
    httpd = HTTPServer(server_address, CustomRequestHandler)
    print(f"Starting server on port {PORT}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        httpd.server_close()


if __name__ == "__main__":
    run()

