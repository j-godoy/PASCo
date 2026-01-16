# Use Ubuntu 20.04 (AMD64)
# Stable base: Old enough for OpenSSL 1.1, new enough to compile Python 3.11
FROM --platform=linux/amd64 ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive

# 1. Install Dependencies (System + Python Build Tools)
RUN apt-get update && apt-get install -y \
    wget \
    git \
    build-essential \
    cmake \
    libicu-dev \
    libssl-dev \
    zlib1g-dev \
    libncurses5-dev \
    libgdbm-dev \
    libnss3-dev \
    libreadline-dev \
    libffi-dev \
    libsqlite3-dev \
    libbz2-dev \
    ca-certificates \
    graphviz \
    && rm -rf /var/lib/apt/lists/*

# 2. Compile Python 3.11 from Source
# We build it manually to avoid repository errors
WORKDIR /tmp
RUN wget https://www.python.org/ftp/python/3.11.7/Python-3.11.7.tgz \
    && tar -xvf Python-3.11.7.tgz \
    && cd Python-3.11.7 \
    && ./configure --enable-optimizations \
    && make -j $(nproc) \
    && make install \
    && cd .. \
    && rm -rf Python-3.11.7 Python-3.11.7.tgz

# 3. Install .NET SDK 2.2.106
WORKDIR /tmp
RUN wget https://dot.net/v1/dotnet-install.sh \
    && chmod +x dotnet-install.sh \
    && ./dotnet-install.sh --version 2.2.106 --install-dir /usr/share/dotnet

ENV PATH="$PATH:/usr/share/dotnet"

# --- THE FIX: Patch OpenSSL Configuration ---
# Disables the advanced configuration section that crashes .NET 2.2
RUN sed -i 's/^openssl_conf = openssl_init/#openssl_conf = openssl_init/g' /etc/ssl/openssl.cnf

# 4. Clone, Build, and Publish Verisol
WORKDIR /app
RUN git clone https://github.com/microsoft/verisol.git
WORKDIR /app/verisol

RUN dotnet restore Sources/VeriSol.sln
RUN dotnet build Sources/VeriSol.sln -c Release
RUN dotnet publish Sources/VeriSol/VeriSol.csproj -c Release -o /app/verisol/out --no-build

# Create wrapper script
RUN echo '#!/bin/bash\ndotnet /app/verisol/out/VeriSol.dll "$@"' > /usr/bin/VeriSol \
    && chmod +x /usr/bin/VeriSol

# 5. PASCo & Python Setup
WORKDIR /app
RUN git clone https://github.com/j-godoy/PASCo.git
WORKDIR /app/PASCo

# Create venv with Python 3.11
RUN python3.11 -m venv .env

# Activate venv permanently
ENV PATH="/app/PASCo/.env/bin:$PATH"

# --- NEW: Create requirements.txt if missing ---
RUN if [ ! -f requirements.txt ]; then \
    echo "requirements.txt not found. Creating it..." && \
    printf "graphviz==0.21\nnumpy==2.2.6\npsutil==7.2.1\npydot==4.0.1\npyparsing==3.3.1\ntabulate==0.9.0\n" > requirements.txt; \
    fi

# Install requirements
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# 6. Final Command
CMD ["/bin/bash"]