# Point at any base image that you find suitable to extend.
FROM ubuntu:22.04 

# Install required tools that are useful for your project i.e. ninja-build
RUN apt update && apt install -y python3-bs4 

ENTRYPOINT ["/bin/bash", "-c"]
