import json
import boto3
import os

sns = boto3.client('sns')
dynamodb = boto3.resource('dynamodb')
SNS_TOPIC_ARN = os.environ['SNS_TOPIC']  # Set in your template
SUBSCRIPTIONS_TABLE = os.environ.get('SUBSCRIPTIONS_TABLE')  # Optional for tracking

def lambda_handler(event, context):
    # Add CORS headers
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
    }
    
    path = event.get('requestContext', {}).get('http', {}).get('path') or event.get('path', '')
    method = event.get('requestContext', {}).get('http', {}).get('method') or event.get('httpMethod', '')

    if method == 'OPTIONS':
        return {'statusCode': 200, 'headers': headers, 'body': json.dumps({'message': 'CORS preflight'})}
    
    if path.endswith('/subscribe') and method == 'POST':
        result = subscribe(event)
    elif path.endswith('/unsubscribe') and method == 'POST':
        result = unsubscribe(event)
    elif path.endswith('/subscriptions') and method == 'GET':
        result = get_subscriptions(event)
    else:
        result = {'statusCode': 404, 'body': json.dumps({'error': 'Not found'})}
    
    result['headers'] = headers
    return result

def subscribe(event):
    body = json.loads(event.get('body', '{}'))
    email = body.get('email')
    species = body.get('species')
    if not email or not species:
        return {'statusCode': 400, 'body': json.dumps({'error': 'Missing email or species'})}

    # Subscribe email to SNS topic (filter by species if using SNS message attributes)
    response = sns.subscribe(
        TopicArn=SNS_TOPIC_ARN,
        Protocol='email',
        Endpoint=email,
        Attributes={
            'FilterPolicy': json.dumps({'species': [species]})
        }
    )
    # Store in DynamoDB for tracking
    if SUBSCRIPTIONS_TABLE:
        table = dynamodb.Table(SUBSCRIPTIONS_TABLE)
        table.put_item(Item={'email': email, 'species': species})

    return {'statusCode': 200, 'body': json.dumps({'message': 'Subscribed successfully'})}

def unsubscribe(event):
    body = json.loads(event.get('body', '{}'))
    email = body.get('email')
    species = body.get('species')
    if not email or not species:
        return {'statusCode': 400, 'body': json.dumps({'error': 'Missing email or species'})}

    # List subscriptions and find the correct one to unsubscribe
    subs = sns.list_subscriptions_by_topic(TopicArn=SNS_TOPIC_ARN)
    for sub in subs['Subscriptions']:
        if sub['Endpoint'] == email:
            sns.unsubscribe(SubscriptionArn=sub['SubscriptionArn'])
            break

    # Remove from DynamoDB
    if SUBSCRIPTIONS_TABLE:
        table = dynamodb.Table(SUBSCRIPTIONS_TABLE)
        table.delete_item(Key={'email': email, 'species': species})

    return {'statusCode': 200, 'body': json.dumps({'message': 'Unsubscribed successfully'})}

def get_subscriptions(event):
    query_params = event.get('queryStringParameters') or {}
    email = query_params.get('email', '')
    if not email:
        return {'statusCode': 400, 'body': json.dumps({'error': 'Email parameter required'})}
    
    subscriptions = []
    subs = sns.list_subscriptions_by_topic(TopicArn=SNS_TOPIC_ARN)
    
    for sub in subs['Subscriptions']:
        if sub['Endpoint'] == email and sub['Protocol'] == 'email':
            try:
                attrs = sns.get_subscription_attributes(SubscriptionArn=sub['SubscriptionArn'])
                filter_policy = attrs.get('Attributes', {}).get('FilterPolicy')
                if filter_policy:
                    filter_data = json.loads(filter_policy)
                    for species in filter_data.get('species', []):
                        subscriptions.append({'email': email, 'species': species})
            except:
                continue
    
    return {'statusCode': 200, 'body': json.dumps({'subscriptions': subscriptions})}
