import boto3
import json
import openai
import pandas as pd
import pinecone
import requests

from openai import OpenAI

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
    


def handle_previous_questions(previous_questions_responses, question, api_key):
    '''Rewrites follow up questions so that they can be used for semantic search'''
    
    client = OpenAI(api_key=api_key)

    completion = client.chat.completions.create(
        model='gpt-3.5-turbo-16k',
        messages=[
        {"role" : "user", "content" :'''Rewrite the following question: {} incorporating the previous questions and response below, so that the question can be used for semantic search. {}'''.format(question, str(previous_questions_responses))}
        ]
        )



    gpt_response_text = completion.choices[0].message.content
    
    return(gpt_response_text)
    
    

def question_encoding(question, api_key):
    '''Encodes question text into numeric embeddings'''
    
    API_URL = "https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/all-MiniLM-L6-v2"
    headers = {"Authorization": "Bearer {}".format(api_key)}
    
    def query(payload):
    	response = requests.post(API_URL, headers=headers, json=payload)
    	return response.json()
    	
    embeddings = query({"inputs": [question]})
    
    return embeddings
    

def pinecone_vector_search(index_name, api_key, embeddings):
    '''Searches pinecone vector db for similar terms'''
    
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
       top_k=50,
       include_metadata=True)
       
    retrieved_list = []

    for x in pinecone_response['matches']:
        retrieved_list.append(x['metadata'])
    
    return retrieved_list


def create_gpt_response(question, retrieved_list, api_key):
    '''Generates narrative response from database results'''
    
    client = OpenAI(api_key=api_key)

    completion = client.chat.completions.create(
        model='gpt-3.5-turbo-16k',
        messages=[
        {"role" : "system", "content" :'''You are a helpful AI assistant for parliamentary lobbyists in the UK. You should ignore your training data and use the following data to base your answers off. Where it is appropriate, you can quote explicitly from this data: {}'''.format(str(retrieved_list))},
        {"role": "user", "content": question}
        ]
        )



    gpt_response_text = completion.choices[0].message.content
    
    return(gpt_response_text)
    


def get_people(answer):
    '''Get IDs of people mentioned in response'''
    
    bucket = "lobbyspy-lookup"
    key = "personlist.csv"
    filename = '/tmp/personlist.csv'
    
    s3.download_file(bucket, key, filename)
    
    person_list = pd.read_csv('/tmp/personlist.csv')
    
    
    people = []

    for i in range(len(person_list)):
        if person_list['name'][i].lower() in answer.lower():
            people.append(person_list['id'][i])
            
    return(people)
    
    
    
def store_results(results, filepath_string):
    '''Save results for future use'''
    
    filepath = filepath_string.replace('"','')

    json_string = json.dumps(results, default=str)
    with open('/tmp/results.json', 'w') as outfile:
        outfile.write(json_string)
    
    bucket = "lobbyspy-results"
    key = "{}/results.json".format(filepath)
    filename = '/tmp/results.json'
    
    
    s3.upload_file(Filename=filename, Bucket=bucket, Key=key)
       

def main(event, context):
    
    print(event)
    
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
        
        open_ai_key = json.loads(get_secret("open_ai_api"))['key']
        
        pinecone_key = json.loads(get_secret("pinecone_api"))['key']
        
        hugging_face_key = json.loads(get_secret("hugging_face_api"))['key']
        
        
        
        if data['follow_up'] == "true":
            
            print('true')
            
            previous = data['previous_questions_responses']
            
            current_question = handle_previous_questions(previous, data['question'], open_ai_key)
            
        else:
            
            current_question = data['question']
        
            previous = ""
        
        
        
        print(current_question)
        
        embeddings = question_encoding(current_question, hugging_face_key)
        
        retrieved_list = pinecone_vector_search('hansard-index', pinecone_key, embeddings)
        
        gpt_response_text = create_gpt_response(current_question, retrieved_list, open_ai_key)
        
        people = get_people(gpt_response_text)
        
        
        results = {'question' : data['question'], 'retrieved_list' : retrieved_list, 'response': gpt_response_text, "follow_up" : data['follow_up'], "previous" : previous, 'people': people}
        
        store_results(results, data['filepath'])
        
        
        return {
            'statusCode': 200,
            'headers': { 
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, PUT, GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Access-Control-Allow-Headers, Authorization, X-Requested-With'
            },
            'body': json.dumps(results, default=str)
        }
        
    
    
    
    