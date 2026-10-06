"""
Lambda: get_inventory.py
Purpose: Get full inventory for a specific relief center.
Trigger: GET /centers/{centerId}/inventory
Permissions needed: dynamodb:Query on Inventory table (using partition key centerId)
"""

import json
import boto3

dynamodb = boto3.resource('dynamodb')
inventory_table = dynamodb.Table('Inventory')

def lambda_handler(event, context):
    """
    Returns all resource types and quantities for a given center.
    Path parameter: centerId
    """
    try:
        center_id = event['pathParameters']['centerId']
        
        # Query uses the partition key — retrieves all resource types for this center
        response = inventory_table.query(
            KeyConditionExpression='centerId = :cid',
            ExpressionAttributeValues={':cid': center_id}
        )
        
        items = response.get('Items', [])
        
        return {
            'statusCode': 200,
            'headers': get_headers(),
            'body': json.dumps({
                'centerId': center_id,
                'inventory': items,
                'count': len(items)
            }, default=str)
        }
        
    except KeyError:
        return {
            'statusCode': 400,
            'headers': get_headers(),
            'body': json.dumps({'error': 'Missing centerId path parameter'})
        }
    except Exception as e:
        print(f"Error getting inventory: {str(e)}")
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
