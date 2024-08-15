import boto3
import json

s3 = boto3.client('s3')

def main(event, context):

    ##Deal with CORS
    
    if event['httpMethod'] == 'OPTIONS':
        
        return {
            'statusCode': 200,
            'headers': { 
                'Access-Control-Allow-Origin': 'http://localhost:3000/',
                'Access-Control-Allow-Methods': 'POST, PUT, GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Access-Control-Allow-Headers, Authorization, X-Requested-With'
            }
            }
            
    
    else:
        data = json.loads(event['body'])
        
        personid = data['person_id']
        
        bucket = "lobbyspy-person-data"
        key = "{}/graphdata.json".format(personid)
        filename = '/tmp/graphdata.json'
        
        s3.download_file(bucket, key, filename)
        
        # Opening JSON file
        f = open('/tmp/graphdata.json')
         
        # returns JSON object as 
        # a dictionary
        graph_data = json.load(f)
        
        
        return {
            'statusCode': 200,
            'headers': { 
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, PUT, GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Access-Control-Allow-Headers, Authorization, X-Requested-With'
            },
            'body': json.dumps(graph_data, default=str)
        }
    