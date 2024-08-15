FROM public.ecr.aws/lambda/python:3.8
COPY question-bot.py .
COPY requirments.txt requirements.txt
COPY tmp/ tmp/
RUN pip install -r requirements.txt
CMD [ "question-bot.main" ]