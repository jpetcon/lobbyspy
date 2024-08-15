import boto3
import json
import pandas as pd
import pinecone
import requests

s3 = boto3.client("s3")



def get_secret(secret):
    secret_name = secret
    region_name = "eu-west-2"

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        # For a list of exceptions thrown, see
        # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
        raise e

    secret = get_secret_value_response['SecretString']
    
    return secret
    


def question_encoding(question, api_key):
    '''Encodes question text into numeric embeddings'''
    
    API_URL = "https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/all-MiniLM-L6-v2"
    headers = {"Authorization": "Bearer {}".format(api_key)}
    
    def query(payload):
        response = requests.post(API_URL, headers=headers, json=payload)
        return response.json()
        
    embeddings = query({"inputs": [question]})
    
    return embeddings
    
 

def get_person(person_id):
    '''Get IDs of people mentioned in response'''
    
    bucket = "lobbyspy-lookup"
    key = "personlist.csv"
    filename = '/tmp/personlist.csv'
    
    s3.download_file(bucket, key, filename)
    
    person_list = pd.read_csv('/tmp/personlist.csv')
    
    
    person = person_list[person_list['id'] == int(person_id)]['name'].values[0]
            
    return(person)   



def pinecone_vector_search(index_name, api_key, embeddings, person):
    '''Searches pinecone vector db for similar terms and returns those over the threshold'''
    
    try:
        question_embeddings = embeddings[0]
        
    except:
        question_embeddings = embeddings
    
    # Initialise pinecone
    pinecone.init(api_key=api_key, environment="gcp-starter")
    index = pinecone.Index(index_name)
    
    # Search DB
    pinecone_response = index.query(
       vector=question_embeddings,
       filter={'speakername' : person},
       top_k=50,
       include_metadata=True,
       include_values=True)
       
    retrieved_list = []

    for x in pinecone_response['matches']:
        if x['score'] > 0.25:
            x['metadata']['similarity_score'] = x['score']
            x['metadata']['id'] = x['id']
            retrieved_list.append(x['metadata'])
    
    return retrieved_list
    


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
        
        pinecone_key = json.loads(get_secret("pinecone_api"))['key']
        
        hugging_face_key = json.loads(get_secret("hugging_face_api"))['key']
        
        
        
        embeddings = question_encoding(data['question'], hugging_face_key)
        
        person = get_person(data['person_id'])

        retrieved_list = pinecone_vector_search('hansard-index', pinecone_key, embeddings, person)
        
        return {
            'statusCode': 200,
            'headers': { 
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, PUT, GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Access-Control-Allow-Headers, Authorization, X-Requested-With'
            },
            'body': json.dumps(retrieved_list, default=str)
        }
    