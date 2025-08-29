# OpenWhisk Deployment Guide

## Prerequisites

1. OpenWhisk running on EC2 with IP 172.31.17.101
2. Ollama running on EC2 with model gpt-oss:20b
3. wsk CLI configured to connect to OpenWhisk

## Package and Deploy

### 1. Create packages (run from project root)
```bash
./package-for-openwhisk.sh
```

### 2. Deploy to OpenWhisk
```bash
# Create package
wsk package create helpdesk

# Deploy orchestrator (main service)
wsk action create helpdesk/orchestrator build/helpdesk-orchestrator.zip \
  --kind python:3.11 --timeout 120000 --memory 1024

# Deploy similarity service
wsk action create helpdesk/similarity build/helpdesk-similarity.zip \
  --kind python:3.11 --timeout 60000 --memory 512

# Deploy ollama service
wsk action create helpdesk/ollama build/helpdesk-ollama.zip \
  --kind python:3.11 --timeout 120000 --memory 512
```

### 3. Test deployment
```bash
# Test orchestrator
wsk action invoke helpdesk/orchestrator \
  -p question "How do I register a new job?" \
  --result

# Test similarity
wsk action invoke helpdesk/similarity \
  -p question "How do I create a customer?" \
  --result

# Test ollama
wsk action invoke helpdesk/ollama \
  -p question "What is 2+2?" \
  --result
```

## Environment Variables

The system reads the `ALWAYS_CALL_LLM` environment variable. To set it:

```bash
# Set in OpenWhisk container (when starting)
docker run --rm -d \
  --name openwhisk \
  -p 3233:3233 \
  -e ALWAYS_CALL_LLM=true \
  -v /var/run/docker.sock:/var/run/docker.sock \
  openwhisk/standalone:nightly
```

## Call from R

```r
library(httr)
library(jsonlite)

OPENWHISK_HOST <- "15.161.146.166"  # Your EC2 public IP
OPENWHISK_PORT <- 3233
OPENWHISK_USER <- "23bc46b1-71f6-4ed5-8c54-816aa4f8c502"
OPENWHISK_PASS <- "123zO3xZCLrMN6v2BKK1dXYFpXlPkccOFqm12CdAsMgRU4VrNZ9lyGVCGuMDGIwP"

call_helpdesk <- function(question) {
  url <- paste0("http://", OPENWHISK_HOST, ":", OPENWHISK_PORT, 
                "/api/v1/namespaces/_/actions/helpdesk/orchestrator")
  
  body <- list(parameters = list(question = question))
  
  response <- POST(
    url = paste0(url, "?blocking=true&result=true"),
    authenticate(OPENWHISK_USER, OPENWHISK_PASS),
    add_headers("Content-Type" = "application/json"),
    body = toJSON(body, auto_unbox = TRUE)
  )
  
  return(fromJSON(content(response, "text")))
}

# Test
result <- call_helpdesk("How do I register a new job?")
print(result)
```

## Troubleshooting

1. **Connection refused to Ollama**: Verify IP address in config/helpdesk-config.yaml matches EC2 internal IP
2. **Module import errors**: Ensure __main__.py is in root of each ZIP file
3. **Timeout errors**: Increase --timeout parameter for LLM calls
4. **Memory errors**: Increase --memory parameter