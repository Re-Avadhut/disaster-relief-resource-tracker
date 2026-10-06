"""
Lambda: update_inventory.py
Purpose: Update resource quantities for a relief center's inventory.
Trigger: PUT /centers/{centerId}/inventory
Permissions needed: dynamodb:UpdateItem on Inventory table
"""

import json
import boto3
from datetime import datetime, timezone
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
inventory_table = dynamodb.Table('Inventory')

def lambda_handler(event, context):
    """
    Updates a specific resource type in a center's inventory.
    
    Path parameter: centerId
    Expected JSON body:
    {
        "resourceType": "food",
        "quantity": 150,
        "unit": "kg",
        "threshold": 100
    }
    """
    try:
        center_id = event['pathParameters']['centerId']
        body = json.loads(event.get('body', '{}'))
        
        resource_type = body.get('resourceType')
        if not resource_type:
            return {
                'statusCode': 400,
                'headers': get_headers(),
                'body': json.dumps({'error': 'resourceType is required'})
            }
        
        now = datetime.now(timezone.utc).isoformat()
        quantity = Decimal(str(body.get('quantity', 0)))
        threshold = Decimal(str(body.get('threshold', 100)))
        
        # Determine if stock is below threshold
        low_stock = 'true' if quantity < threshold else 'false'
        
        # Build update expression dynamically — only update fields that are provided
        update_parts = []
        expr_values = {}
        expr_names = {}
        
        if 'quantity' in body:
            update_parts.append('#q = :qty')
            expr_values[':qty'] = quantity
            expr_names['#q'] = 'quantity'
        
        if 'unit' in body:
            update_parts.append('#u = :unit')
            expr_values[':unit'] = body['unit']
            expr_names['#u'] = 'unit'
        
        if 'threshold' in body:
            update_parts.append('#t = :thresh')
            expr_values[':thresh'] = threshold
            expr_names['#t'] = 'threshold'
        
        # Always update lowStock flag and timestamp
        update_parts.append('#ls = :lowstock')
        expr_values[':lowstock'] = low_stock
        expr_names['#ls'] = 'lowStock'
        
        update_parts.append('#lu = :updated')
        expr_values[':updated'] = now
        expr_names['#lu'] = 'lastUpdated'
        
        response = inventory_table.update_item(
            Key={
                'centerId': center_id,
                'resourceType': resource_type
            },
            UpdateExpression='SET ' + ', '.join(update_parts),
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
            ReturnValues='ALL_NEW'
        )
        
        return {
            'statusCode': 200,
            'headers': get_headers(),
            'body': json.dumps({
                'message': 'Inventory updated',
                'inventory': response['Attributes']
            }, default=str)
        }
        
    except KeyError:
        return {
            'statusCode': 400,
            'headers': get_headers(),
            'body': json.dumps({'error': 'Missing centerId path parameter'})
        }
    except Exception as e:
        print(f"Error updating inventory: {str(e)}")
        return {
            'statusCode': 500,
            'headers': get_headers(),
            'body': json.dumps({'error': 'Internal server error'})
        }

def get_headers():
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'PUT, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization'
    }
