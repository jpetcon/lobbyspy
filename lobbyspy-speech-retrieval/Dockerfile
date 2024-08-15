FROM public.ecr.aws/lambda/python:3.8
COPY speech-retrieval.py .
COPY requirements.txt .
COPY tmp/ tmp/
RUN pip install -r requirements.txt
CMD [ "speech-retrieval.main" ]