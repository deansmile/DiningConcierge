import json
import os
import random
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
from boto3.dynamodb.conditions import Key, Attr
from requests_aws4auth import AWS4Auth
from botocore.vendored import requests
from botocore.exceptions import ClientError

REGION = 'us-east-1'
HOST = 'search-search-restaurants-ekx7xirg3kxoibn53nlvpndjzq.us-east-1.es.amazonaws.com'
INDEX = 'restaurants'

USERTABLE= 'user_history'

def insert_table(email,data):
    res = [{'email':email, 'data':data}]
    db = boto3.resource('dynamodb')
    table = db.Table(USERTABLE)

    for data in res:
        response = table.put_item(Item=data)
    print('@insert_data: response', response)

def lambda_handler(event, context):
    sqs = boto3.client('sqs', region_name='us-east-1')
    queue_url = 'https://sqs.us-east-1.amazonaws.com/739275450007/DiningConciergeRequestsQueue'

    # Send or receive messages using the Queue URL
    response_from_sqs = sqs.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=10
    )

    print("Messages:", response_from_sqs['Messages'][0])

    if response_from_sqs:
        message = response_from_sqs['Messages'][0]
        # retrieving relevant info
        cuisine = message['MessageAttributes']['Cuisine']['StringValue'] if 'MessageAttributes' in message and 'Cuisine' in message['MessageAttributes'] else "chinese"
        location = message['MessageAttributes']['Location']['StringValue'] if 'MessageAttributes' in message and 'Location' in message['MessageAttributes'] else "manhattan"
        email = message['MessageAttributes']['Email']['StringValue'] if 'MessageAttributes' in message and 'Email' in message['MessageAttributes'] else "ds5725@nyu.edu"
        people = message['MessageAttributes']['Numberofpeople']['StringValue'] if 'MessageAttributes' in message and 'Numberofpeople' in message['MessageAttributes'] else "2"
        time = message['MessageAttributes']['Time']['StringValue'] if 'MessageAttributes' in message and 'Time' in message['MessageAttributes'] else "10:00"
        date = message['MessageAttributes']['Date']['StringValue'] if 'MessageAttributes' in message and 'Date' in message['MessageAttributes'] else "2027-01-02"
        Business_ID_list = query(cuisine)
        # if cuisine == "chinese":
        #     Business_ID_list = ["8Oo2AtQEPDfxIOnA8wfXoQ","83BXSwE0166sObnXLUE4bQ","-VRnWGBVMovSS0Ijta_qyg"]
        # if cuisine == "italian":
        #     Business_ID_list = ["vjubSxmdG_HoBBgd39geBw","LXdblKc5g1Dp17xiV-Am1w","K9Ur20N51Li3sAvaV9-6Ng"]
        # if cuisine == "mexican":
        #     Business_ID_list = ["v8tuFxvNkKdZytWTn9BhMA","jnEv25Y2DosTq2sNnvmC9g","1nR3kKOs938gcgnw6p5wjg"]
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('yelp-restaurants')
        recommendBackMessage = []
        for n in Business_ID_list:
            response_from_DB = table.query(
                KeyConditionExpression=Key('id').eq(n)
            )
            recommend_restaurant = response_from_DB['Items'][0]["name"]
            recommend_address = response_from_DB['Items'][0]["address"]
            recommendBackMessage.append({
                "name": recommend_restaurant,
                "address": recommend_address
            })

        message_to_user = \
            "Hey! This is the recommended " \
            + cuisine \
            + "cuisine for " \
            + people \
            + " people, for " \
            + date \
            + " at " \
            + time \
            + " : 1. " \
            + recommendBackMessage[0]["name"] + " located at " + recommendBackMessage[0]["address"] + ", 2. " \
            + recommendBackMessage[1]["name"] + " located at " + recommendBackMessage[1]["address"] + ", 3. " \
            + recommendBackMessage[2]["name"] + " located at " + recommendBackMessage[2]["address"] + ". Enjoy!!"


        # Email sending to user
        send_email(email, message_to_user)
        insert_table(email, message_to_user)



        # Delete queue info, fifo
        sqs.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=response_from_sqs['Messages'][0]['ReceiptHandle']
        )

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': '*',
            },
            'body': json.dumps({'results': message_to_user})
        }
    else:

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': '*',
            },
            'body': json.dumps("SQS queue is now empty")
        }


def query(input):
    q = {'size': 20, 'query': {'multi_match': {'query': input}}}

    client = OpenSearch(hosts=[{
        'host': HOST,
        'port': 443
    }],
        http_auth=get_awsauth(REGION, 'es'),
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection)

    res = client.search(index=INDEX, body=q)
    hits = res['hits']['hits']
    result = []
    while len(result) != 3:
        index = random.randint(0, 19)
        RestaurantID = hits[index]['_source']['id']
        if RestaurantID not in result:
            result.append(RestaurantID)
    return result


def send_email(email, body_text):
    SENDER = "diweisheng1@gmail.com"
    RECIPIENT = email
    AWS_REGION = "us-east-1"
    SUBJECT = "Dining Suggestion Based On your Given Information"
    BODY_TEXT = (body_text)
    CHARSET = "UTF-8"
    client = boto3.client('ses', region_name=AWS_REGION)

    try:
        response = client.send_email(
            Destination={
                'ToAddresses': [
                    RECIPIENT,
                ],
            },
            Message={
                'Body': {
                    'Text': {
                        'Charset': CHARSET,
                        'Data': BODY_TEXT,
                    },
                },
                'Subject': {
                    'Charset': CHARSET,
                    'Data': SUBJECT,
                },
            },
            Source=SENDER,
        )

    # Error Handling
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print("Email sent! Message ID:"),
        print(response['MessageId'])


def get_awsauth(region, service):
    cred = boto3.Session().get_credentials()
    return AWS4Auth(cred.access_key,
                    cred.secret_key,
                    region,
                    service,
                    session_token=cred.token)