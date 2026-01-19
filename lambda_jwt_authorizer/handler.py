import os
import jwt

JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")


def generate_policy(is_allowed, route_arn):
    return {"isAuthorized": is_allowed}


def lambda_handler(event, context):
    auth = event["headers"].get("authorization", "")
    parts = auth.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        token = parts[1]
        try:
            jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return generate_policy(True, event["routeArn"])
        except jwt.PyJWTError:
            pass
    return generate_policy(False, event["routeArn"])
