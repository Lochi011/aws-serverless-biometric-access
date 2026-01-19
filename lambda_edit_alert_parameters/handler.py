import json
import psycopg2
from db import get_db_connection

def lambda_handler(event, context):
    try:
        body = json.loads(event['body'])
        max_attempts = body.get('max_denied_attempts')
        window_seconds = body.get('window_seconds')

        if max_attempts is None or window_seconds is None:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Both max_denied_attempts and window_seconds are required.'})
            }

        conn = get_db_connection()
        cur = conn.cursor()

        update_query = """
            UPDATE configurations
            SET value = %s
            WHERE name_config = %s
        """

        cur.execute(update_query, (str(max_attempts), 'max_denied_attempts'))
        cur.execute(update_query, (str(window_seconds), 'window_seconds'))

        conn.commit()
        cur.close()
        conn.close()

        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Alert parameters updated successfully.'})
        }

    except (psycopg2.Error, Exception) as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
