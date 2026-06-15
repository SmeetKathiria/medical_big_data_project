# RunPod Setup

RunPod is optional and reserved for larger Spark or embedding workloads. The local representative pipeline should remain the primary proof path.

Build `infra/runpod/Dockerfile.worker`, mount or fetch pipeline inputs, and run the numbered jobs with explicit environment variables when full-corpus processing is required.
