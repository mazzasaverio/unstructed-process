import os
import boto3
from io import BytesIO
from fastapi import FastAPI, HTTPException
from loguru import logger
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from unstructured.partition.pdf import partition_pdf
from unstructured.staging.base import elements_to_json
from confluent_kafka import Producer
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()


def init_s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=os.getenv("GOOGLE_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("GOOGLE_SECRET_ACCESS_KEY"),
        region_name="auto",
        endpoint_url="https://storage.googleapis.com",
    )


def init_mongo_client():
    return MongoClient(os.getenv("MONGO_URI"), server_api=ServerApi("1"))


def init_kafka_producer(config_file):
    return Producer(read_ccloud_config(config_file))


def read_ccloud_config(config_file):
    omitted_fields = set(
        ["schema.registry.url", "basic.auth.credentials.source", "basic.auth.user.info"]
    )
    conf = {}
    with open(config_file) as fh:
        for line in fh:
            line = line.strip()
            if len(line) != 0 and line[0] != "#":
                parameter, value = line.strip().split("=", 1)
                if parameter not in omitted_fields:
                    conf[parameter] = value.strip()
    return conf


s3_client = init_s3_client()
mongo_client = init_mongo_client()
db = mongo_client[os.getenv("MONGO_DB_NAME", "mydatabase")]
collection = db[os.getenv("MONGO_COLLECTION_NAME", "mycollection")]
producer = init_kafka_producer("client.properties")


def process_pdf(bucket_name, pdf_key):
    try:
        s3_object = s3_client.get_object(Bucket=bucket_name, Key=pdf_key)
        file_stream = BytesIO(s3_object["Body"].read())

        elements = partition_pdf(file=file_stream)
        elements_json = elements_to_json(elements)

        document = {"elements": elements_json}
        result = collection.insert_many([document])

        producer.produce(os.getenv("KAFKA_TOPIC"), key="success", value=pdf_key)
        producer.flush()

        logger.info("PDF processed and stored successfully.")
    except Exception as e:
        logger.error(f"Error processing PDF: {e}")
        raise


@app.post("/process-pdf/")
def api_process_pdf(bucket_name: str, pdf_key: str):
    try:
        process_pdf(bucket_name, pdf_key)
        return {
            "status": "success",
            "message": "PDF processed and stored successfully.",
        }
    except Exception as e:
        logger.error(f"API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    bucket_name = "esg-x-v8"
    pdf_key = "aaaaaaa.pdf"
    process_pdf(bucket_name, pdf_key)
