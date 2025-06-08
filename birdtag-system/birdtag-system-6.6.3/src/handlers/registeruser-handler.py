import boto3
import os
import json
from datetime import datetime
import logging

# Setup logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialise DynamoDB
dynamodb = boto3.resource('dynamodb')
user_table = dynamodb.Table(os.environ['USER_TABLE_NAME'])

# Initialise Cognito client
cognito = boto3.client('cognito-idp')
USER_POOL_ID = os.environ['COGNITO_USER_POOL_ID']
CLIENT_ID = os.environ['COGNITO_CLIENT_ID']

def lambda_handler(event, context):
    try:
        logger.info(f"Received event: {event}")

        email = event.get("email")
        name = event.get("name")
        password = event.get("password")

        if not email or not name or not password:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing required fields: email, name, password"})
            }

        # Register user in Cognito
        response = cognito.sign_up(
            ClientId=CLIENT_ID,
            Username=email,
            Password=password,
            UserAttributes=[
                {"Name": "email", "Value": email},
                {"Name": "name", "Value": name}
            ]
        )

        user_sub = response['UserSub']

        # Store user metadata into DynamoDB
        user_table.put_item(Item={
            "email": email,
            "name": name,
            "userSub": user_sub,
            "createdAt": datetime.utcnow().isoformat(),
            "role": "user",
            "status": "active"
        })

        logger.info(f"User {email} registered and stored in DB")

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "✅ User registered and saved",
                "email": email,
                "userSub": user_sub
            })
        }

    except Exception as e:
        logger.error(f"Registration failed: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Registration failed", "details": str(e)})
        }
