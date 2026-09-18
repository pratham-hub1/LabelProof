import boto3
import time

def create_table():
    session = boto3.Session(profile_name="labelcheck", region_name="ap-south-1")
    dynamodb = session.client('dynamodb')
    
    table_name = 'scans'
    
    try:
        print(f"Creating DynamoDB table {table_name}...")
        dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {'AttributeName': 'scan_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'scan_id', 'AttributeType': 'S'},
                {'AttributeName': 'gsi1_pk', 'AttributeType': 'S'},
                {'AttributeName': 'gsi1_sk', 'AttributeType': 'S'},
                {'AttributeName': 'gsi2_pk', 'AttributeType': 'S'},
                {'AttributeName': 'gsi2_sk', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'GSI-1',
                    'KeySchema': [
                        {'AttributeName': 'gsi1_pk', 'KeyType': 'HASH'},
                        {'AttributeName': 'gsi1_sk', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                },
                {
                    'IndexName': 'GSI-2',
                    'KeySchema': [
                        {'AttributeName': 'gsi2_pk', 'KeyType': 'HASH'},
                        {'AttributeName': 'gsi2_sk', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        print("Table creation initiated. Waiting for it to become active...")
        waiter = dynamodb.get_waiter('table_exists')
        waiter.wait(TableName=table_name)
        print(f"Table {table_name} is active.")
    except dynamodb.exceptions.ResourceInUseException:
        print(f"Table {table_name} already exists.")
        
if __name__ == "__main__":
    create_table()
