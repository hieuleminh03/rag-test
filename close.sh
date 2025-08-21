#!/bin/bash
# for closing Weaviate and cleaning up processes
pkill -9 -f weaviate
lsof -ti:8079 | xargs kill -9 2>/dev/null || true
lsof -ti:50060 | xargs kill -9 2>/dev/null || true