"""
Lambda: get_center.py
Purpose: Retrieve a single relief center's details by its ID.
Trigger: GET /centers/{centerId}
Permissions needed: dynamodb:GetItem on ReliefCenters table
"""

import json
import boto3

dynamodb = boto3.resource('dynamodb')
centers_table = dynamodb.Table('ReliefCenters')

def lambda_handler(event, context):
    """
    Returns the relief center record for the given centerId.
    Path parameter: centerId
    """
    try:
        center_id = event['pathParameters']['centerId']
        
        response = centers_table.get_item(
            Key={'centerId': center_id}
        )
        
        item = response.get('Item')
        if not item:
            return {
                'statusCode': 404,
                'headers': get_headers(),
                'body': json.dumps({'error': 'Center not found'})
            }
        
        return {
            'statusCode': 200,
            'headers': get_headers(),
            'body': json.dumps(item, default=str)
        }
        
    except KeyError:
        return {
            'statusCode': 400,
            'headers': get_headers(),
            'body': json.dumps({'error': 'Missing centerId path parameter'})
        }
    except Exception as e:
        print(f"Error getting center: {str(e)}")
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
