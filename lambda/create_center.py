"""
Lambda: create_center.py
Purpose: Register a new relief center in the system.
Trigger: POST /centers
Permissions needed: dynamodb:PutItem on ReliefCenters table, dynamodb:PutItem on Users table
"""

import json
import hashlib
import uuid
import boto3
from datetime import datetime, timezone
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
centers_table = dynamodb.Table('ReliefCenters')
users_table = dynamodb.Table('Users')
inventory_table = dynamodb.Table('Inventory')


def hash_password(password):
    return hashlib.sha256(str(password).encode('utf-8')).hexdigest()


def lambda_handler(event, context):
    """
    Creates a new relief center and registers the staff user.

    Expected JSON body:
    {
        "name": "Mumbai Relief Center",
        "location": "Andheri, Mumbai",
        "latitude": 19.1197,
        "longitude": 72.8464,
        "contactPhone": "+91-9876543210",
        "contactEmail": "mumbai@relief.org",
        "staffEmail": "staff@relief.org",
        "staffPassword": "securePass123"
    }
    """
    try:
        body = json.loads(event.get('body', '{}'))

        required = ['name', 'location', 'staffEmail', 'staffPassword']
        for field in required:
            if field not in body:
                return {
                    'statusCode': 400,
                    'headers': get_headers(),
                    'body': json.dumps({'error': f'Missing required field: {field}'})
                }

        center_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        center_item = {
            'centerId': center_id,
            'name': body['name'],
            'location': body['location'],
            'latitude': Decimal(str(body.get('latitude', 0))),
            'longitude': Decimal(str(body.get('longitude', 0))),
            'contactPhone': body.get('contactPhone', ''),
            'contactEmail': body.get('contactEmail', ''),
            'staffEmail': body['staffEmail'],
            'createdAt': now,
            'status': 'active'
        }
        centers_table.put_item(Item=center_item)

        user_item = {
            'email': body['staffEmail'],
            'passwordHash': hash_password(body['staffPassword']),
            'name': body.get('staffName', body['name'] + ' Staff'),
            'role': 'staff',
            'centerId': center_id,
            'createdAt': now
        }
        users_table.put_item(Item=user_item)

        resource_defaults = {
            'food': {'unit': 'kg', 'threshold': 100},
            'water': {'unit': 'liters', 'threshold': 200},
            'medical': {'unit': 'kits', 'threshold': 50},
            'shelter': {'unit': 'beds', 'threshold': 20}
        }

        for res_type, defaults in resource_defaults.items():
            inventory_item = {
                'centerId': center_id,
                'resourceType': res_type,
                'quantity': Decimal('0'),
                'unit': defaults['unit'],
                'threshold': Decimal(str(defaults['threshold'])),
                'lowStock': 'true',
                'lastUpdated': now
            }
            inventory_table.put_item(Item=inventory_item)

        return {
            'statusCode': 201,
            'headers': get_headers(),
            'body': json.dumps({
                'message': 'Relief center created successfully',
                'centerId': center_id
            }, default=str)
        }

    except Exception as e:
        print(f"Error creating center: {str(e)}")
        return {
            'statusCode': 500,
            'headers': get_headers(),
            'body': json.dumps({'error': 'Internal server error'})
        }


def get_headers():
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization'
    }
