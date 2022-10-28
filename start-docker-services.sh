#!/usr/bin/env bash

# Starts two docker-compose images with same settings, except for listening port

# Disable deep computations
export ENABLE_DEEP_SENTENCE_BUILDER=yes
export ENABLE_DEEP_PSO=yes
export ENABLE_DEEP_CATEGORIZER=no

# Huggingface access
export HF_API_TOKEN=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

# Start 1st WS
export WS_PORT=5000
docker compose -p overton${WS_PORT} up -d

# Wait a bit for startup
sleep 10

# Start 2nd WS
export WS_PORT=5001
docker compose -p overton${WS_PORT} up -d
