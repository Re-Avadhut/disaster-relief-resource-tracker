"""
Lambda: login_user.py
Purpose: Authenticate a user and return their role/center info.
Trigger: POST /auth/login
Permissions needed: dynamodb:GetItem on Users table, dynamodb:GetItem on ReliefCenters table
"""

import json
import hashlib
import uuid
import boto3

dynamodb = boto3.resource('dynamodb')
users_table = dynamodb.Table('Users')
centers_table = dynamodb.Table('ReliefCenters')


def hash_password(password):
    return hashlib.sha256(str(password).encode('utf-8')).hexdigest()


def lambda_handler(event, context):
    """
    Simple login: checks email + password against Users table.

    Expected JSON body:
    {
        "email": "staff@relief.org",
        "password": "securePass123"
    }

    Returns:
    {
        "token": "mock-jwt-token",
        "user": { "email": "...", "role": "staff", "name": "...", "centerId": "..." }
    }
    """
    try:
        body = json.loads(event.get('body', '{}'))

        email = body.get('email')
        password = body.get('password')

        if not email or not password:
            return {
                'statusCode': 400,
                'headers': get_headers(),
                'body': json.dumps({'error': 'Email and password are required'})
            }

        response = users_table.get_item(Key={'email': email})
        user = response.get('Item')

        if not user:
            return {
                'statusCode': 401,
                'headers': get_headers(),
                'body': json.dumps({'error': 'Invalid email or password'})
            }

        stored_hash = user.get('passwordHash')
        input_hash = hash_password(password)

        if stored_hash not in (password, input_hash):
            return {
                'statusCode': 401,
                'headers': get_headers(),
                'body': json.dumps({'error': 'Invalid email or password'})
            }

        center_info = None
        if user.get('role') == 'staff' and user.get('centerId'):
            center_resp = centers_table.get_item(
                Key={'centerId': user['centerId']})
            center_info = center_resp.get('Item')

        token = f"mock-token-{uuid.uuid4()}"
        session_user = {
            'email': user['email'],
            'name': user.get('name', ''),
            'role': user.get('role', 'staff'),
            'centerId': user.get('centerId'),
            'center': center_info,
            'token': token
        }

        return {
            'statusCode': 200,
            'headers': get_headers(),
            'body': json.dumps({
                'message': 'Login successful',
                'token': token,
                'user': session_user
            }, default=str)
        }

    except Exception as e:
        print(f"Error during login: {str(e)}")
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
