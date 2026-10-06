"""
Lambda: list_centers.py
Purpose: List all relief centers. Used by admin dashboard.
Trigger: GET /centers
Permissions needed: dynamodb:Scan on ReliefCenters table
"""

import json
import boto3

dynamodb = boto3.resource('dynamodb')
centers_table = dynamodb.Table('ReliefCenters')


def lambda_handler(event, context):
    """
    Returns all relief centers.
    Optional query parameter: ?status=active to filter by status
    """
    try:
        query_params = event.get('queryStringParameters') or {}
        status_filter = query_params.get('status')

        if status_filter:
            # Use Scan with FilterExpression when filtering is needed
            response = centers_table.scan(
                FilterExpression='#s = :status',
                ExpressionAttributeNames={'#s': 'status'},
                ExpressionAttributeValues={':status': status_filter}
            )
        else:
            # Full scan returns all centers (fine for small datasets)
            response = centers_table.scan()

        items = response.get('Items', [])

        return {
            'statusCode': 200,
            'headers': get_headers(),
            'body': json.dumps({
                'centers': items,
                'count': len(items)
            }, default=str)
        }

    except Exception as e:
        print(f"Error listing centers: {str(e)}")
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
