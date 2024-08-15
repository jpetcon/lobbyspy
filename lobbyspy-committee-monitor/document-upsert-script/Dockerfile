FROM python:3.9
COPY document-upsert.py .
COPY tmp/ .
COPY requirements.txt .
RUN pip install -r requirements.txt
CMD [ "python", "-u", "document-upsert.py" ]