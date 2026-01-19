# 1) Imagen base AWS Lambda Python 3.11
FROM public.ecr.aws/lambda/python:3.11

# 2) Dependencias de SO para compilar dlib/OpenCV y SQLite,
#    incluyendo CMake ≥3.10, tar y gzip
RUN yum -y update && \
    yum install -y \
      gcc gcc-c++ make \
      cmake3 tar gzip \
      libjpeg-turbo-devel zlib-devel \
      sqlite sqlite-devel && \
    # linkea cmake3 a cmake para que dlib lo encuentre
    ln -s /usr/bin/cmake3 /usr/bin/cmake && \
    yum clean all

# 3) Requisitos Python
COPY requirements.txt .
RUN pip3 install --upgrade pip && \
    pip3 install --no-cache-dir -r requirements.txt

# 4) Copia tu código Lambda
COPY lambda_function.py ${LAMBDA_TASK_ROOT}/lambda_function.py

# 5) Define el handler
CMD ["lambda_function.lambda_handler"]
