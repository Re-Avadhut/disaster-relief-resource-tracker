"""
Lambda: get_stats.py
Purpose: Return summary statistics for the admin dashboard.
Trigger: GET /stats
Permissions needed: dynamodb:Scan on ReliefCenters, dynamodb:Scan on HelpRequests, dynamodb:Query on LowStock-index
"""

import json
import boto3

dynamodb = boto3.resource('dynamodb')
centers_table = dynamodb.Table('ReliefCenters')
requests_table = dynamodb.Table('HelpRequests')
inventory_table = dynamodb.Table('Inventory')

def lambda_handler(event, context):
    """
    Returns a summary object:
    {
        "totalCenters": 5,
        "activeCenters": 4,
        "totalPendingRequests": 12,
        "totalAssignedRequests": 3,
        "totalResolvedRequests": 20,
        "criticalLowStock": 8,
        "urgentPendingRequests": 4
    }
    """
    try:
        # Count centers
        centers_resp = centers_table.scan(Select='COUNT')
        total_centers = centers_resp.get('Count', 0)
        
        active_resp = centers_table.scan(
            Select='COUNT',
            FilterExpression='#s = :active',
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={':active': 'active'}
        )
        active_centers = active_resp.get('Count', 0)
        
        # Count requests by status
        pending_resp = requests_table.query(
            IndexName='StatusUrgency-index',
            KeyConditionExpression='#s = :status',
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={':status': 'pending'},
            Select='COUNT'
        )
        pending_count = pending_resp.get('Count', 0)
        
        assigned_resp = requests_table.query(
            IndexName='StatusUrgency-index',
            KeyConditionExpression='#s = :status',
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={':status': 'assigned'},
            Select='COUNT'
        )
        assigned_count = assigned_resp.get('Count', 0)
        
        resolved_resp = requests_table.query(
            IndexName='StatusUrgency-index',
            KeyConditionExpression='#s = :status',
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={':status': 'resolved'},
            Select='COUNT'
        )
        resolved_count = resolved_resp.get('Count', 0)
        
        # Count critically low stock items (urgency=1 pending requests)
        urgent_resp = requests_table.query(
            IndexName='StatusUrgency-index',
            KeyConditionExpression='#s = :status AND #u = :urgency',
            ExpressionAttributeNames={'#s': 'status', '#u': 'urgency'},
            ExpressionAttributeValues={':status': 'pending', ':urgency': 1},
            Select='COUNT'
        )
        urgent_pending = urgent_resp.get('Count', 0)
        
        # Count low stock items across all centers
        low_stock_resp = inventory_table.query(
            IndexName='LowStock-index',
            KeyConditionExpression='lowStock = :ls',
            ExpressionAttributeValues={':ls': 'true'},
            Select='COUNT'
        )
        critical_low_stock = low_stock_resp.get('Count', 0)
        
        return {
            'statusCode': 200,
            'headers': get_headers(),
            'body': json.dumps({
                'totalCenters': total_centers,
                'activeCenters': active_centers,
                'totalPendingRequests': pending_count,
                'totalAssignedRequests': assigned_count,
                'totalResolvedRequests': resolved_count,
                'urgentPendingRequests': urgent_pending,
                'criticalLowStock': critical_low_stock
            })
        }
        
    except Exception as e:
        print(f"Error getting stats: {str(e)}")
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
