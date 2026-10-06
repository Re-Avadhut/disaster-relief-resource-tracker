"""
Lambda: get_low_stock.py
Purpose: Find all resources across all centers that are below their threshold.
Trigger: GET /inventory/low-stock
Permissions needed: dynamodb:Query on Inventory table using LowStock-index GSI
"""

import json
import boto3

dynamodb = boto3.resource('dynamodb')
inventory_table = dynamodb.Table('Inventory')

def lambda_handler(event, context):
    """
    Returns all inventory items where lowStock = 'true'.
    Uses the LowStock-index GSI so we don't have to scan the entire table.
    """
    try:
        # Query the GSI where lowStock = 'true'
        response = inventory_table.query(
            IndexName='LowStock-index',
            KeyConditionExpression='lowStock = :ls',
            ExpressionAttributeValues={':ls': 'true'}
        )
        
        items = response.get('Items', [])
        
        # Enrich with center names for display
        centers_table = dynamodb.Table('ReliefCenters')
        center_cache = {}
        enriched_items = []
        
        for item in items:
            center_id = item['centerId']
            
            # Cache center lookups to avoid redundant reads
            if center_id not in center_cache:
                center_resp = centers_table.get_item(Key={'centerId': center_id})
                center_cache[center_id] = center_resp.get('Item', {})
            
            center = center_cache[center_id]
            enriched_items.append({
                'centerId': center_id,
                'centerName': center.get('name', 'Unknown'),
                'centerLocation': center.get('location', 'Unknown'),
                'resourceType': item['resourceType'],
                'quantity': item.get('quantity', 0),
                'unit': item.get('unit', ''),
                'threshold': item.get('threshold', 0)
            })
        
        return {
            'statusCode': 200,
            'headers': get_headers(),
            'body': json.dumps({
                'lowStockItems': enriched_items,
                'count': len(enriched_items)
            }, default=str)
        }
        
    except Exception as e:
        print(f"Error getting low stock: {str(e)}")
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
