# handlers/register_access_user.py
import json
from services.access_users_service import AccessUserService
from repositories.access_user_repo import AccessUserRepository

svc = AccessUserService(AccessUserRepository())


def lambda_handler(event, context):
    body = event.get("body", event)
    body = json.loads(body) if isinstance(body, str) else body
    try:
        result = svc.create_user(body)
        return {"statusCode": 201, "body": json.dumps(result)}
    except LookupError as e:
        return {"statusCode": 409, "body": json.dumps({"error": str(e)})}
    except ValueError as e:
        return {"statusCode": 400, "body": json.dumps({"error": str(e)})}
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
