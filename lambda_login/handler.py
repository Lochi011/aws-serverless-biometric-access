import json
import os
import bcrypt
import jwt
import psycopg2
from datetime import datetime, timedelta


def lambda_handler(event, context):
    try:
        # 1. Extract credentials from the request body.
        # Se espera que el body esté en formato JSON (como un string en event['body'])
        body = json.loads(event.get('body', '{}'))
        email = body.get('email')
        password = body.get('password')

        # Basic input validation.
        if not email or not password:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Email and password are required'})
            }

        # 2. Database connection configuration.
        db_config = {
            'host': os.environ.get('DB_HOST'),
            'dbname': os.environ.get('DB_NAME'),
            'user': os.environ.get('DB_USER'),
            'password': os.environ.get('DB_PASS'),
            'port': os.environ.get('DB_PORT')
        }

        missing_env_vars = [k for k, v in db_config.items() if v is None]
        if missing_env_vars or os.environ.get('JWT_SECRET') is None:
            missing = ', '.join(
                missing_env_vars + (['JWT_SECRET'] if os.environ.get('JWT_SECRET') is None else []))
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': f'Missing environment variables: {missing}'})
            }

        # 3. Connect to the database.
        conn = None
        try:
            conn = psycopg2.connect(**db_config)
            cursor = conn.cursor()

            # 4. Search for the user in the web_users table by email.
            query = "SELECT id, email, first_name, last_name, password_hash, role FROM web_users WHERE email = %s"
            cursor.execute(query, (email,))
            user_record = cursor.fetchone()

            if not user_record:
                return {
                    'statusCode': 401,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({'error': 'Invalid credentials'})
                }

            user_id, user_email, user_first_name, user_last_name, password_hash, user_role = user_record

            # 5. Verify the password using bcrypt.
            if not bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8')):
                return {
                    'statusCode': 401,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({'error': 'Invalid credentials'})
                }

            # 6. Generate a JWT token for the authenticated user.
            jwt_secret = os.environ.get('JWT_SECRET')
            payload = {
                'user_id': user_id,
                'email': user_email,
                'name': user_first_name + ' ' + user_last_name,
                'role': user_role,
                'exp': datetime.utcnow() + timedelta(days=1)  # Token expires in 1 day
            }

            # Encode the JWT token using the secret key.

            token = jwt.encode(payload, jwt_secret, algorithm='HS256')

            # 7. Return a successful response including the token and user details.
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'message': 'Login successful',
                    'token': token,
                    'user': {
                        'id': user_id,
                        'email': user_email,
                        'name': user_first_name + ' ' + user_last_name,
                    }
                })
            }

        finally:
            if conn is not None:
                cursor.close()
                conn.close()

    except psycopg2.Error as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': f'Database error: {str(e)}'})
        }
    except jwt.PyJWTError as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': f'Error generating token: {str(e)}'})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': f'Internal error: {str(e)}'})
        }
