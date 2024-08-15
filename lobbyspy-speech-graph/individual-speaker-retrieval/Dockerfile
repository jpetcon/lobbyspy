FROM public.ecr.aws/lambda/python:3.8
COPY individual-speaker-retrieval.py .
COPY requirements.txt .
COPY tmp/ tmp/
RUN pip install -r requirements.txt
CMD [ "individual-speaker-retrieval.main" ]