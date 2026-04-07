import os
import ydb

YDB_ENDPOINT = os.getenv("YDB_ENDPOINT")
YDB_DATABASE = os.getenv("YDB_DATABASE")
PASSWORD = os.getenv("ADMIN_PASSWORD")

driver = ydb.Driver(endpoint=YDB_ENDPOINT, database=YDB_DATABASE)
driver.wait(timeout=5)
session = driver.table_client.session().create()

def handler(event, context):
    params = event.get("queryStringParameters") or {}

    if params.get("key") != PASSWORD:
        return {"statusCode": 403, "body": "Access denied"}

    result = session.transaction().execute(
        "SELECT user_id, service, budget, contact, segment FROM users;",
        commit_tx=True
    )

    rows = ""
    for u in result[0].rows:
        rows += f"<tr><td>{u.user_id}</td><td>{u.service}</td><td>{u.budget}</td><td>{u.contact}</td><td>{u.segment}</td></tr>"

    html = f"""
    <html>
    <body>
    <h1>Админка</h1>
    <table border="1">
    <tr><th>ID</th><th>Service</th><th>Budget</th><th>Contact</th><th>Segment</th></tr>
    {rows}
    </table>
    </body>
    </html>
    """

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "text/html"},
        "body": html
    }
