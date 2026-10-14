#!/bin/bash

CRAWL_JOB_ID="14fa9118-dbe3-4d59-ba3b-16a03392970d"
MAX_DEPTH="5"
MAX_PAGES="2000"
NAMESPACE="chattyhub-staging"
IMAGE="ghcr.io/farajan/chatbot-crawler-job:0.1.0"

kubectl run crawler-test -it --restart=Never \
    --namespace="$NAMESPACE" \
    --image="$IMAGE" \
    --overrides="{
      \"spec\": {
        \"containers\": [{
          \"name\": \"crawler-test\",
          \"image\": \"$IMAGE\",
          \"envFrom\": [{
            \"configMapRef\": { \"name\": \"chatbot-crawler-job-config\" }
          }],
          \"env\": [
            { \"name\": \"CRAWL_JOB_ID\", \"value\": \"$CRAWL_JOB_ID\" },
            { \"name\": \"MAX_DEPTH\", \"value\": \"$MAX_DEPTH\" },
            { \"name\": \"MAX_PAGES\", \"value\": \"$MAX_PAGES\" },
            { \"name\": \"DB_PASSWORD\", \"valueFrom\": { \"secretKeyRef\": { \"name\": \"postgresql-credentials\", \"key\": \"password\" } } }
          ]
        }],
        \"imagePullSecrets\": [{ \"name\": \"ghcr-secret\" }]
      }
    }"
