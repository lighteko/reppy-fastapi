# Dockerfile for AWS Lambda deployment

FROM public.ecr.aws/lambda/python:3.11

# Copy requirements and install
COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ${LAMBDA_TASK_ROOT}/src/
COPY prompts/ ${LAMBDA_TASK_ROOT}/prompts/

# Set the Lambda handler
CMD ["src.consumer.lambda_handler.handler"]

