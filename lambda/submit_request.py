"""
Lambda: submit_request.py
Purpose: Submit a new help request from anyone (public form).
Trigger: POST /requests
Permissions needed: dynamodb:PutItem on HelpRequests table
"""

import json
import uuid
import boto3
from datetime import datetime, timezone

dynamodb = boto3.resource('dynamodb')
requests_table = dynamodb.Table('HelpRequests')

def lambda_handler(event, context):
    """
    Creates a new help request. Anyone can call this endpoint.
    
    Expected JSON body:
    {
        "name": "Rajesh Kumar",
        "location": "Flood-affected area, Patna",
        "needType": "food",
        "urgency": 1,
        "description": "Family of 6, no food for 2 days",
        "contactPhone": "+91-9876543210"
    }
    """
    try:
        body = json.loads(event.get('body', '{}'))
        
        # Validate required fields
        required = ['name', 'location', 'needType', 'urgency', 'description']
        for field in required:
            if field not in body:
                return {
                    'statusCode': 400,
                    'headers': get_headers(),
                    'body': json.dumps({'error': f'Missing required field: {field}'})
                }
        
        # Validate urgency range
        urgency = int(body['urgency'])
        if urgency not in [1, 2, 3, 4]:
            return {
                'statusCode': 400,
                'headers': get_headers(),
                'body': json.dumps({'error': 'Urgency must be 1 (critical), 2 (high), 3 (medium), or 4 (low)'})
            }
        
        # Map urgency number to label
        urgency_labels = {1: 'critical', 2: 'high', 3: 'medium', 4: 'low'}
        
        request_item = {
            'requestId': str(uuid.uuid4()),
            'name': body['name'],
            'location': body['location'],
            'needType': body['needType'],
            'urgency': urgency,
            'urgencyLabel': urgency_labels[urgency],
            'description': body['description'],
            'contactPhone': body.get('contactPhone', ''),
            'status': 'pending',
            'assignedCenterId': None,
            'createdAt': datetime.now(timezone.utc).isoformat()
        }
        
        requests_table.put_item(Item=request_item)
        
        return {
            'statusCode': 201,
            'headers': get_headers(),
            'body': json.dumps({
                'message': 'Help request submitted successfully',
                'requestId': request_item['requestId'],
                'status': 'pending'
            })
        }
        
    except ValueError:
        return {
            'statusCode': 400,
            'headers': get_headers(),
            'body': json.dumps({'error': 'Invalid urgency value'})
        }
    except Exception as e:
        print(f"Error submitting request: {str(e)}")
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
