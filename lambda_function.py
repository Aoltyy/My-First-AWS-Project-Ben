import json
import boto3
import urllib.parse
import datetime
import os

# --- AWS CLIENTS ---
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')

# --- CONFIGURATION ---
TABLE_NAME = 'ImageMetadata'

SNS_TOPIC_ARN = 'arn:aws:sns:us-east-1:111111111:Uploaded' 

def lambda_handler(event, context):
    """Lambda function to process S3 upload events: """
    
    
    try:
        # Get the bucket name and file key (filename) from the event
        bucket = event['Records'][0]['s3']['bucket']['name']
        # Decode the filename (e.g., converts "My%20Image.jpg" to "My Image.jpg")
        key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
        
        # Get file size
        size = event['Records'][0]['s3']['object']['size']
        upload_time = str(datetime.datetime.now())
        
        # Construct the object URL (for reference)
        object_url = f"https://{bucket}.s3.amazonaws.com/{key}"
        
        print(f"Processing file: {key} from bucket: {bucket}")

        # 2. Write Metadata to DynamoDB
        table = dynamodb.Table(TABLE_NAME)
        table.put_item(Item={
            'metadata': key,       # Partition Key
            'Bucket': bucket, 
            'UploadTime': upload_time, 
            'Size': size,
            'ObjectURL': object_url
        })
        
        # 3. Publish Notification to SNS
        sns.publish(
            TopicArn=SNS_TOPIC_ARN, 
            Message=f"New image uploaded and processed successfully: {key}", 
            Subject='ScribeServ: Upload Complete'
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps(f'Successfully processed {key}')
        }
        
    except Exception as e:
        print(f"Error processing image: {str(e)}")
        raise e