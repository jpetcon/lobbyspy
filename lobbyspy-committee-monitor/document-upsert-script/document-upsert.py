import base64
import boto3
import datetime as dt
import json
import pandas as pd
import requests

from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os

from pinecone import Pinecone

from sentence_transformers import SentenceTransformer
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')




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
    


def get_publication_documents():

    last_week = dt.datetime.strftime(dt.datetime.today() - dt.timedelta(days=7), '%Y-%m-%d')
    response = requests.get('https://committees-api.parliament.uk/api/Publications?StartDate={}&Take=1000'.format(last_week))
    
    try:
        publications = json.loads(response.content)['items']
    
        for i in publications:
            publication_id = i['id']
    
            for j in i['documents']:
                document_id = j['documentId']
                pdf_url = 'https://committees-api.parliament.uk/api/Publications/{}/Document/{}/OriginalFormat'.format(publication_id, document_id)
                pdf_response = requests.get(pdf_url)
    
                if json.loads(pdf_response.content)['fileName'].endswith('.pdf') == True:
                    document = open("tmp/publication-"+str(publication_id)+"-"+str(document_id)+".pdf", 'wb')
                    document.write(base64.b64decode(json.loads(pdf_response.content)['data']))
                    document.close()
                    print("File ", document_id, " downloaded")
                
    
                else:
                    print('unsupported document')
                
    except:
        print('no new publications')
        


    
    

### Upsert Script
    
pinecone_api = json.loads(get_secret("pinecone_serverless_api"))['key']

pc = Pinecone(api_key=pinecone_api)
index = pc.Index("uk-committees")

get_publication_documents()

for i in os.listdir('tmp'):
    print(i)
    try:
        # create a loader
        loader = PyPDFLoader("tmp/{}".format(i))

        # load your data
        data = loader.load()

        # split texts into 1000 character chunks
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=0)
        texts = text_splitter.split_documents(data)

        texts_list = []
        
        for j in texts:
            texts_list.append(j.page_content)
        
        print(texts_list)
        

        # create embeddings dataframe for upsert
        pdf_texts = pd.DataFrame(texts_list)
        embeddings = model.encode(pdf_texts[0])
        
        document_df = pdf_texts
        document_df = document_df.rename(columns={0:'text'})

        document_df['embeddings'] = embeddings.tolist()

        
        
        document_df['chunk'] = range(0, len(document_df))
        document_df['publication'] = i.split('-')[1]
        document_df['document'] = i.split('-')[2].replace('.pdf', '')
        document_df['id'] = document_df['publication']+'-'+document_df['document']+'-'+document_df['chunk'].astype(str)

        
        # upsert data
        
        start = 0

        if len(document_df) >= 99:
            end = 99
        else:
            end = len(document_df)

        while end <= len(document_df):
            print(start, end)

            ids_batch = [ document_df['id'][k] for k in range(start, end)]
            embeds = [document_df['embeddings'][x] for x in range(start, end)]
            meta_batch = [{
                    "publication" : document_df['publication'][y],
                    "document" : document_df['document'][y],
                    "text" : document_df['text'][y]
                } for y in range(start, end)]
            to_upsert = list(zip(ids_batch, embeds, meta_batch))
            index.upsert(vectors=to_upsert)

            start = start + 100
            end = end + 100

            if end >= len(document_df):
                end = len(document_df)

                ids_batch = [ document_df['id'][k] for k in range(start, end)]
                embeds = [document_df['embeddings'][x] for x in range(start, end)]
                meta_batch = [{
                        "publication" : document_df['publication'][y],
                        "document" : document_df['document'][y]
                    } for y in range(start, end)]
                to_upsert = list(zip(ids_batch, embeds, meta_batch))
                index.upsert(vectors=to_upsert)

                break


        
    except:
        print('document empty')
    


    
