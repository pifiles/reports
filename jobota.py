import boto3
import json
import time
from datetime import datetime

# Initialize the AWS IoT client
iot_client = boto3.client('iot')

# Define the job document (the given JSON for OTA job creation)
# job_document = {
#     "afr_ota": {
#         "protocols": ["MQTT"],
#         "streamname": "AFR_OTA-48648284-0ba8-4fc7-b30c-db8db1015f69",
#         "files": [
#             {
#                 "filepath": "expresslink_firmware.bin",
#                 "filesize": 200876,
#                 "fileid": 0,
#                 "certfile": "TheCertificate",
#                 "fileType": 101,
#                 "sig-sha256-ecdsa": "MEUCIEZxqErogG1tSfnM7Xb48/u2Rr5a5llJKSFni7JTlJVMAiEAkjR2QJ2v7UU7rqWLVQKBRU7S3acF+kYEbulkW/I/+uI="
#             }
#         ]
#     }
# }
job_document = {
  "afr_ota": {
    "protocols": [
      "MQTT"
    ],
    "streamname": "AFR_OTA-9d0c8160-4427-4534-bc63-24510a9797d7",
    "files": [
      {
        "filepath": "expresslink_firmware.bin",
        "filesize": 1625568,
        "fileid": 0,
        "certfile": "TheCertificate",
        "fileType": 101,
        "sig-sha256-ecdsa": "MEUCIQCMw6jAslzGmOg22/+mcke9yf+8F48fiN5OPobRHk+liAIgTQiRyg7j+SZIH/ViSsTj5tITxLyqdzzvinidijf2Skw="
      }
    ]
  }
}

job_document_hota = {
  "afr_ota": {
    "protocols": [
      "MQTT"
    ],
    "streamname": "AFR_OTA-8823f916-407e-4ec8-ba8b-616e2ff83a0d",
    "files": [
      {
        "filepath": "HOTAImage.bin",
        "filesize": 4096,
        "fileid": 0,
        "certfile": "TheCertificate",
        "fileType": 202,
        "sig-sha256-ecdsa": "MEUCIQDLUeOdU2csCG+Fnn+Qee2PQGfHfQcQNSkX1n+Wo37qOgIgBT/z+OxCgQcQTqUpt6PPhetN2q7Yrw23SMNPcDAAvmo="
      }
    ]
  }
}

# Function to list and delete all jobs
def delete_all_jobs():
    try:
        # Get the list of all jobs
        response = iot_client.list_jobs(maxResults=50)  # You can adjust maxResults if needed
        jobs = response.get('jobs', [])

        if not jobs:
            print("No jobs found to delete.")
            return

        # Iterate through each job and delete it
        for job in jobs:
            job_id = job['jobId']
            print(f"Deleting job: {job_id}")
            iot_client.delete_job(jobId=job_id, force=True)  # force=True to delete even if the job is in progress
            print(f"Job {job_id} deleted successfully.")

        # If there are more jobs (pagination), keep fetching and deleting
        while 'nextToken' in response:
            next_token = response['nextToken']
            response = iot_client.list_jobs(maxResults=50, nextToken=next_token)
            jobs = response.get('jobs', [])

            for job in jobs:
                job_id = job['jobId']
                print(f"Deleting job: {job_id}")
                iot_client.delete_job(jobId=job_id, force=True)  # force=True to delete even if the job is in progress
                print(f"Job {job_id} deleted successfully.")

    except Exception as e:
        print(f"Error deleting jobs: {e}")

# Function to create a new OTA job
def create_ota_job():
    try:
        # Generate a unique job ID using datetime
        current_time = datetime.now().strftime('%Y%m%d%H%M%S')
        job_name = f"Expresslink_Test_ota_{current_time}"

        # Define the thing name and ARN (replace with your actual thing name)
        thing_name = "silicon_labs_thing"

        # Get the ARN of the thing
        response = iot_client.describe_thing(thingName=thing_name)
        thing_arn = response['thingArn']

        # Create the OTA job
        response = iot_client.create_job(
            jobId=job_name,
            targets=[thing_arn],  # Use the ARN as the target
            document=json.dumps(job_document),
            description="OTA update job for Expresslink Test",
            targetSelection='SNAPSHOT',  # Use 'SNAPSHOT' or 'CONTINUOUS' depending on your use case
            jobExecutionsRolloutConfig={
                'maximumPerMinute': 1  # You can adjust this value as needed
            },
            timeoutConfig={
                'inProgressTimeoutInMinutes': 60  # Set your timeout configuration here
            }
        )
        print(f"OTA Job '{job_name}' created successfully.")

    except Exception as e:
        print(f"Error creating OTA job: {e}")

# Main function that deletes all jobs and creates a new one
def main():
    delete_all_jobs()
    create_ota_job()

# Run the script
main()
