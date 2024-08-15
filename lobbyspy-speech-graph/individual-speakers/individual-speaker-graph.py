import boto3
import json
import pandas as pd

s3 = boto3.client('s3')

def main(event, context):
    
    
    ## Get person list and graph data
    bucket = "lobbyspy-lookup"
    
    s3.download_file(bucket, "personlist.csv", '/tmp/personlist.csv')
    s3.download_file(bucket, "all_graph_points.csv", '/tmp/all_graph_points.csv')
    
    person_list = pd.read_csv('/tmp/personlist.csv')
    graph_df = pd.read_csv('/tmp/all_graph_points.csv')
    
    
    
    ## Generate individual graph points
    for x in range(len(personlist)):

        speakerid = personlist['id'][x]
        speakername = personlist['name'][x]
    
        speaker_df = graph_df[graph_df['speaker'] == speakername].reset_index(drop=True)
    
        graph_data = []
        graph_data_template = {"x" : 0,
                            "y" : 0,
                            "z" : "string",
                            "id" : "string"}
    
        for i in range(len(speaker_df)):
            graph_data_template = {"x" : 0,
                            "y" : 0,
                            "z" : "string",
                            "id" : "string"}
            graph_data_template["x"] = speaker_df['x'][i]
            graph_data_template["y"] = speaker_df['y'][i]
            graph_data_template["z"] = speaker_df['speech'][i]
            graph_data_template["id"] = speaker_df['id'][i]
    
            graph_data.append(graph_data_template)
    
        series_data = {"name" : speakername, "data" : graph_data}
    
        with open('/tmp/data.json', 'w') as f:
            json.dump(str(series_data), f)
        
    
        key =  "{}/graphdata.json".format(speakerid)
        s3.upload_file('/tmp/data.json', 'lobbyspy-person-data', key)
