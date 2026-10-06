"""
Lambda: list_requests.py
Purpose: List help requests with optional filtering and sorting.
Trigger: GET /requests
Permissions needed: dynamodb:Scan on HelpRequests table, dynamodb:Query on StatusUrgency-index
"""

import json
import boto3

dynamodb = boto3.resource('dynamodb')
requests_table = dynamodb.Table('HelpRequests')


def lambda_handler(event, context):
    """
    Returns help requests. Supports:
      ?status=pending          — filter by status
      ?sort=urgency           — sort by urgency (uses GSI)
      ?location=Mumbai        — filter by location
    """
    try:
        params = event.get('queryStringParameters', {}) or {}
        status = params.get('status')
        sort_by = params.get('sort')
        location = params.get('location')

        if status:
            response = requests_table.query(
                IndexName='StatusUrgency-index',
                KeyConditionExpression='#s = :status',
                ExpressionAttributeNames={'#s': 'status'},
                ExpressionAttributeValues={':status': status}
            )
            items = response.get('Items', [])
        else:
            response = requests_table.scan()
            items = response.get('Items', [])

        if sort_by == 'urgency':
            items = sorted(items, key=lambda x: x.get('urgency', 4))

        if location:
            items = [i for i in items if location.lower() in i.get(
                'location', '').lower()]

        return {
            'statusCode': 200,
            'headers': get_headers(),
            'body': json.dumps({
                'requests': items,
                'count': len(items)
            }, default=str)
        }

    except Exception as e:
        print(f"Error listing requests: {str(e)}")
        return {
            'statusCode': 500,
            'headers': get_headers(),
            'body': json.dumps({'error': 'Internal server error'})
        }


def get_headers():
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization'
    }
