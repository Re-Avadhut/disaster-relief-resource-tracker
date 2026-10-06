"""
Lambda: update_request_status.py
Purpose: Update the status of a help request (pending → assigned → resolved).
Trigger: PUT /requests/{requestId}
Permissions needed: dynamodb:UpdateItem on HelpRequests table
"""

import json
import boto3
from datetime import datetime, timezone

dynamodb = boto3.resource('dynamodb')
requests_table = dynamodb.Table('HelpRequests')

def lambda_handler(event, context):
    """
    Updates a help request's status and optionally assigns a center.
    
    Path parameter: requestId
    Expected JSON body:
    {
        "status": "assigned",
        "assignedCenterId": "uuid-of-center"
    }
    
    Valid status transitions:
      pending → assigned → resolved
    """
    try:
        request_id = event['pathParameters']['requestId']
        body = json.loads(event.get('body', '{}'))
        
        new_status = body.get('status')
        if not new_status:
            return {
                'statusCode': 400,
                'headers': get_headers(),
                'body': json.dumps({'error': 'status is required'})
            }
        
        # Validate status value
        valid_statuses = ['pending', 'assigned', 'resolved']
        if new_status not in valid_statuses:
            return {
                'statusCode': 400,
                'headers': get_headers(),
                'body': json.dumps({'error': f'Invalid status. Must be one of: {valid_statuses}'})
            }
        
        # Build update expression
        update_parts = ['#s = :status']
        expr_values = {':status': new_status}
        expr_names = {'#s': 'status'}
        
        # Optionally assign a center
        if 'assignedCenterId' in body:
            update_parts.append('#ac = :center')
            expr_values[':center'] = body['assignedCenterId']
            expr_names['#ac'] = 'assignedCenterId'
        
        response = requests_table.update_item(
            Key={'requestId': request_id},
            UpdateExpression='SET ' + ', '.join(update_parts),
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
            ReturnValues='ALL_NEW'
        )
        
        return {
            'statusCode': 200,
            'headers': get_headers(),
            'body': json.dumps({
                'message': f'Request status updated to {new_status}',
                'request': response['Attributes']
            }, default=str)
        }
        
    except KeyError:
        return {
            'statusCode': 400,
            'headers': get_headers(),
            'body': json.dumps({'error': 'Missing requestId path parameter'})
        }
    except Exception as e:
        print(f"Error updating request: {str(e)}")
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
